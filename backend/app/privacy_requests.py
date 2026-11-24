"""Client access and correction requests (Privacy Act 2020, information privacy
principles 6 and 7).

Roles:
- An admin (acting for the privacy officer) logs each request against a client,
  tracks it and closes it with an outcome. Admins see request metadata only, never
  clinical payloads.
- The client's owning clinician prepares the response: for an access request, an
  access-response export; for a correction request, either a correction (a new
  assessment version via the amendment workflow, or an update to the client
  record, so signed-off records stay immutable) or, when the correction is
  declined, a statement of correction supplied by the client, which is stored
  encrypted and attached to the client's records.

Due dates: the response period comes only from configuration. Nothing here asserts
the statutory period. STN_PRIVACY_RESPONSE_WORKING_DAYS sets the number of
working days after the day of receipt; weekends are never working days; dates in
STN_PRIVACY_NON_WORKING_DATES (comma-separated YYYY-MM-DD, for public holidays)
are skipped; STN_PRIVACY_EXCLUDE_SUMMER_PERIOD=true also skips 25 December to
15 January. The organisation's privacy officer must confirm the period, the
definition of a working day and the holiday list against the Act before relying
on these dates (the Act's 20-working-day rule for responding should be verified).
Without a valid configuration the request is still logged, with no due date, and
the policy endpoint reports that dates are not configured.

Exports: an access-response export is recorded in the export log (one row per
signed-off assessment it includes, reason code privacy_access_request) and in a
hash-chained audit event carrying the document's SHA-256, never the payload.
Everything is organisation-scoped and audited; other organisations' requests and
clients behave as missing.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from . import audit, db
from .assessments import (
    SIGNED_OFF, AssessmentNotFound, InvalidInput, TransitionNotAllowed, _meta, _note, _payload, content_hash,
)
from .crypto import decrypt_payload, encrypt_payload
from .store import RecordDisposed, RecordNotFound, client_aad, client_row

WORKING_DAYS_ENV = "STN_PRIVACY_RESPONSE_WORKING_DAYS"
NON_WORKING_ENV = "STN_PRIVACY_NON_WORKING_DATES"
SUMMER_ENV = "STN_PRIVACY_EXCLUDE_SUMMER_PERIOD"
ACCESS, CORRECTION = "access", "correction"
OPEN, RESPONDED, CLOSED = "open", "responded", "closed"
OUTCOMES = ("completed", "refused", "transferred", "withdrawn")
ACCESS_EXPORT_FORMAT = "stn-privacy-access-response/1"
ACCESS_EXPORT_REASON = "privacy_access_request"
BASIS_NOTE = (
    "Configured values only. The privacy officer must confirm the response period, the definition of a working "
    "day and the non-working dates against the Privacy Act 2020 (including its 20-working-day rule for "
    "responding to requests) before relying on these due dates."
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COLUMNS = (
    "id, client_id, kind, received_on, working_days, due_on, state, logged_by, logged_at, responded_by, "
    "responded_at, response_kind, response_hash, amended_assessment_id, outcome_code, closed_by, closed_at"
)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _finish(error: Exception | None, result: Any) -> Any:
    if error is not None:
        raise error
    return result


# --------------------------------------------------------------------------- due-date policy


def _parse_date(value: str) -> date:
    if not _DATE.match(value):
        raise ValueError(value)
    return date.fromisoformat(value)


def policy() -> dict[str, Any]:
    raw_days = os.getenv(WORKING_DAYS_ENV, "").strip()
    problems: list[str] = []
    days: int | None = None
    try:
        days = int(raw_days) if raw_days else None
        if days is not None and days <= 0:
            problems.append(f"{WORKING_DAYS_ENV} must be a positive whole number.")
            days = None
    except ValueError:
        problems.append(f"{WORKING_DAYS_ENV} must be a positive whole number.")
    holidays: list[date] = []
    for item in (v.strip() for v in os.getenv(NON_WORKING_ENV, "").split(",") if v.strip()):
        try:
            holidays.append(_parse_date(item))
        except ValueError:
            problems.append(f"{NON_WORKING_ENV} contains an invalid date: {item!r}.")
    summer = os.getenv(SUMMER_ENV, "false").strip().lower() in {"true", "1", "yes", "on"}
    configured = days is not None and not problems
    return {
        "configured": configured,
        "response_working_days": days if configured else None,
        "non_working_dates": sorted(d.isoformat() for d in holidays),
        "exclude_25_december_to_15_january": summer,
        "problems": problems or ([] if days is not None else [f"{WORKING_DAYS_ENV} is not set."]),
        "basis_note": BASIS_NOTE,
    }


def _is_working_day(day: date, holidays: set[date], summer: bool) -> bool:
    if day.weekday() >= 5 or day in holidays:
        return False
    if summer and ((day.month == 12 and day.day >= 25) or (day.month == 1 and day.day <= 15)):
        return False
    return True


def due_date(received_on: date, working_days: int, holidays: set[date], summer: bool) -> date:
    """The date that is `working_days` working days after the day of receipt."""
    day, counted = received_on, 0
    while counted < working_days:
        day += timedelta(days=1)
        if _is_working_day(day, holidays, summer):
            counted += 1
    return day


def _with_status(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if row["due_on"] and row["state"] != CLOSED:
        remaining = (date.fromisoformat(row["due_on"]) - _today()).days
        out["days_until_due"] = remaining
        out["overdue"] = remaining < 0
    else:
        out["days_until_due"] = None
        out["overdue"] = False
    return out


def _request(conn: db.Conn, request_id: str, org: str) -> dict[str, Any] | None:
    return conn.execute(f"SELECT {_COLUMNS}, org_id FROM privacy_requests WHERE id = ? AND org_id = ?",
                        (request_id, org)).fetchone()


def _public(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return _with_status({k: v for k, v in row.items() if k != "org_id"})


# --------------------------------------------------------------------------- admin: log, list, close


def log_request(actor: str, org: str, client_id: Any, kind: Any, received_on: Any) -> dict[str, Any]:
    if kind not in (ACCESS, CORRECTION):
        raise InvalidInput("kind must be 'access' or 'correction'.")
    if not isinstance(client_id, str) or not client_id:
        raise InvalidInput("client_id is required.")
    try:
        received = _parse_date(received_on) if isinstance(received_on, str) else None
    except ValueError:
        received = None
    if received is None:
        raise InvalidInput("received_on must be a date in YYYY-MM-DD form.")
    if received > _today():
        raise InvalidInput("received_on cannot be in the future.")
    rules = policy()
    due: str | None = None
    if rules["configured"]:
        holidays = {date.fromisoformat(d) for d in rules["non_working_dates"]}
        due = due_date(received, rules["response_working_days"], holidays,
                       rules["exclude_25_december_to_15_january"]).isoformat()
    request_id = str(uuid.uuid4())
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        client = client_row(conn, client_id, org)
        if client is None:
            error, outcome = RecordNotFound(client_id), "denied_or_missing"
        elif client["disposed_at"] is not None:
            error, outcome = RecordDisposed(client_id), "rejected_disposed"
        else:
            error, outcome = None, "ok"
            conn.execute(
                "INSERT INTO privacy_requests (id, org_id, client_id, kind, received_on, working_days, due_on, state, "
                "logged_by, logged_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (request_id, org, client_id, kind, received.isoformat(),
                 rules["response_working_days"] if rules["configured"] else None, due, OPEN, actor, audit.now()),
            )
            result = _public(_request(conn, request_id, org)) | {"due_date_configured": rules["configured"]}
        audit.append(conn, actor, "privacy_request.log", "client", client_id, outcome, org=org)
    return _finish(error, result)


def list_requests(actor: str, org: str, state: str | None = None) -> list[dict[str, Any]]:
    if state is not None and state not in (OPEN, RESPONDED, CLOSED):
        raise InvalidInput("state must be open, responded or closed.")
    with db.transaction() as conn:
        sql = f"SELECT {_COLUMNS} FROM privacy_requests WHERE org_id = ?"
        params: list[Any] = [org]
        if state is not None:
            sql += " AND state = ?"
            params.append(state)
        rows = conn.execute(sql + " ORDER BY received_on, logged_at", tuple(params)).fetchall()
        audit.append(conn, actor, "privacy_request.list", "privacy_request", None, "ok", org=org)
    return [_with_status(r) for r in rows]


def close_request(actor: str, org: str, request_id: str, outcome_code: Any) -> dict[str, Any]:
    if outcome_code not in OUTCOMES:
        raise InvalidInput(f"outcome_code must be one of {', '.join(OUTCOMES)}.")
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = _request(conn, request_id, org)
        if row is None:
            error, outcome = RecordNotFound(request_id), "denied_or_missing"
        elif row["state"] == CLOSED:
            error, outcome = TransitionNotAllowed("This request is already closed."), "rejected_state"
        elif outcome_code == "completed" and row["state"] != RESPONDED:
            error = TransitionNotAllowed("A request is completed only after its response has been recorded.")
            outcome = "rejected_no_response"
        else:
            error, outcome = None, "ok"
            conn.execute(
                "UPDATE privacy_requests SET state = ?, outcome_code = ?, closed_by = ?, closed_at = ? "
                "WHERE id = ? AND state <> ?",
                (CLOSED, outcome_code, actor, audit.now(), request_id, CLOSED),
            )
            result = _public(_request(conn, request_id, org))
        audit.append(conn, actor, "privacy_request.close", "privacy_request", request_id, outcome, org=org)
    return _finish(error, result)


# --------------------------------------------------------------------------- clinician: respond


def _owned_open(conn: db.Conn, actor: str, org: str, request_id: str, kind: str
                ) -> tuple[dict | None, dict | None, Exception | None, str]:
    row = _request(conn, request_id, org)
    client = client_row(conn, row["client_id"], org) if row else None
    if row is None or client is None or client["owner_sub"] != actor:
        return row, client, RecordNotFound(request_id), "denied_or_missing"
    if client["disposed_at"] is not None:
        return row, client, RecordDisposed(row["client_id"]), "rejected_disposed"
    if row["kind"] != kind:
        return row, client, TransitionNotAllowed(f"This is a {row['kind']} request."), "rejected_kind"
    if row["state"] != OPEN:
        return row, client, TransitionNotAllowed(f"This request is already {row['state']}."), "rejected_state"
    return row, client, None, "ok"


def _statement_aad(statement_id: str, client_id: str) -> bytes:
    return f"correction-statement\x1f{statement_id}\x1f{client_id}".encode("utf-8")


def _statements(conn: db.Conn, org: str, client_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM correction_statements WHERE org_id = ? AND client_id = ? AND disposed_at IS NULL "
        "ORDER BY attached_at, id",
        (org, client_id),
    ).fetchall()
    return [{
        "id": r["id"],
        "privacy_request_id": r["privacy_request_id"],
        "attached_by": r["attached_by"],
        "attached_at": r["attached_at"],
        "statement": decrypt_payload(r["statement_ciphertext"], _statement_aad(r["id"], client_id))["statement"],
    } for r in rows]


def access_response(actor: str, org: str, request_id: str) -> dict[str, Any]:
    """The owning clinician prepares the access-response export for the privacy officer."""
    error: Exception | None = None
    document: dict[str, Any] | None = None
    export_hash: str | None = None
    with db.transaction() as conn:
        row, client, error, outcome = _owned_open(conn, actor, org, request_id, ACCESS)
        if error is None:
            try:
                client_payload = decrypt_payload(client["ciphertext"], client_aad(client["id"], client["owner_sub"]))
                versions = conn.execute(
                    "SELECT * FROM assessments WHERE client_id = ? AND org_id = ? AND disposed_at IS NULL "
                    "ORDER BY created_at, version",
                    (client["id"], org),
                ).fetchall()
                included, signed_ids = [], []
                for version in versions:
                    if version["state"] == SIGNED_OFF:
                        included.append(_meta(version) | {"payload": _payload(version)})
                        signed_ids.append(version["id"])
                    else:
                        included.append(_meta(version) | {
                            "payload": None,
                            "release_note": "Not finalised. The privacy officer decides whether and how to release it.",
                        })
                statements = _statements(conn, org, client["id"])
            except Exception as exc:  # integrity or key failure: audit, then raise after commit
                error, outcome = exc, "integrity_failure"
            else:
                stamp = audit.now()
                document = {
                    "format": ACCESS_EXPORT_FORMAT,
                    "privacy_request_id": request_id,
                    "organisation": org,
                    "client_id": client["id"],
                    "prepared_by": actor,
                    "prepared_at": stamp,
                    "client_record": client_payload,
                    "assessments": included,
                    "correction_statements": statements,
                    "release_note": ("Prepared for the privacy officer. Check any grounds for withholding and "
                                     "material that is not finalised before release to the client."),
                }
                export_hash = content_hash(document)
                for assessment_id in signed_ids:
                    conn.execute(
                        "INSERT INTO exports (id, org_id, assessment_id, exported_by, exported_at, reason_code, "
                        "export_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), org, assessment_id, actor, stamp, ACCESS_EXPORT_REASON, export_hash),
                    )
                conn.execute(
                    "UPDATE privacy_requests SET state = ?, responded_by = ?, responded_at = ?, response_kind = ?, "
                    "response_hash = ? WHERE id = ? AND state = ?",
                    (RESPONDED, actor, stamp, "access_export", export_hash, request_id, OPEN),
                )
        audit.append(conn, actor, "privacy_request.access_response", "privacy_request", request_id, outcome,
                     org=org, content_hash=export_hash)
    return _finish(error, document and {"export": document, "export_hash": export_hash})


CORRECTION_ACTIONS = ("amended", "client_record_corrected", "declined")


def correction_response(actor: str, org: str, request_id: str, action: Any, assessment_id: Any = None,
                        statement: Any = None) -> dict[str, Any]:
    """Record how the owning clinician dealt with a correction request."""
    if action not in CORRECTION_ACTIONS:
        raise InvalidInput(f"action must be one of {', '.join(CORRECTION_ACTIONS)}.")
    statement_text = _note(statement, "statement") if action == "declined" else None
    if action == "amended" and (not isinstance(assessment_id, str) or not assessment_id):
        raise InvalidInput("assessment_id of the amended version is required.")
    statement_id = str(uuid.uuid4())
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        row, client, error, outcome = _owned_open(conn, actor, org, request_id, CORRECTION)
        amended_id = None
        if error is None and action == "amended":
            version = conn.execute(
                "SELECT * FROM assessments WHERE id = ? AND org_id = ?", (assessment_id, org)
            ).fetchone()
            if version is None or version["client_id"] != client["id"] or version["author_sub"] != actor:
                error, outcome = AssessmentNotFound(assessment_id), "denied_or_missing"
            elif version["parent_id"] is None:
                error = TransitionNotAllowed("Link the new version created by the amendment workflow, not an original.")
                outcome = "rejected_not_amendment"
            else:
                amended_id = assessment_id
        if error is None:
            stamp = audit.now()
            if statement_text is not None:
                blob = encrypt_payload({"statement": statement_text}, _statement_aad(statement_id, client["id"]))
                conn.execute(
                    "INSERT INTO correction_statements (id, org_id, client_id, privacy_request_id, statement_ciphertext, "
                    "attached_by, attached_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (statement_id, org, client["id"], request_id, blob, actor, stamp),
                )
                audit.append(conn, actor, "correction_statement.attach", "correction_statement", statement_id, "ok",
                             org=org)
            kind = {"amended": "amended_new_version", "client_record_corrected": "client_record_corrected",
                    "declined": "declined_statement_attached"}[action]
            conn.execute(
                "UPDATE privacy_requests SET state = ?, responded_by = ?, responded_at = ?, response_kind = ?, "
                "amended_assessment_id = ? WHERE id = ? AND state = ?",
                (RESPONDED, actor, stamp, kind, amended_id, request_id, OPEN),
            )
            result = _public(_request(conn, request_id, org))
        audit.append(conn, actor, "privacy_request.correction_response", "privacy_request", request_id, outcome,
                     org=org)
    return _finish(error, result)


def client_requests(actor: str, org: str, client_id: str) -> list[dict[str, Any]]:
    """Request metadata for the owning clinician's client."""
    with db.transaction() as conn:
        client = client_row(conn, client_id, org)
        if client is None or client["owner_sub"] != actor:
            error, outcome, rows = RecordNotFound(client_id), "denied_or_missing", []
        else:
            error, outcome = None, "ok"
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM privacy_requests WHERE org_id = ? AND client_id = ? ORDER BY received_on",
                (org, client_id),
            ).fetchall()
        audit.append(conn, actor, "privacy_request.list", "client", client_id, outcome, org=org)
    return _finish(error, [_with_status(r) for r in rows])


def correction_statements(actor: str, org: str, client_id: str) -> list[dict[str, Any]]:
    """Statements of correction attached to the owning clinician's client, decrypted."""
    error: Exception | None = None
    statements: list[dict[str, Any]] = []
    with db.transaction() as conn:
        client = client_row(conn, client_id, org)
        if client is None or client["owner_sub"] != actor:
            error, outcome = RecordNotFound(client_id), "denied_or_missing"
        elif client["disposed_at"] is not None:
            error, outcome = RecordDisposed(client_id), "rejected_disposed"
        else:
            try:
                statements = _statements(conn, org, client_id)
                outcome = "ok"
            except Exception as exc:
                error, outcome = exc, "integrity_failure"
        audit.append(conn, actor, "correction_statement.read", "client", client_id, outcome, org=org)
    return _finish(error, statements)


def statement_aad(statement_id: str, client_id: str) -> bytes:
    """Associated data for a stored statement (used by key rotation and restore checks)."""
    return _statement_aad(statement_id, client_id)
