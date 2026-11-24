"""Client accounts and onboarding (D-07): invitation, claim, verification, acknowledgement, activation.

Lifecycle (enforced here and by the schema; tests/test_client_accounts.py):

    invited --claim--> provisional --activate--> active <--suspend/reactivate--> suspended
    any state except deactivated --deactivate--> deactivated (final)

- The client record's owning clinician issues an invitation. The platform returns a one-time
  code once; only its SHA-256 is stored. The code is delivered to the client out of band (the
  notification service will carry it once an email provider is approved). No email address or
  phone number is stored here.
- A signed-in subject with the client role claims the code. The code binds that subject to that
  client record in the token's organisation. A code is single use, expires
  (STN_CLIENT_INVITE_HOURS, default 168) and cannot be used in another organisation.
- A provisional account can see its own onboarding status and record acknowledgements, and
  nothing else. It cannot see any clinical information.
- Activation is a clinician action (the record owner), never self-service, and needs every
  requirement met: identity-provider verification events for each kind in
  STN_CLIENT_REQUIRED_VERIFICATIONS (default "email,mfa"), and acknowledgement of the current
  versions of the terms, privacy notice and consent (STN_TERMS_VERSION,
  STN_PRIVACY_NOTICE_VERSION, STN_CONSENT_VERSION). Missing configuration fails closed.
- Admins suspend, reactivate and deactivate, with a reason code. Admins never see clinical content.
- A client's identity is resolved on the server from the token subject and organisation; no
  client route accepts a client id, so one client cannot address another client's records.
- Every action, including refusals, is audited (codes and identifiers only).
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from . import audit, db
from .identity_events import verified_kinds

INVITED, PROVISIONAL, ACTIVE, SUSPENDED, DEACTIVATED = "invited", "provisional", "active", "suspended", "deactivated"
ACK_ENV = {"terms": "STN_TERMS_VERSION", "privacy_notice": "STN_PRIVACY_NOTICE_VERSION", "consent": "STN_CONSENT_VERSION"}
VERIFY_ENV = "STN_CLIENT_REQUIRED_VERIFICATIONS"
INVITE_ENV = "STN_CLIENT_INVITE_HOURS"
_CODE = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
_REASON = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_VERSION = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class ClientAccountError(Exception):
    """Base; routes map subclasses to status codes."""


class ClientAccountNotFound(ClientAccountError):
    pass


class InvitationInvalid(ClientAccountError):
    pass


class ClientAccountConflict(ClientAccountError):
    pass


class ClientAccountInvalidInput(ClientAccountError):
    pass


class RequirementsNotMet(ClientAccountError):
    def __init__(self, missing: list[str]):
        super().__init__("Onboarding requirements are not met: " + ", ".join(missing))
        self.missing = missing


class OnboardingNotConfigured(ClientAccountError):
    pass


class ClientAccessDenied(PermissionError):
    pass


def _finish(error: Exception | None, result: Any) -> Any:
    if error is not None:
        raise error
    return result


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def invite_hours() -> int:
    try:
        return min(24 * 30, max(1, int(os.getenv(INVITE_ENV, "") or 168)))
    except ValueError:
        return 168


def required_verifications() -> list[str]:
    raw = os.getenv(VERIFY_ENV, "email,mfa")
    kinds = [k.strip() for k in raw.split(",") if k.strip()]
    return [k for k in kinds if k in {"email", "phone", "mfa"}] or ["email", "mfa"]


def current_version(kind: str) -> str | None:
    value = os.getenv(ACK_ENV[kind], "").strip()
    return value if value and _VERSION.match(value) else None


def _ident(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID.match(value):
        raise ClientAccountInvalidInput(f"{name} is invalid.")
    return value


def _owned_client(conn: db.Conn, org: str, actor: str, client_id: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT id, owner_sub FROM client_records WHERE id = ? AND org_id = ? AND owner_sub = ? AND disposed_at IS NULL",
        (client_id, org, actor),
    ).fetchone()


def _account(conn: db.Conn, org: str, client_id: str) -> dict[str, Any] | None:
    return conn.execute("SELECT * FROM client_accounts WHERE org_id = ? AND client_id = ?", (org, client_id)).fetchone()


def account_for_subject(conn: db.Conn, org: str, subject: str) -> dict[str, Any] | None:
    return conn.execute("SELECT * FROM client_accounts WHERE org_id = ? AND subject = ?", (org, subject)).fetchone()


def missing_requirements(conn: db.Conn, org: str, subject: str | None) -> list[str]:
    missing: list[str] = []
    have = verified_kinds(conn, subject) if subject else set()
    missing += [f"identity:{k}" for k in required_verifications() if k not in have]
    for kind in ACK_ENV:
        version = current_version(kind)
        if version is None:
            missing.append(f"configuration:{kind}_version")
            continue
        done = subject and conn.execute(
            "SELECT 1 AS x FROM client_acknowledgements WHERE org_id = ? AND subject = ? AND kind = ? AND version = ?",
            (org, subject, kind, version),
        ).fetchone()
        if not done:
            missing.append(f"acknowledgement:{kind}")
    return missing


def _staff_view(row: dict[str, Any], missing: list[str]) -> dict[str, Any]:
    return {
        "client_id": row["client_id"], "status": row["status"], "claimed": row["subject"] is not None,
        "invited_by": row["invited_by"], "invited_at": row["invited_at"], "invite_expires_at": row["invite_expires_at"],
        "claimed_at": row["claimed_at"], "activated_by": row["activated_by"], "activated_at": row["activated_at"],
        "status_reason_code": row["status_reason_code"], "status_changed_at": row["status_changed_at"],
        "outstanding_requirements": missing,
    }


# --------------------------------------------------------------------------- staff actions


def invite(actor: str, org: str, client_id: Any) -> dict[str, Any]:
    client_id = _ident(client_id, "client_id")
    code = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(hours=invite_hours())).isoformat()
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        account = _account(conn, org, client_id)
        action = "client_account.invite"
        if _owned_client(conn, org, actor, client_id) is None:
            error, outcome = ClientAccountNotFound(client_id), "denied_or_missing"
        elif account is not None and account["status"] != INVITED:
            error = ClientAccountConflict(f"This client already has an account ({account['status']}).")
            outcome = "rejected_state"
        else:
            error, outcome = None, "ok"
            stamp = now.isoformat()
            if account is None:
                conn.execute(
                    "INSERT INTO client_accounts (org_id, client_id, status, invite_code_sha256, invite_expires_at, "
                    "invited_by, invited_at, status_changed_by, status_changed_at) VALUES (?, ?, 'invited', ?, ?, ?, ?, ?, ?)",
                    (org, client_id, _hash(code), expires, actor, stamp, actor, stamp),
                )
            else:
                action = "client_account.reinvite"  # the earlier code stops working
                conn.execute(
                    "UPDATE client_accounts SET invite_code_sha256 = ?, invite_expires_at = ?, invited_by = ?, "
                    "invited_at = ? WHERE org_id = ? AND client_id = ? AND status = 'invited'",
                    (_hash(code), expires, actor, stamp, org, client_id),
                )
            result = {"client_id": client_id, "invitation_code": code, "expires_at": expires,
                      "note": "Shown once. Deliver it to the client through an approved channel."}
        audit.append(conn, actor, action, "client", client_id, outcome, org=org)
    return _finish(error, result)


def get_for_staff(actor: str, org: str, client_id: Any, is_admin: bool) -> dict[str, Any]:
    client_id = _ident(client_id, "client_id")
    with db.transaction() as conn:
        visible = is_admin or _owned_client(conn, org, actor, client_id) is not None
        account = _account(conn, org, client_id) if visible else None
        if account is None:
            error, outcome, view = ClientAccountNotFound(client_id), "denied_or_missing", None
        else:
            error, outcome = None, "ok"
            view = _staff_view(account, missing_requirements(conn, org, account["subject"]))
        audit.append(conn, actor, "client_account.read", "client", client_id, outcome, org=org)
    return _finish(error, view)


def activate(actor: str, org: str, client_id: Any) -> dict[str, Any]:
    client_id = _ident(client_id, "client_id")
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        account = _account(conn, org, client_id)
        if _owned_client(conn, org, actor, client_id) is None or account is None:
            error, outcome = ClientAccountNotFound(client_id), "denied_or_missing"
        elif account["status"] != PROVISIONAL:
            error, outcome = ClientAccountConflict(f"Only a provisional account can be activated ({account['status']})."), "rejected_state"
        elif account["subject"] == actor:
            error, outcome = ClientAccountConflict("You cannot activate your own client account."), "rejected_self"
        else:
            missing = missing_requirements(conn, org, account["subject"])
            if any(m.startswith("configuration:") for m in missing):
                error, outcome = OnboardingNotConfigured("Onboarding document versions are not configured."), "rejected_not_configured"
            elif missing:
                error, outcome = RequirementsNotMet(missing), "rejected_requirements"
            else:
                error, outcome = None, "ok"
                stamp = audit.now()
                conn.execute(
                    "UPDATE client_accounts SET status = 'active', activated_by = ?, activated_at = ?, "
                    "status_changed_by = ?, status_changed_at = ?, status_reason_code = NULL "
                    "WHERE org_id = ? AND client_id = ? AND status = 'provisional'",
                    (actor, stamp, actor, stamp, org, client_id),
                )
                result = _staff_view(_account(conn, org, client_id), [])
        audit.append(conn, actor, "client_account.activate", "client", client_id, outcome, org=org)
    return _finish(error, result)


_ADMIN_ACTIONS = {
    "suspend": ({PROVISIONAL, ACTIVE}, SUSPENDED, True),
    "reactivate": ({SUSPENDED}, None, False),
    "deactivate": ({INVITED, PROVISIONAL, ACTIVE, SUSPENDED}, DEACTIVATED, True),
}


def change_status(actor: str, org: str, client_id: Any, action: str, reason_code: Any = None) -> dict[str, Any]:
    client_id = _ident(client_id, "client_id")
    sources, target, reason_required = _ADMIN_ACTIONS[action]
    if reason_code is not None and (not isinstance(reason_code, str) or not _REASON.match(reason_code)):
        raise ClientAccountInvalidInput("reason_code is invalid.")
    if reason_required and reason_code is None:
        raise ClientAccountInvalidInput("reason_code is required.")
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        account = _account(conn, org, client_id)
        if account is None:
            error, outcome = ClientAccountNotFound(client_id), "denied_or_missing"
        elif account["status"] not in sources:
            error, outcome = ClientAccountConflict(f"Cannot {action} an account that is {account['status']}."), "rejected_state"
        elif account["subject"] is not None and account["subject"] == actor:
            error, outcome = ClientAccountConflict("You cannot change the status of your own account."), "rejected_self"
        else:
            error, outcome = None, "ok"
            new = target
            if action == "reactivate":
                # Back to active only if it had been activated and still meets every requirement.
                new = ACTIVE if account["activated_at"] and not missing_requirements(conn, org, account["subject"]) \
                    else PROVISIONAL
            conn.execute(
                "UPDATE client_accounts SET status = ?, status_reason_code = ?, status_changed_by = ?, status_changed_at = ?, "
                "invite_code_sha256 = CASE WHEN ? = 'deactivated' THEN NULL ELSE invite_code_sha256 END "
                "WHERE org_id = ? AND client_id = ?",
                (new, reason_code, actor, audit.now(), new, org, client_id),
            )
            row = _account(conn, org, client_id)
            result = _staff_view(row, missing_requirements(conn, org, row["subject"]))
        audit.append(conn, actor, f"client_account.{action}", "client", client_id, outcome, org=org)
    return _finish(error, result)


# --------------------------------------------------------------------------- client (self) actions


def claim(subject: str, org: str, code: Any) -> dict[str, Any]:
    if not isinstance(code, str) or not _CODE.match(code):
        raise InvitationInvalid("Invitation is invalid or has expired.")
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = conn.execute(
            "SELECT * FROM client_accounts WHERE invite_code_sha256 = ?", (_hash(code),)
        ).fetchone()
        now = datetime.now(timezone.utc)
        existing = account_for_subject(conn, org, subject)
        record = row["client_id"] if row is not None and row["org_id"] == org else None
        if row is None or row["org_id"] != org or row["status"] != INVITED or \
                datetime.fromisoformat(row["invite_expires_at"]) < now:
            error, outcome = InvitationInvalid("Invitation is invalid or has expired."), "rejected_invitation"
        elif existing is not None:
            error, outcome = ClientAccountConflict("This sign-in is already linked to a client account."), "rejected_subject_in_use"
        else:
            error, outcome = None, "ok"
            stamp = now.isoformat()
            conn.execute(
                "UPDATE client_accounts SET subject = ?, status = 'provisional', claimed_at = ?, invite_code_sha256 = NULL, "
                "invite_expires_at = NULL, status_changed_by = ?, status_changed_at = ? "
                "WHERE org_id = ? AND client_id = ? AND status = 'invited'",
                (subject, stamp, subject, stamp, org, row["client_id"]),
            )
            result = me(conn, org, subject)
        audit.append(conn, subject, "client_account.claim", "client", record, outcome, org=org)
    return _finish(error, result)


def me(conn: db.Conn, org: str, subject: str) -> dict[str, Any]:
    account = account_for_subject(conn, org, subject)
    if account is None:
        raise ClientAccountNotFound(subject)
    missing = missing_requirements(conn, org, subject)
    versions = {k: current_version(k) for k in ACK_ENV}
    return {"status": account["status"], "outstanding_requirements": missing, "current_versions": versions,
            "activation": "A clinician activates the account once every requirement is met." if account["status"] == PROVISIONAL else None}


def my_status(subject: str, org: str) -> dict[str, Any]:
    with db.transaction() as conn:
        return me(conn, org, subject)


def acknowledge(subject: str, org: str, kind: Any, version: Any) -> dict[str, Any]:
    if kind not in ACK_ENV:
        raise ClientAccountInvalidInput("kind must be terms, privacy_notice or consent.")
    current = current_version(kind)
    if current is None:
        raise OnboardingNotConfigured(f"The current {kind} version is not configured.")
    if version != current:
        raise ClientAccountInvalidInput(f"Only the current {kind} version ({current}) can be acknowledged.")
    with db.transaction() as conn:
        account = account_for_subject(conn, org, subject)
        if account is None or account["status"] not in {PROVISIONAL, ACTIVE}:
            audit.append(conn, subject, f"client_ack.{kind}", "subject", subject, "denied_or_missing", org=org)
            error: Exception | None = ClientAccountNotFound(subject)
        else:
            error = None
            seen = conn.execute(
                "SELECT 1 AS x FROM client_acknowledgements WHERE org_id = ? AND subject = ? AND kind = ? AND version = ?",
                (org, subject, kind, version),
            ).fetchone()
            if seen is None:
                conn.execute(
                    "INSERT INTO client_acknowledgements (id, org_id, subject, kind, version, recorded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (secrets.token_hex(16), org, subject, kind, version, audit.now()),
                )
            audit.append(conn, subject, f"client_ack.{kind}", "subject", subject, "ok" if seen is None else "ok_duplicate", org=org)
            result = me(conn, org, subject)
    return _finish(error, None if error else result)


def my_assessments(subject: str, org: str) -> list[dict[str, Any]]:
    """Metadata of the signed-in client's own assessments. Active accounts only; no payloads or notes."""
    with db.transaction() as conn:
        account = account_for_subject(conn, org, subject)
        rows = conn.execute(
            "SELECT id, form_id, form_version, state, created_at, updated_at FROM assessments "
            "WHERE org_id = ? AND client_id = ? AND disposed_at IS NULL ORDER BY created_at, id",
            (org, account["client_id"]),
        ).fetchall()
        audit.append(conn, subject, "client_portal.assessments", "client", account["client_id"], "ok", org=org)
    return rows


def enforce(org: str, subject: str, allowed: Iterable[str]) -> None:
    """Refuse a client subject whose account is missing or not in an allowed status (audited)."""
    allowed = set(allowed)
    with db.transaction() as conn:
        account = account_for_subject(conn, org, subject)
        status = account["status"] if account else "unregistered"
        if status not in allowed:
            audit.append(conn, subject, "client_account.access", "subject", subject, f"denied_{status}", org=org)
    if status not in allowed:
        raise ClientAccessDenied(
            "This client account is not active." if account else "This sign-in is not linked to a client account.")
