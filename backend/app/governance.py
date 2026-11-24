"""Consent records, retention policy, legal holds and two-person disposal.

Consent: the owning clinician records each consent a client gives (a scope code
and a reference to the version of the consent text, not the text itself), and
records a withdrawal once. Rows cannot be deleted or rewritten.

Retention: the minimum retention period comes only from STN_RETENTION_PERIOD_DAYS.
Nothing here asserts what the legal period is. In New Zealand the Health
(Retention of Health Information) Regulations 1996 set a minimum period for
health information; the period, how it is counted and any longer obligations must
be confirmed by the organisation's legal adviser before any record is disposed of.
With no valid period configured, disposal is refused (fail closed).
The retention anchor used here is the latest updated_at of the client record and
its assessments: an approximation of "the last date services were provided" that
the legal review must confirm or replace.

Legal holds: an admin places and releases holds. A client under an active hold
cannot be disposed of, and a hold placed after a request blocks its approval.

Disposal: an admin requests disposal of one client's records; a different person
with the admin or reviewer role approves it. Approval re-checks eligibility
(period elapsed, no active hold, no unresolved safety escalation, no assessment
submitted or in review) and then
removes every payload (client record, assessment versions, notes, statements of
correction) and the safety flag codes. Metadata rows stay as tombstones with disposed_at set, the executed
disposal row records who, when and how many, and every step is audited. Disposed
rows are final at the database level.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from . import audit, db
from .assessments import IN_REVIEW, SUBMITTED, InvalidInput, TransitionNotAllowed, _code
from .store import RecordDisposed, RecordNotFound, client_row

RETENTION_ENV = "STN_RETENTION_PERIOD_DAYS"
RETENTION_BASIS_NOTE = (
    "Configured value only. The organisation's legal adviser must confirm the retention period and how it "
    "is counted under the Health (Retention of Health Information) Regulations 1996 and any other "
    "applicable obligation before any record is disposed of."
)


class RetentionNotConfigured(RuntimeError):
    """No valid retention period is configured; disposal is refused."""


class NotEligible(RuntimeError):
    """The client's records are not eligible for disposal now."""


class SecondPersonRequired(PermissionError):
    """Disposal must be approved by someone other than the requester."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def retention_period_days() -> int | None:
    raw = os.getenv(RETENTION_ENV, "").strip()
    try:
        days = int(raw)
    except ValueError:
        return None
    return days if days > 0 else None


def policy() -> dict[str, Any]:
    days = retention_period_days()
    return {"configured": days is not None, "retention_period_days": days, "basis_note": RETENTION_BASIS_NOTE}


def _finish(error: Exception | None, result: Any) -> Any:
    if error is not None:
        raise error
    return result


# --------------------------------------------------------------------------- consent


_CONSENT_COLUMNS = "id, client_id, scope, consent_text_ref, captured_by, captured_at, withdrawn_by, withdrawn_at"


def _owned_client(conn: db.Conn, actor: str, org: str, client_id: str) -> tuple[dict | None, Exception | None, str]:
    client = client_row(conn, client_id, org)
    if client is None or client["owner_sub"] != actor:
        return client, RecordNotFound(client_id), "denied_or_missing"
    if client["disposed_at"] is not None:
        return client, RecordDisposed(client_id), "rejected_disposed"
    return client, None, "ok"


def record_consent(actor: str, org: str, client_id: str, scope: Any, consent_text_ref: Any) -> dict[str, Any]:
    scope, consent_text_ref = _code(scope, "scope"), _code(consent_text_ref, "consent_text_ref")
    consent: dict[str, Any] | None = None
    consent_id = str(uuid.uuid4())
    with db.transaction() as conn:
        _, error, outcome = _owned_client(conn, actor, org, client_id)
        if error is None:
            conn.execute(
                "INSERT INTO consents (id, org_id, client_id, scope, consent_text_ref, captured_by, captured_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (consent_id, org, client_id, scope, consent_text_ref, actor, audit.now()),
            )
            consent = conn.execute(f"SELECT {_CONSENT_COLUMNS} FROM consents WHERE id = ?", (consent_id,)).fetchone()
        audit.append(conn, actor, "consent.record", "consent" if error is None else "client",
                     consent_id if error is None else client_id, outcome, org=org)
    return _finish(error, consent)


def list_consents(actor: str, org: str, client_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with db.transaction() as conn:
        client = client_row(conn, client_id, org)
        if client is None or client["owner_sub"] != actor:
            error, outcome = RecordNotFound(client_id), "denied_or_missing"
        else:
            error, outcome = None, "ok"
            rows = conn.execute(
                f"SELECT {_CONSENT_COLUMNS} FROM consents WHERE client_id = ? AND org_id = ? ORDER BY captured_at",
                (client_id, org),
            ).fetchall()
        audit.append(conn, actor, "consent.list", "client", client_id, outcome, org=org)
    return _finish(error, rows)


def withdraw_consent(actor: str, org: str, client_id: str, consent_id: str) -> dict[str, Any]:
    consent: dict[str, Any] | None = None
    with db.transaction() as conn:
        _, error, outcome = _owned_client(conn, actor, org, client_id)
        if error is None:
            current = conn.execute(
                "SELECT * FROM consents WHERE id = ? AND client_id = ? AND org_id = ?", (consent_id, client_id, org)
            ).fetchone()
            if current is None:
                error, outcome = RecordNotFound(consent_id), "denied_or_missing"
            elif current["withdrawn_at"] is not None:
                error, outcome = TransitionNotAllowed("This consent has already been withdrawn."), "rejected_duplicate"
            else:
                conn.execute(
                    "UPDATE consents SET withdrawn_by = ?, withdrawn_at = ? WHERE id = ? AND withdrawn_at IS NULL",
                    (actor, audit.now(), consent_id),
                )
                consent = conn.execute(f"SELECT {_CONSENT_COLUMNS} FROM consents WHERE id = ?", (consent_id,)).fetchone()
        audit.append(conn, actor, "consent.withdraw", "consent", consent_id, outcome, org=org)
    return _finish(error, consent)


# --------------------------------------------------------------------------- legal holds


_HOLD_COLUMNS = "id, client_id, reason_code, placed_by, placed_at, released_by, released_at"


def _active_hold(conn: db.Conn, client_id: str, org: str) -> bool:
    return conn.execute(
        "SELECT 1 AS x FROM legal_holds WHERE client_id = ? AND org_id = ? AND released_at IS NULL",
        (client_id, org),
    ).fetchone() is not None


def place_hold(actor: str, org: str, client_id: str, reason_code: Any) -> dict[str, Any]:
    reason_code = _code(reason_code, "reason_code")
    hold: dict[str, Any] | None = None
    hold_id = str(uuid.uuid4())
    with db.transaction() as conn:
        client = client_row(conn, client_id, org)
        if client is None:
            error, outcome = RecordNotFound(client_id), "denied_or_missing"
        elif client["disposed_at"] is not None:
            error, outcome = RecordDisposed(client_id), "rejected_disposed"
        else:
            error, outcome = None, "ok"
            conn.execute(
                "INSERT INTO legal_holds (id, org_id, client_id, reason_code, placed_by, placed_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (hold_id, org, client_id, reason_code, actor, audit.now()),
            )
            hold = conn.execute(f"SELECT {_HOLD_COLUMNS} FROM legal_holds WHERE id = ?", (hold_id,)).fetchone()
        audit.append(conn, actor, "legal_hold.place", "client", client_id, outcome, org=org)
    return _finish(error, hold)


def release_hold(actor: str, org: str, hold_id: str) -> dict[str, Any]:
    hold: dict[str, Any] | None = None
    with db.transaction() as conn:
        current = conn.execute("SELECT * FROM legal_holds WHERE id = ? AND org_id = ?", (hold_id, org)).fetchone()
        if current is None:
            error, outcome = RecordNotFound(hold_id), "denied_or_missing"
        elif current["released_at"] is not None:
            error, outcome = TransitionNotAllowed("This legal hold has already been released."), "rejected_duplicate"
        else:
            error, outcome = None, "ok"
            conn.execute(
                "UPDATE legal_holds SET released_by = ?, released_at = ? WHERE id = ? AND released_at IS NULL",
                (actor, audit.now(), hold_id),
            )
            hold = conn.execute(f"SELECT {_HOLD_COLUMNS} FROM legal_holds WHERE id = ?", (hold_id,)).fetchone()
        audit.append(conn, actor, "legal_hold.release", "legal_hold", hold_id, outcome, org=org)
    return _finish(error, hold)


def list_holds(actor: str, org: str, client_id: str | None = None) -> list[dict[str, Any]]:
    with db.transaction() as conn:
        if client_id is None:
            rows = conn.execute(
                f"SELECT {_HOLD_COLUMNS} FROM legal_holds WHERE org_id = ? ORDER BY placed_at", (org,)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {_HOLD_COLUMNS} FROM legal_holds WHERE org_id = ? AND client_id = ? ORDER BY placed_at",
                (org, client_id),
            ).fetchall()
        audit.append(conn, actor, "legal_hold.list", "legal_hold", client_id, "ok", org=org)
    return rows


# --------------------------------------------------------------------------- retention


def _anchor(conn: db.Conn, client: dict[str, Any], org: str) -> str:
    row = conn.execute(
        "SELECT MAX(updated_at) AS latest FROM assessments WHERE client_id = ? AND org_id = ?", (client["id"], org)
    ).fetchone()
    latest = row["latest"] if row and row["latest"] else None
    return max(client["updated_at"], latest) if latest else client["updated_at"]


def _active_workflow(conn: db.Conn, client_id: str, org: str) -> bool:
    return conn.execute(
        "SELECT 1 AS x FROM assessments WHERE client_id = ? AND org_id = ? AND state IN (?, ?)",
        (client_id, org, SUBMITTED, IN_REVIEW),
    ).fetchone() is not None


def _pending_disposal(conn: db.Conn, client_id: str, org: str) -> bool:
    return conn.execute(
        "SELECT 1 AS x FROM disposals WHERE client_id = ? AND org_id = ? AND state = 'requested'", (client_id, org)
    ).fetchone() is not None


def _unresolved_escalation(conn: db.Conn, client_id: str, org: str) -> bool:
    return conn.execute(
        "SELECT 1 AS x FROM safety_escalations WHERE client_id = ? AND org_id = ? AND status <> 'resolved'",
        (client_id, org),
    ).fetchone() is not None


def _ineligible_reason(conn: db.Conn, client: dict[str, Any], org: str, days: int) -> tuple[str | None, str]:
    anchor = _anchor(conn, client, org)
    if _active_hold(conn, client["id"], org):
        return "The client's records are under an active legal hold.", anchor
    if _unresolved_escalation(conn, client["id"], org):
        return "A safety escalation about this client is unresolved; resolve it first.", anchor
    if _active_workflow(conn, client["id"], org):
        return "An assessment is submitted or in review; finish or return it first.", anchor
    if datetime.fromisoformat(anchor) + timedelta(days=days) > _now():
        return "The retention period has not yet elapsed.", anchor
    return None, anchor


def due_for_disposal(actor: str, org: str) -> list[dict[str, Any]]:
    """Clients in the organisation past the configured period, not held, not disposed, not already requested."""
    days = retention_period_days()
    if days is None:
        raise RetentionNotConfigured("Retention period is not configured.")
    due: list[dict[str, Any]] = []
    with db.transaction() as conn:
        clients = conn.execute(
            "SELECT * FROM client_records WHERE org_id = ? AND disposed_at IS NULL ORDER BY updated_at", (org,)
        ).fetchall()
        for client in clients:
            reason, anchor = _ineligible_reason(conn, client, org, days)
            if reason is None and not _pending_disposal(conn, client["id"], org):
                eligible_from = datetime.fromisoformat(anchor) + timedelta(days=days)
                due.append({"client_id": client["id"], "retention_anchor": anchor,
                            "eligible_from": _iso(eligible_from)})
        audit.append(conn, actor, "retention.due.read", "retention", None, "ok", org=org)
    return due


# --------------------------------------------------------------------------- disposal


_DISPOSAL_COLUMNS = (
    "id, client_id, reason_code, state, retention_period_days, retention_anchor, requested_by, requested_at, "
    "decided_by, decided_at, assessments_disposed"
)


def _disposal(conn: db.Conn, disposal_id: str) -> dict[str, Any]:
    return conn.execute(f"SELECT {_DISPOSAL_COLUMNS} FROM disposals WHERE id = ?", (disposal_id,)).fetchone()


def request_disposal(actor: str, org: str, client_id: str, reason_code: Any) -> dict[str, Any]:
    reason_code = _code(reason_code, "reason_code")
    days = retention_period_days()
    if days is None:
        raise RetentionNotConfigured("Retention period is not configured.")
    disposal_id = str(uuid.uuid4())
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        client = client_row(conn, client_id, org)
        if client is None:
            error, outcome = RecordNotFound(client_id), "denied_or_missing"
        elif client["disposed_at"] is not None:
            error, outcome = TransitionNotAllowed("These records have already been disposed of."), "rejected_disposed"
        elif _pending_disposal(conn, client_id, org):
            error, outcome = TransitionNotAllowed("A disposal request is already pending."), "rejected_duplicate"
        else:
            reason, anchor = _ineligible_reason(conn, client, org, days)
            if reason is not None:
                error, outcome = NotEligible(reason), "rejected_not_eligible"
            else:
                error, outcome = None, "ok"
                conn.execute(
                    "INSERT INTO disposals (id, org_id, client_id, reason_code, state, retention_period_days, "
                    "retention_anchor, requested_by, requested_at) VALUES (?, ?, ?, ?, 'requested', ?, ?, ?, ?)",
                    (disposal_id, org, client_id, reason_code, days, anchor, actor, audit.now()),
                )
                result = _disposal(conn, disposal_id)
        audit.append(conn, actor, "disposal.request", "client", client_id, outcome, org=org)
    return _finish(error, result)


def approve_disposal(actor: str, org: str, disposal_id: str) -> dict[str, Any]:
    days = retention_period_days()
    if days is None:
        raise RetentionNotConfigured("Retention period is not configured.")
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        request = conn.execute("SELECT * FROM disposals WHERE id = ? AND org_id = ?", (disposal_id, org)).fetchone()
        client = client_row(conn, request["client_id"], org) if request else None
        if request is None or client is None:
            error, outcome = RecordNotFound(disposal_id), "denied_or_missing"
        elif request["state"] != "requested":
            error, outcome = TransitionNotAllowed(f"Disposal is already {request['state']}."), "rejected_state"
        elif request["requested_by"] == actor:
            error = SecondPersonRequired("Disposal must be approved by a different person from the requester.")
            outcome = "rejected_same_person"
        else:
            reason, _ = _ineligible_reason(conn, client, org, days)
            if reason is not None:
                error, outcome = NotEligible(reason), "rejected_not_eligible"
            else:
                error, outcome = None, "ok"
                stamp = audit.now()
                client_id = client["id"]
                versions = conn.execute(
                    "SELECT id FROM assessments WHERE client_id = ? AND org_id = ? AND disposed_at IS NULL",
                    (client_id, org),
                ).fetchall()
                conn.execute(
                    "UPDATE assessments SET ciphertext = ?, note_ciphertext = NULL, disposed_at = ? "
                    "WHERE client_id = ? AND org_id = ? AND disposed_at IS NULL",
                    (b"", stamp, client_id, org),
                )
                conn.execute(
                    "UPDATE safety_flags SET code = 'disposed:' || id WHERE assessment_id IN "
                    "(SELECT id FROM assessments WHERE client_id = ? AND org_id = ?)",
                    (client_id, org),
                )
                conn.execute(
                    "UPDATE client_records SET ciphertext = ?, disposed_at = ? WHERE id = ? AND org_id = ?",
                    (b"", stamp, client_id, org),
                )
                statements = conn.execute(
                    "SELECT id FROM correction_statements WHERE client_id = ? AND org_id = ? AND disposed_at IS NULL",
                    (client_id, org),
                ).fetchall()
                conn.execute(
                    "UPDATE correction_statements SET statement_ciphertext = ?, disposed_at = ? "
                    "WHERE client_id = ? AND org_id = ? AND disposed_at IS NULL",
                    (b"", stamp, client_id, org),
                )
                for statement in statements:
                    audit.append(conn, actor, "record.dispose", "correction_statement", statement["id"], "ok", org=org)
                conn.execute(
                    "UPDATE disposals SET state = 'executed', decided_by = ?, decided_at = ?, assessments_disposed = ? "
                    "WHERE id = ? AND state = 'requested'",
                    (actor, stamp, len(versions), disposal_id),
                )
                for version in versions:
                    audit.append(conn, actor, "record.dispose", "assessment", version["id"], "ok", org=org)
                audit.append(conn, actor, "record.dispose", "client", client_id, "ok", org=org)
                result = _disposal(conn, disposal_id)
        audit.append(conn, actor, "disposal.approve", "disposal", disposal_id, outcome, org=org)
    return _finish(error, result)


def cancel_disposal(actor: str, org: str, disposal_id: str) -> dict[str, Any]:
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        request = conn.execute("SELECT * FROM disposals WHERE id = ? AND org_id = ?", (disposal_id, org)).fetchone()
        if request is None:
            error, outcome = RecordNotFound(disposal_id), "denied_or_missing"
        elif request["state"] != "requested":
            error, outcome = TransitionNotAllowed(f"Disposal is already {request['state']}."), "rejected_state"
        else:
            error, outcome = None, "ok"
            conn.execute(
                "UPDATE disposals SET state = 'cancelled', decided_by = ?, decided_at = ? WHERE id = ? AND state = 'requested'",
                (actor, audit.now(), disposal_id),
            )
            result = _disposal(conn, disposal_id)
        audit.append(conn, actor, "disposal.cancel", "disposal", disposal_id, outcome, org=org)
    return _finish(error, result)


def list_disposals(actor: str, org: str) -> list[dict[str, Any]]:
    with db.transaction() as conn:
        rows = conn.execute(
            f"SELECT {_DISPOSAL_COLUMNS} FROM disposals WHERE org_id = ? ORDER BY requested_at", (org,)
        ).fetchall()
        audit.append(conn, actor, "disposal.list", "disposal", None, "ok", org=org)
    return rows


__all__ = [
    "RETENTION_ENV", "RetentionNotConfigured", "NotEligible", "SecondPersonRequired", "InvalidInput", "policy",
    "record_consent", "list_consents", "withdraw_consent", "place_hold", "release_hold", "list_holds",
    "due_for_disposal", "request_disposal", "approve_disposal", "cancel_disposal", "list_disposals",
]
