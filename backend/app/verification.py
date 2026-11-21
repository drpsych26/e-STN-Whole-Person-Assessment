"""Identity-verification events from the identity provider.

Verification is never supplied by staff or customers. The identity provider signs an event
(a JWT) when it verifies an email address, a phone number or MFA enrolment. This module
validates the signature against the configured JWKS, checks issuer, audience, expiry and a
unique event id, and only then records the verification. Replayed event ids are refused.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request, status

from . import audit, store
from .auth import _jwks_client

EVENT_KINDS = {
    "email_verified": "email",
    "phone_verified": "phone",
    "mfa_enrolled": "mfa",
}


class VerificationRejected(ValueError):
    pass


class VerificationNotConfigured(RuntimeError):
    pass


def _config() -> tuple[str, str, str]:
    issuer = os.getenv("STN_OIDC_ISSUER", "").strip()
    audience = os.getenv("STN_OIDC_AUDIENCE", "").strip()
    jwks_url = os.getenv("STN_OIDC_JWKS_URL", "").strip()
    if not (issuer and audience and jwks_url):
        raise VerificationNotConfigured("Identity provider is not configured.")
    return issuer, audience, jwks_url


def ingest_event(token: str) -> dict:
    issuer, audience, jwks_url = _config()
    try:
        key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"], audience=audience, issuer=issuer,
            options={"require": ["exp", "iat", "sub", "jti", "event"]},
        )
    except Exception as exc:  # fail closed; do not expose provider or key detail
        raise VerificationRejected("Event signature or claims are invalid.") from exc

    kind = EVENT_KINDS.get(claims.get("event"))
    if kind is None or claims.get("verified") is not True:
        raise VerificationRejected("Event type is not a verification the platform accepts.")
    subject = str(claims["sub"]).strip()
    event_id = str(claims["jti"]).strip()
    if not subject or not event_id:
        raise VerificationRejected("Event has no subject or event id.")
    issued = datetime.fromtimestamp(int(claims["iat"]), tz=timezone.utc).isoformat()
    now = datetime.now(timezone.utc).isoformat()

    def _do(conn):
        if conn.execute("SELECT 1 FROM verification_events WHERE event_id = ?", (event_id,)).fetchone():
            raise VerificationRejected("Event has already been recorded.")
        conn.execute(
            "INSERT INTO verification_events (event_id, subject, kind, issuer, issued_at, received_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, subject, kind, issuer, issued, now),
        )
        audit.append_in_tx(conn, f"idp:{issuer}", "verification.recorded", f"subject:{subject}",
                           {"kind": kind, "event_id": event_id})
        return {"subject": subject, "kind": kind}

    with store._connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            result = _do(conn)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    return result


def has_verification(conn, subject: str, kind: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM verification_events WHERE subject = ? AND kind = ? LIMIT 1", (subject, kind)
    ).fetchone() is not None


router = APIRouter(prefix="/v1/verification", tags=["verification"])


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def receive_event(request: Request) -> dict:
    """Webhook for identity-provider events. Authenticated by the event's own signature."""
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Body must be JSON.") from exc
    token = body.get("event") if isinstance(body, dict) else None
    if not isinstance(token, str) or not token:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Body must contain a signed event.")
    try:
        return ingest_event(token)
    except VerificationNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Verification is not available.") from exc
    except VerificationRejected as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    except store.StoreNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Verification is not available.") from exc
