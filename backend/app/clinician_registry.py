"""Clinician professional registration and attestation (D-07 clinician side, D-08).

- A clinician or reviewer submits their own registration details (authority code, registration
  number, scope code, expiry). A submission is a declaration only and grants nothing.
- An admin who is not that clinician attests that they checked the submitted record against the
  authority's public register: the attestation cites the exact registration record (reference
  validation: it must exist, be in the same organisation, belong to the named clinician, be the
  clinician's latest submission and be unexpired), an https source URL (host allow-listed by
  STN_REGISTER_HOSTS when set) and the date checked (not in the future, not older than
  STN_ATTESTATION_MAX_AGE_DAYS, default 30). Self-attestation is refused here and by the schema.
- Verified = the latest registration has an unrevoked attestation and has not expired.
  Submitting new details supersedes the old record, so it needs a new attestation.
- Enforcement: when STN_REQUIRE_VERIFIED_REGISTRATION is true (default: true in staging and
  production, false locally), routes reached through the clinician or reviewer role refuse
  unverified clinicians (403). Admin-only access is unaffected: admin is not clinical authority.

The engine records what a person says they checked. It does not and cannot confirm a
registration with the authority itself; that is the attesting admin's responsibility.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse

from . import audit, db

_CODE = re.compile(r"^[a-z0-9_]{2,64}$")
_NUMBER = re.compile(r"^[A-Za-z0-9-]{1,32}$")
_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
REQUIRE_ENV = "STN_REQUIRE_VERIFIED_REGISTRATION"
HOSTS_ENV = "STN_REGISTER_HOSTS"
AGE_ENV = "STN_ATTESTATION_MAX_AGE_DAYS"


class RegistryError(Exception):
    pass


class RegistryNotFound(RegistryError):
    pass


class RegistryInvalidInput(RegistryError):
    pass


class RegistryConflict(RegistryError):
    pass


class SelfAttestation(PermissionError):
    pass


class RegistrationNotVerified(PermissionError):
    pass


def enforcement_required() -> bool:
    raw = os.getenv(REQUIRE_ENV, "").strip().lower()
    if raw in {"true", "1", "yes", "on"}:
        return True
    if raw in {"false", "0", "no", "off"}:
        return False
    return db.hosted_environment()


def _date(value: Any, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise RegistryInvalidInput(f"{name} must be YYYY-MM-DD.") from exc


def _latest(conn: db.Conn, org: str, subject: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT * FROM clinician_registrations WHERE org_id = ? AND subject = ? ORDER BY submitted_at DESC, id DESC LIMIT 1",
        (org, subject),
    ).fetchone()


def status_for(conn: db.Conn, org: str, subject: str, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    reg = _latest(conn, org, subject)
    if reg is None:
        return {"subject": subject, "verified": False, "reason": "no_registration_submitted", "registration": None}
    att = conn.execute(
        "SELECT id, attested_by, attested_at, checked_on, source_url FROM attestations WHERE org_id = ? "
        "AND reference_type = 'clinician_registration' AND reference_id = ? AND revoked_at IS NULL "
        "ORDER BY attested_at DESC LIMIT 1",
        (org, reg["id"]),
    ).fetchone()
    expired = date.fromisoformat(reg["expires_on"]) < today
    reason = "registration_expired" if expired else ("awaiting_attestation" if att is None else None)
    view = {k: reg[k] for k in ("id", "authority", "registration_number", "scope_code", "expires_on", "submitted_at")}
    return {"subject": subject, "verified": reason is None, "reason": reason, "registration": view, "attestation": att}


def submit(actor: str, org: str, body: dict[str, Any]) -> dict[str, Any]:
    authority, number, scope = body.get("authority"), body.get("registration_number"), body.get("scope_code")
    if not isinstance(authority, str) or not _CODE.match(authority):
        raise RegistryInvalidInput("authority must be a code such as nz_psychologists_board.")
    if not isinstance(number, str) or not _NUMBER.match(number):
        raise RegistryInvalidInput("registration_number is invalid.")
    if not isinstance(scope, str) or not _CODE.match(scope):
        raise RegistryInvalidInput("scope_code must be a code.")
    expires = _date(body.get("expires_on"), "expires_on")
    if expires < date.today():
        raise RegistryInvalidInput("expires_on is in the past.")
    reg_id = str(uuid.uuid4())
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO clinician_registrations (id, org_id, subject, authority, registration_number, scope_code, "
            "expires_on, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (reg_id, org, actor, authority, number, scope, expires.isoformat(), audit.now()),
        )
        audit.append(conn, actor, "clinician_registration.submit", "clinician_registration", reg_id, "ok", org=org)
        return status_for(conn, org, actor)


def my_status(actor: str, org: str) -> dict[str, Any]:
    with db.transaction() as conn:
        return status_for(conn, org, actor)


def attest(actor: str, org: str, registration_id: Any, body: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(registration_id, str) or not _ID.match(registration_id):
        raise RegistryInvalidInput("registration_id is invalid.")
    source = body.get("source_url")
    parsed = urlparse(source) if isinstance(source, str) else None
    if parsed is None or parsed.scheme != "https" or not parsed.hostname or len(source) > 512:
        raise RegistryInvalidInput("source_url must be the https address of the public register entry.")
    hosts = {h.strip().lower() for h in os.getenv(HOSTS_ENV, "").split(",") if h.strip()}
    if hosts and parsed.hostname.lower() not in hosts:
        raise RegistryInvalidInput("source_url is not on an approved public register (STN_REGISTER_HOSTS).")
    checked = _date(body.get("checked_on"), "checked_on")
    try:
        max_age = max(1, int(os.getenv(AGE_ENV, "") or 30))
    except ValueError:
        max_age = 30
    if checked > date.today() or checked < date.today() - timedelta(days=max_age):
        raise RegistryInvalidInput(f"checked_on must be within the last {max_age} days and not in the future.")
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        reg = conn.execute(
            "SELECT * FROM clinician_registrations WHERE id = ? AND org_id = ?", (registration_id, org)
        ).fetchone()
        if reg is None:
            error, outcome = RegistryNotFound(registration_id), "denied_or_missing"
        elif reg["subject"] == actor:
            error, outcome = SelfAttestation("You cannot attest your own registration."), "rejected_self"
        elif _latest(conn, org, reg["subject"])["id"] != reg["id"]:
            error, outcome = RegistryConflict("A newer registration has been submitted; attest that one."), "rejected_superseded"
        elif date.fromisoformat(reg["expires_on"]) < date.today():
            error, outcome = RegistryConflict("This registration has expired."), "rejected_expired"
        elif conn.execute(
                "SELECT 1 AS x FROM attestations WHERE org_id = ? AND reference_type = 'clinician_registration' "
                "AND reference_id = ? AND revoked_at IS NULL", (org, reg["id"])).fetchone():
            error, outcome = RegistryConflict("This registration is already attested."), "rejected_duplicate"
        else:
            error, outcome = None, "ok"
            conn.execute(
                "INSERT INTO attestations (id, org_id, kind, reference_type, reference_id, subject, source_url, "
                "checked_on, attested_by, attested_at) VALUES (?, ?, 'registration_verified', 'clinician_registration', "
                "?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), org, reg["id"], reg["subject"], source, checked.isoformat(), actor, audit.now()),
            )
            result = status_for(conn, org, reg["subject"])
        audit.append(conn, actor, "attestation.registration_verified", "clinician_registration", registration_id,
                     outcome, org=org)
    return _finish(error, result)


def revoke(actor: str, org: str, attestation_id: Any) -> dict[str, Any]:
    if not isinstance(attestation_id, str) or not _ID.match(attestation_id):
        raise RegistryInvalidInput("attestation_id is invalid.")
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        att = conn.execute("SELECT * FROM attestations WHERE id = ? AND org_id = ?", (attestation_id, org)).fetchone()
        if att is None:
            error, outcome = RegistryNotFound(attestation_id), "denied_or_missing"
        elif att["revoked_at"] is not None:
            error, outcome = RegistryConflict("This attestation is already revoked."), "rejected_duplicate"
        else:
            error, outcome = None, "ok"
            conn.execute("UPDATE attestations SET revoked_by = ?, revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                         (actor, audit.now(), attestation_id))
            result = status_for(conn, org, att["subject"])
        audit.append(conn, actor, "attestation.revoke", "attestation", attestation_id, outcome, org=org)
    return _finish(error, result)


def list_status(actor: str, org: str) -> list[dict[str, Any]]:
    with db.transaction() as conn:
        subjects = [r["subject"] for r in conn.execute(
            "SELECT DISTINCT subject FROM clinician_registrations WHERE org_id = ? ORDER BY subject", (org,)).fetchall()]
        out = [status_for(conn, org, s) for s in subjects]
        audit.append(conn, actor, "clinician_registration.list", "clinician_registration", None, "ok", org=org)
    return out


def enforce(org: str, subject: str) -> None:
    if not enforcement_required():
        return
    with db.transaction() as conn:
        verified = status_for(conn, org, subject)["verified"]
        if not verified:
            audit.append(conn, subject, "clinician_registration.access", "subject", subject, "denied_unverified", org=org)
    if not verified:
        raise RegistrationNotVerified("Clinical access needs a verified professional registration.")


def _finish(error: Exception | None, result: Any) -> Any:
    if error is not None:
        raise error
    return result
