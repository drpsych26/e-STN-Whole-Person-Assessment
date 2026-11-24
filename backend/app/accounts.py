"""Clinician account registry: organisation-level status for token subjects.

Identity and roles still come only from the verified token (app.auth, app.rbac).
The registry adds what a token cannot carry: whether this organisation has
invited, activated, suspended or deactivated a subject.

Statuses and transitions (admin role only; an admin cannot change their own account):

    invited --activate--> active --suspend--> suspended --activate--> active
    invited | active | suspended --deactivate--> deactivated
    deactivated --request reactivation (admin A)--> pending --approve (admin B != A)--> active

Request-time enforcement (fail closed), applied by app.rbac.require_roles to every
role-protected route after the role, MFA and organisation checks:
- A subject registered as invited, suspended or deactivated in the caller's
  organisation is refused (403) even with a valid token. The denial is audited.
- When STN_ACCOUNT_REGISTRY_REQUIRED is true, an unregistered subject is refused
  too. Production should set it, so that the access review covers everyone.
  Bootstrap the first admin with `python -m app.accounts register ...`.
- If the registry cannot be read: 503 when registration is required. When it is
  not required and no record store is configured, the check is skipped (routes
  that need data fail on their own).
- Active subjects get last_seen_at and the roles they last presented recorded, at
  most once every LAST_SEEN_INTERVAL seconds, for the access review.

Every transition writes an append-only account_events row and a hash-chained
audit event; reactivation after deactivation needs two different admins.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from . import audit, db

INVITED, ACTIVE, SUSPENDED, DEACTIVATED = "invited", "active", "suspended", "deactivated"
STATUSES = (INVITED, ACTIVE, SUSPENDED, DEACTIVATED)
REQUIRED_ENV = "STN_ACCOUNT_REGISTRY_REQUIRED"
STALE_ENV = "STN_ACCESS_REVIEW_STALE_DAYS"
DEFAULT_STALE_DAYS = 90
LAST_SEEN_INTERVAL = 300
CLI_ACTOR = "operator:cli"

_SUBJECT = re.compile(r"^[A-Za-z0-9_.:@|+=-]{1,256}$")
_CODE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_COLUMNS = ("org_id, subject, status, invited_by, invited_at, status_reason_code, status_changed_by, "
            "status_changed_at, last_seen_at, last_roles")
_REACT_COLUMNS = "id, subject, reason_code, state, requested_by, requested_at, decided_by, decided_at"


class AccountNotFound(LookupError):
    """No registry entry for this subject in the caller's organisation."""


class AccountTransitionNotAllowed(RuntimeError):
    """The requested status change is not permitted from the current status."""


class AccountSelfChange(PermissionError):
    """Admins cannot change the status of their own account."""


class AccountSecondPersonRequired(PermissionError):
    """Reactivation after deactivation must be approved by a different admin."""


class AccountInvalidInput(ValueError):
    """Request data failed validation."""


class AccountNotUsable(RuntimeError):
    """The subject's registry status does not allow this (for example as an assigned reviewer)."""


class AccountAccessDenied(PermissionError):
    """The caller's account is not active in this organisation."""


class AccountRegistryUnavailable(RuntimeError):
    """Registration is required but the registry cannot be read."""


def registry_required() -> bool:
    return os.getenv(REQUIRED_ENV, "false").strip().lower() in {"true", "1", "yes", "on"}


def stale_days() -> int:
    try:
        value = int(os.getenv(STALE_ENV, "").strip() or DEFAULT_STALE_DAYS)
    except ValueError:
        value = DEFAULT_STALE_DAYS
    return max(1, value)


def valid_subject(value: Any) -> str:
    if not isinstance(value, str) or not _SUBJECT.match(value):
        raise AccountInvalidInput("subject must be 1-256 characters of letters, digits or _ . : @ | + = -")
    return value


def _code(value: Any, field: str, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not _CODE.match(value):
        raise AccountInvalidInput(f"{field} must be 1-64 characters of letters, digits, '_', '.', ':' or '-'.")
    return value


def _finish(error: Exception | None, result: Any) -> Any:
    if error is not None:
        raise error
    return result


def account_row(conn: db.Conn, org: str, subject: str) -> dict[str, Any] | None:
    return conn.execute(
        f"SELECT {_COLUMNS} FROM clinician_accounts WHERE org_id = ? AND subject = ?", (org, subject)
    ).fetchone()


def usable(conn: db.Conn, org: str, subject: str) -> bool:
    """True if the subject may act in the organisation (active, or unregistered when registration is optional)."""
    row = account_row(conn, org, subject)
    if row is None:
        return not registry_required()
    return row["status"] == ACTIVE


def _event(conn: db.Conn, org: str, subject: str, before: str | None, after: str, reason: str | None,
           actor: str, stamp: str) -> None:
    conn.execute(
        "INSERT INTO account_events (id, org_id, subject, from_status, to_status, reason_code, actor, at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), org, subject, before, after, reason, actor, stamp),
    )


def _set_status(conn: db.Conn, org: str, subject: str, before: str, after: str, reason: str | None,
                actor: str) -> dict[str, Any]:
    stamp = audit.now()
    conn.execute(
        "UPDATE clinician_accounts SET status = ?, status_reason_code = ?, status_changed_by = ?, "
        "status_changed_at = ? WHERE org_id = ? AND subject = ? AND status = ?",
        (after, reason, actor, stamp, org, subject, before),
    )
    _event(conn, org, subject, before, after, reason, actor, stamp)
    return account_row(conn, org, subject)


# --------------------------------------------------------------------------- admin operations


def invite(actor: str, org: str, subject: Any, reason_code: Any = None) -> dict[str, Any]:
    subject = valid_subject(subject)
    reason = _code(reason_code, "reason_code", required=False)
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        if account_row(conn, org, subject) is not None:
            error, outcome = AccountTransitionNotAllowed("This subject is already registered."), "rejected_duplicate"
        else:
            error, outcome = None, "ok"
            stamp = audit.now()
            conn.execute(
                "INSERT INTO clinician_accounts (org_id, subject, status, invited_by, invited_at, status_reason_code, "
                "status_changed_by, status_changed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (org, subject, INVITED, actor, stamp, reason, actor, stamp),
            )
            _event(conn, org, subject, None, INVITED, reason, actor, stamp)
            result = account_row(conn, org, subject)
        audit.append(conn, actor, "account.invite", "account", subject, outcome, org=org)
    return _finish(error, result)


_ALLOWED = {
    "activate": ({INVITED, SUSPENDED}, ACTIVE, False),
    "suspend": ({ACTIVE}, SUSPENDED, True),
    "deactivate": ({INVITED, ACTIVE, SUSPENDED}, DEACTIVATED, True),
}


def change_status(actor: str, org: str, subject: Any, action: str, reason_code: Any = None) -> dict[str, Any]:
    """activate, suspend or deactivate. Reactivation after deactivation uses the two-person flow."""
    subject = valid_subject(subject)
    sources, target, reason_required = _ALLOWED[action]
    reason = _code(reason_code, "reason_code", required=reason_required)
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = account_row(conn, org, subject)
        if row is None:
            error, outcome = AccountNotFound(subject), "denied_or_missing"
        elif subject == actor:
            error, outcome = AccountSelfChange("You cannot change the status of your own account."), "rejected_self_change"
        elif row["status"] == DEACTIVATED and action == "activate":
            error = AccountTransitionNotAllowed(
                "A deactivated account is reactivated only through a reactivation request approved by a second admin.")
            outcome = "rejected_needs_second_person"
        elif row["status"] not in sources:
            error, outcome = AccountTransitionNotAllowed(f"Cannot {action} an account that is {row['status']}."), "rejected_state"
        else:
            error, outcome = None, "ok"
            result = _set_status(conn, org, subject, row["status"], target, reason, actor)
            if target == DEACTIVATED:
                _end_assignments(conn, org, subject, actor)
        audit.append(conn, actor, f"account.{action}", "account", subject, outcome, org=org)
    return _finish(error, result)


def _end_assignments(conn: db.Conn, org: str, subject: str, actor: str) -> None:
    """A deactivated reviewer keeps no open review assignments; they return to the reassignment queue."""
    stamp = audit.now()
    rows = conn.execute(
        "SELECT id, assessment_id FROM review_assignments WHERE org_id = ? AND reviewer_sub = ? AND ended_at IS NULL",
        (org, subject),
    ).fetchall()
    for row in rows:
        conn.execute(
            "UPDATE review_assignments SET ended_by = ?, ended_at = ?, end_reason = 'reviewer_deactivated' "
            "WHERE id = ? AND ended_at IS NULL",
            (actor, stamp, row["id"]),
        )
        audit.append(conn, actor, "review.unassign", "assessment", row["assessment_id"], "reviewer_deactivated", org=org)


def request_reactivation(actor: str, org: str, subject: Any, reason_code: Any) -> dict[str, Any]:
    subject = valid_subject(subject)
    reason = _code(reason_code, "reason_code")
    request_id = str(uuid.uuid4())
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = account_row(conn, org, subject)
        pending = conn.execute(
            "SELECT 1 AS x FROM account_reactivations WHERE org_id = ? AND subject = ? AND state = 'requested'",
            (org, subject),
        ).fetchone()
        if row is None:
            error, outcome = AccountNotFound(subject), "denied_or_missing"
        elif subject == actor:
            error, outcome = AccountSelfChange("You cannot request reactivation of your own account."), "rejected_self_change"
        elif row["status"] != DEACTIVATED:
            error, outcome = AccountTransitionNotAllowed("Only deactivated accounts need a reactivation request."), "rejected_state"
        elif pending:
            error, outcome = AccountTransitionNotAllowed("A reactivation request is already pending."), "rejected_duplicate"
        else:
            error, outcome = None, "ok"
            conn.execute(
                "INSERT INTO account_reactivations (id, org_id, subject, reason_code, state, requested_by, requested_at) "
                "VALUES (?, ?, ?, ?, 'requested', ?, ?)",
                (request_id, org, subject, reason, actor, audit.now()),
            )
            result = conn.execute(
                f"SELECT {_REACT_COLUMNS} FROM account_reactivations WHERE id = ?", (request_id,)
            ).fetchone()
        audit.append(conn, actor, "account.reactivation.request", "account", subject, outcome, org=org)
    return _finish(error, result)


def decide_reactivation(actor: str, org: str, request_id: str, approve: bool) -> dict[str, Any]:
    action = "approve" if approve else "cancel"
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        req = conn.execute(
            "SELECT * FROM account_reactivations WHERE id = ? AND org_id = ?", (request_id, org)
        ).fetchone()
        row = account_row(conn, org, req["subject"]) if req else None
        if req is None or row is None:
            error, outcome = AccountNotFound(request_id), "denied_or_missing"
        elif req["state"] != "requested":
            error, outcome = AccountTransitionNotAllowed(f"Reactivation is already {req['state']}."), "rejected_state"
        elif req["subject"] == actor:
            error, outcome = AccountSelfChange("You cannot decide on your own reactivation."), "rejected_self_change"
        elif approve and req["requested_by"] == actor:
            error = AccountSecondPersonRequired("Reactivation must be approved by a different admin from the requester.")
            outcome = "rejected_same_person"
        elif approve and row["status"] != DEACTIVATED:
            error, outcome = AccountTransitionNotAllowed("The account is no longer deactivated."), "rejected_state"
        else:
            error, outcome = None, "ok"
            stamp = audit.now()
            conn.execute(
                "UPDATE account_reactivations SET state = ?, decided_by = ?, decided_at = ? "
                "WHERE id = ? AND state = 'requested'",
                ("approved" if approve else "cancelled", actor, stamp, request_id),
            )
            if approve:
                _set_status(conn, org, req["subject"], DEACTIVATED, ACTIVE, req["reason_code"], actor)
            result = conn.execute(
                f"SELECT {_REACT_COLUMNS} FROM account_reactivations WHERE id = ?", (request_id,)
            ).fetchone()
        audit.append(conn, actor, f"account.reactivation.{action}", "account_reactivation", request_id, outcome, org=org)
    return _finish(error, result)


def list_accounts(actor: str, org: str, status: str | None = None) -> list[dict[str, Any]]:
    if status is not None and status not in STATUSES:
        raise AccountInvalidInput(f"status must be one of {', '.join(STATUSES)}.")
    with db.transaction() as conn:
        if status is None:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM clinician_accounts WHERE org_id = ? ORDER BY subject", (org,)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM clinician_accounts WHERE org_id = ? AND status = ? ORDER BY subject",
                (org, status),
            ).fetchall()
        audit.append(conn, actor, "account.list", "account", None, "ok", org=org)
    return rows


def account_history(actor: str, org: str, subject: Any) -> list[dict[str, Any]]:
    subject = valid_subject(subject)
    with db.transaction() as conn:
        if account_row(conn, org, subject) is None:
            error, outcome, rows = AccountNotFound(subject), "denied_or_missing", []
        else:
            error, outcome = None, "ok"
            rows = conn.execute(
                "SELECT from_status, to_status, reason_code, actor, at FROM account_events "
                "WHERE org_id = ? AND subject = ? ORDER BY at, id",
                (org, subject),
            ).fetchall()
        audit.append(conn, actor, "account.history", "account", subject, outcome, org=org)
    return _finish(error, rows)


def access_review(actor: str, org: str, stale_after_days: int | None = None) -> dict[str, Any]:
    """Who is registered, in which status, with which roles last presented and when last seen."""
    days = stale_after_days if stale_after_days is not None else stale_days()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with db.transaction() as conn:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM clinician_accounts WHERE org_id = ? ORDER BY subject", (org,)
        ).fetchall()
        pending = {r["subject"] for r in conn.execute(
            "SELECT subject FROM account_reactivations WHERE org_id = ? AND state = 'requested'", (org,)
        ).fetchall()}
        entries = []
        for row in rows:
            seen = row["last_seen_at"]
            entries.append({
                "subject": row["subject"],
                "status": row["status"],
                "roles_last_presented": [r for r in (row["last_roles"] or "").split(",") if r],
                "last_seen_at": seen,
                "invited_at": row["invited_at"],
                "status_changed_at": row["status_changed_at"],
                "status_reason_code": row["status_reason_code"],
                "inactive": row["status"] == ACTIVE and (seen is None or datetime.fromisoformat(seen) < cutoff),
                "reactivation_pending": row["subject"] in pending,
            })
        audit.append(conn, actor, "access_review.read", "account", None, "ok", org=org)
    counts = {s: sum(1 for e in entries if e["status"] == s) for s in STATUSES}
    return {
        "organisation": org,
        "generated_at": audit.now(),
        "registry_required": registry_required(),
        "inactive_after_days": days,
        "counts": counts,
        "inactive_active_accounts": sum(1 for e in entries if e["inactive"]),
        "accounts": entries,
        "note": ("Roles come from the identity provider; this report shows the roles each subject last "
                 "presented. Review role assignments in the identity provider as part of the access review."),
    }


# --------------------------------------------------------------------------- request-time enforcement


def enforce(org: str, subject: str, roles: Iterable[str]) -> None:
    """Refuse subjects whose registry status is not active (and unregistered ones when required)."""
    required = registry_required()
    try:
        kind = db.dialect()
    except db.StoreNotConfigured as exc:
        if required:
            raise AccountRegistryUnavailable("Account registry is not available.") from exc
        return
    if not required and kind == "sqlite" and not os.path.exists(os.environ[db.DB_ENV].strip()):
        # No database yet, so nothing is registered and nothing can be refused.
        # Do not create the file just to look.
        return
    role_text = ",".join(sorted(set(roles)))
    denial: str | None = None
    try:
        with db.transaction() as conn:
            row = account_row(conn, org, subject)
            if row is None:
                if required:
                    denial = "unregistered"
            elif row["status"] != ACTIVE:
                denial = row["status"]
            else:
                seen = row["last_seen_at"]
                stale = seen is None or datetime.fromisoformat(seen) < datetime.now(timezone.utc) - timedelta(
                    seconds=LAST_SEEN_INTERVAL)
                if stale or row["last_roles"] != role_text:
                    conn.execute(
                        "UPDATE clinician_accounts SET last_seen_at = ?, last_roles = ? "
                        "WHERE org_id = ? AND subject = ? AND status = ?",
                        (audit.now(), role_text, org, subject, ACTIVE),
                    )
            if denial is not None:
                audit.append(conn, subject, "account.access", "account", subject, f"denied_{denial}", org=org)
    except db.StoreNotConfigured as exc:
        if required:
            raise AccountRegistryUnavailable("Account registry is not available.") from exc
        return
    if denial is not None:
        detail = ("This account is not registered in this organisation." if denial == "unregistered"
                  else f"This account is {denial} in this organisation.")
        raise AccountAccessDenied(detail)


# --------------------------------------------------------------------------- operator CLI (bootstrap)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STN clinician account registry (operator bootstrap).")
    sub = parser.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register", help="Register a subject (status invited, or active with --activate).")
    reg.add_argument("--org", required=True)
    reg.add_argument("--subject", required=True)
    reg.add_argument("--activate", action="store_true")
    lst = sub.add_parser("list", help="List registered subjects for an organisation.")
    lst.add_argument("--org", required=True)
    args = parser.parse_args(argv)
    if args.command == "register":
        row = invite(CLI_ACTOR, args.org, args.subject, "operator_bootstrap")
        if args.activate:
            row = change_status(CLI_ACTOR, args.org, args.subject, "activate", "operator_bootstrap")
        print(json.dumps(row))
        return 0
    print(json.dumps(list_accounts(CLI_ACTOR, args.org), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
