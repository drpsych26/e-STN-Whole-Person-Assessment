"""Identity-provider verification events (D-07): signed by the provider, never asserted by people.

The identity provider (Microsoft Entra External ID, or a compatible provider) signs a JWT when
it verifies an email address, a phone number or MFA enrolment, and posts it to
POST /v1/identity/events. The event is accepted only when every check passes:

- RS256 signature against the provider's JWKS (STN_IDP_EVENT_JWKS_URL, default STN_OIDC_JWKS_URL);
- issuer (STN_IDP_EVENT_ISSUER, default STN_OIDC_ISSUER);
- audience STN_IDP_EVENT_AUDIENCE, which must differ from the API audience STN_OIDC_AUDIENCE so
  an access token can never be replayed as an event (fail closed if missing or equal);
- exp in the future, iat present, not more than 60 s in the future and not older than
  STN_IDP_EVENT_MAX_AGE_SECONDS (default 600); nbf honoured when present;
- sub and jti present and well formed; event is a known kind and verified is true;
- (issuer, jti) not seen before: replayed events are refused.

Results are recorded as identifiers and codes only (no email address or phone number).
Rejections are not stored (they are unauthenticated input) but are counted by the per-IP
rate limit and logged without token content.

Live integration is NOT verified: tests use a synthetic RSA key and JWKS. Before staging, the
Entra tenant must be configured to emit these events (see docs/architecture/IDENTITY-AND-ONBOARDING.md).
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

import jwt
from fastapi import APIRouter, HTTPException, Request, status

from . import audit, db
from .auth import _jwks_client

EVENT_KINDS = {"email_verified": "email", "phone_verified": "phone", "mfa_enrolled": "mfa"}
CLOCK_SKEW_SECONDS = 60
DEFAULT_MAX_AGE_SECONDS = 600
_SUBJECT = re.compile(r"^[A-Za-z0-9_.:@|+=-]{1,256}$")
_EVENT_ID = re.compile(r"^[A-Za-z0-9_.:-]{8,128}$")
MAX_EVENT_BYTES = 8192


class EventRejected(ValueError):
    """The event failed a check. The message is safe to return; it never echoes token content."""


class EventsNotConfigured(RuntimeError):
    pass


def _config() -> tuple[str, str, str, int]:
    issuer = (os.getenv("STN_IDP_EVENT_ISSUER") or os.getenv("STN_OIDC_ISSUER", "")).strip()
    jwks_url = (os.getenv("STN_IDP_EVENT_JWKS_URL") or os.getenv("STN_OIDC_JWKS_URL", "")).strip()
    audience = os.getenv("STN_IDP_EVENT_AUDIENCE", "").strip()
    api_audience = os.getenv("STN_OIDC_AUDIENCE", "").strip()
    if not (issuer and jwks_url and audience):
        raise EventsNotConfigured("Identity events are not configured.")
    if audience == api_audience:
        raise EventsNotConfigured("STN_IDP_EVENT_AUDIENCE must differ from the API audience.")
    try:
        max_age = max(60, int(os.getenv("STN_IDP_EVENT_MAX_AGE_SECONDS", "") or DEFAULT_MAX_AGE_SECONDS))
    except ValueError:
        max_age = DEFAULT_MAX_AGE_SECONDS
    return issuer, jwks_url, audience, max_age


def validate(token: str, now: datetime | None = None) -> dict[str, Any]:
    """Return {issuer, event_id, subject, kind, issued_at} or raise EventRejected."""
    issuer, jwks_url, audience, max_age = _config()
    if not isinstance(token, str) or not token or len(token) > MAX_EVENT_BYTES:
        raise EventRejected("A signed event is required.")
    try:
        key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"], audience=audience, issuer=issuer,
            options={"require": ["exp", "iat", "sub", "jti", "iss", "aud"]}, leeway=CLOCK_SKEW_SECONDS,
        )
    except Exception as exc:  # fail closed; never expose key or token detail
        raise EventRejected("Event signature or claims are invalid.") from exc
    now = now or datetime.now(timezone.utc)
    iat = claims.get("iat")
    if not isinstance(iat, (int, float)):
        raise EventRejected("Event issue time is invalid.")
    age = now.timestamp() - float(iat)
    if age < -CLOCK_SKEW_SECONDS:
        raise EventRejected("Event is issued in the future.")
    if age > max_age:
        raise EventRejected("Event is too old.")
    kind = EVENT_KINDS.get(claims.get("event"))
    if kind is None:
        raise EventRejected("Event type is not a verification the platform accepts.")
    if claims.get("verified") is not True:
        raise EventRejected("Event does not confirm a verification.")
    subject, event_id = claims.get("sub"), claims.get("jti")
    if not isinstance(subject, str) or not _SUBJECT.match(subject):
        raise EventRejected("Event subject is invalid.")
    if not isinstance(event_id, str) or not _EVENT_ID.match(event_id):
        raise EventRejected("Event id is invalid.")
    return {"issuer": issuer, "event_id": event_id, "subject": subject, "kind": kind,
            "issued_at": datetime.fromtimestamp(float(iat), tz=timezone.utc).isoformat()}


def ingest(token: str) -> dict[str, Any]:
    event = validate(token)
    with db.transaction() as conn:
        seen = conn.execute(
            "SELECT 1 AS x FROM identity_verification_events WHERE issuer = ? AND event_id = ?",
            (event["issuer"], event["event_id"]),
        ).fetchone()
        if seen is not None:
            audit.append(conn, "idp", f"identity_event.{event['kind']}", "subject", event["subject"], "rejected_replay")
            replay = True
        else:
            replay = False
            conn.execute(
                "INSERT INTO identity_verification_events (issuer, event_id, subject, kind, issued_at, received_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (event["issuer"], event["event_id"], event["subject"], event["kind"], event["issued_at"], audit.now()),
            )
            audit.append(conn, "idp", f"identity_event.{event['kind']}", "subject", event["subject"], "ok")
    if replay:
        raise EventRejected("Event has already been recorded.")
    return {"subject": event["subject"], "kind": event["kind"], "recorded": True}


def verified_kinds(conn: db.Conn, subject: str) -> set[str]:
    rows = conn.execute(
        "SELECT DISTINCT kind FROM identity_verification_events WHERE subject = ?", (subject,)
    ).fetchall()
    return {r["kind"] for r in rows}


router = APIRouter(prefix="/v1/identity", tags=["identity"])


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def receive_event(request: Request) -> dict:
    """Identity-provider webhook. Authenticated only by the event's own signature; body {"event": "<JWT>"}."""
    raw = await request.body()
    if len(raw) > MAX_EVENT_BYTES + 64:
        raise HTTPException(413, "Payload exceeds the size limit.")
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(422, "Body must be a JSON object.") from exc
    token = body.get("event") if isinstance(body, dict) else None
    try:
        return ingest(token)
    except EventsNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Identity events are not available.") from exc
    except EventRejected as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    except db.StoreNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Identity events are not available.") from exc
