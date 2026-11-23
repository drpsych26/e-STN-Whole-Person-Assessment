"""Assessment records and the human clinician review workflow.

State machine (only these transitions exist):

    draft --submit--> submitted --start_review--> in_review --sign_off--> signed_off
                                                   in_review --return--> returned --reopen--> draft

Rules enforced here and covered by tests:
- Payloads are generic JSON, encrypted at rest and bound to assessment id + author.
  This module adds no clinical questions, scales, scoring, routing or risk logic.
- Only the author edits, submits and reopens. Edits need the current revision.
- Only a user with the reviewer role who is not the author can start review, and
  only the reviewer who started it can return or sign off. Nobody signs off their own work.
- Safety flags raised at submission must each be acknowledged by a named human
  (the author or a reviewer) before review can start. Acknowledgement records who
  and when; it is not a risk disposition and triggers no automated action.
- Sign-off requires the reviewer to quote the content hash they reviewed; it
  records reviewer, time and hash. Signed-off rows are immutable (also enforced by
  a database trigger). Corrections are new versions linked by parent_id.
- Every access, change, transition, acknowledgement, export and denial is audited
  (hash-chained, no payloads). Denials are committed before the error is raised.
- Everything is scoped to the caller's organisation: another organisation's
  records behave exactly like missing ones.
- Reads of submitted, in-review, returned or signed-off work re-check the stored
  content hash, so an older ciphertext replayed into the row is detected.
- Disposed records (app.governance) keep metadata only; payload access, edits and
  transitions raise RecordDisposed.
- Export: only signed-off work, by its author (clinician) or the reviewer who
  signed it off, with a reason code. The export document's SHA-256 goes into the
  export log and the audit event; the payload never does.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any, Iterable

from . import audit, db
from .crypto import RecordIntegrityError, decrypt_payload, encrypt_payload
from .rbac import CLINICIAN, REVIEWER
from .store import RecordDisposed, client_row

__all__ = ["RecordDisposed"]

DRAFT, SUBMITTED, IN_REVIEW, RETURNED, SIGNED_OFF = "draft", "submitted", "in_review", "returned", "signed_off"
TRANSITIONS = {
    (DRAFT, SUBMITTED): "submit",
    (SUBMITTED, IN_REVIEW): "start_review",
    (IN_REVIEW, RETURNED): "return",
    (IN_REVIEW, SIGNED_OFF): "sign_off",
    (RETURNED, DRAFT): "reopen",
}

_CODE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
MAX_FLAGS = 50
MAX_NOTE_CHARS = 4000
EXPORT_FORMAT = "stn-assessment-export/1"
HASHED_STATES = frozenset({SUBMITTED, IN_REVIEW, RETURNED, SIGNED_OFF})


class AssessmentNotFound(LookupError):
    """Missing, or not visible to the caller. Same response either way (no enumeration)."""


class TransitionNotAllowed(RuntimeError):
    """The requested change is not permitted from the record's current state."""


class ReviewBlocked(RuntimeError):
    """Review cannot start while safety flags are unacknowledged."""


class SelfReviewForbidden(PermissionError):
    """A user may not review or sign off an assessment they authored."""


class RevisionConflict(RuntimeError):
    """The caller edited a stale revision."""


class ContentHashMismatch(RuntimeError):
    """The hash quoted at sign-off does not match the submitted content."""


class InvalidInput(ValueError):
    """Request data failed validation."""


def content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _aad(assessment_id: str, author: str) -> bytes:
    return f"assessment\x1f{assessment_id}\x1f{author}".encode("utf-8")


def _note_aad(assessment_id: str) -> bytes:
    return f"assessment-note\x1f{assessment_id}".encode("utf-8")


def _code(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _CODE.match(value):
        raise InvalidInput(f"{field} must be 1-64 characters of letters, digits, '_', '.', ':' or '-'.")
    return value


def _note(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInput(f"{field} is required.")
    if len(value) > MAX_NOTE_CHARS:
        raise InvalidInput(f"{field} exceeds {MAX_NOTE_CHARS} characters.")
    return value.strip()


def _meta(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id", "client_id", "version", "parent_id", "form_id", "form_version", "state", "revision",
        "submission", "content_hash", "author_sub", "reviewer_sub", "created_at", "updated_at",
        "submitted_at", "review_started_at", "returned_at", "signed_off_by", "signed_off_at", "disposed_at",
    )
    return {k: row[k] for k in keys}


def _load(conn: db.Conn, assessment_id: str, org: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT * FROM assessments WHERE id = ? AND org_id = ?", (assessment_id, org)
    ).fetchone()


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    """Decrypt and, for submitted work, check the content still matches its recorded hash."""
    payload = decrypt_payload(row["ciphertext"], _aad(row["id"], row["author_sub"]))
    if row["state"] in HASHED_STATES and content_hash(payload) != row["content_hash"]:
        raise RecordIntegrityError("Stored assessment does not match its recorded content hash.")
    return payload


def _can_read(row: dict[str, Any], actor: str, roles: Iterable[str]) -> bool:
    roles = set(roles)
    if CLINICIAN in roles and row["author_sub"] == actor:
        return True
    return REVIEWER in roles and row["reviewer_sub"] == actor


def _flags(conn: db.Conn, assessment_id: str, submission: int) -> list[dict[str, Any]]:
    return conn.execute(
        "SELECT id, code, raised_by, raised_at, acknowledged_by, acknowledged_at FROM safety_flags "
        "WHERE assessment_id = ? AND submission = ? ORDER BY code",
        (assessment_id, submission),
    ).fetchall()


def _unacknowledged(conn: db.Conn, assessment_id: str, submission: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM safety_flags WHERE assessment_id = ? AND submission = ? AND acknowledged_by IS NULL",
        (assessment_id, submission),
    ).fetchone()
    return int(row["n"])


def _finish(error: Exception | None, result: Any) -> Any:
    if error is not None:
        raise error
    return result


# --------------------------------------------------------------------------- create / read / edit


def create(actor: str, org: str, client_id: str, form_id: Any, form_version: Any,
           payload: dict[str, Any]) -> dict[str, Any]:
    form_id, form_version = _code(form_id, "form_id"), _code(form_version, "form_version")
    db.dialect()
    assessment_id = str(uuid.uuid4())
    blob = encrypt_payload(payload, _aad(assessment_id, actor))
    stamp = audit.now()
    error: Exception | None = None
    row: dict[str, Any] | None = None
    with db.transaction() as conn:
        client = client_row(conn, client_id, org)
        if client is None or client["owner_sub"] != actor:
            error = AssessmentNotFound(client_id)
            audit.append(conn, actor, "assessment.create", "client", client_id, "denied_or_missing", org=org)
        elif client["disposed_at"] is not None:
            error = RecordDisposed(client_id)
            audit.append(conn, actor, "assessment.create", "client", client_id, "rejected_disposed", org=org)
        else:
            conn.execute(
                "INSERT INTO assessments (id, org_id, client_id, author_sub, version, parent_id, form_id, form_version, "
                "state, revision, submission, ciphertext, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 1, NULL, ?, ?, ?, 1, 0, ?, ?, ?)",
                (assessment_id, org, client_id, actor, form_id, form_version, DRAFT, blob, stamp, stamp),
            )
            audit.append(conn, actor, "assessment.create", "assessment", assessment_id, "ok", org=org)
            row = _load(conn, assessment_id, org)
    return _finish(error, row and _meta(row))


def read(actor: str, org: str, roles: Iterable[str], assessment_id: str) -> dict[str, Any]:
    error: Exception | None = None
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = _load(conn, assessment_id, org)
        if row is None or not _can_read(row, actor, roles):
            error = AssessmentNotFound(assessment_id)
            audit.append(conn, actor, "assessment.read", "assessment", assessment_id, "denied_or_missing", org=org)
        elif row["disposed_at"] is not None:
            error = RecordDisposed(assessment_id)
            audit.append(conn, actor, "assessment.read", "assessment", assessment_id, "rejected_disposed", org=org)
        else:
            try:
                payload = _payload(row)
                note = None
                if row["note_ciphertext"] is not None:
                    note = decrypt_payload(row["note_ciphertext"], _note_aad(assessment_id))["note"]
            except Exception as exc:
                error = exc
                audit.append(conn, actor, "assessment.read", "assessment", assessment_id, "integrity_failure", org=org)
            else:
                result = _meta(row) | {
                    "payload": payload,
                    "note": note,
                    "safety_flags": _flags(conn, assessment_id, row["submission"]),
                }
                audit.append(conn, actor, "assessment.read", "assessment", assessment_id, "ok", org=org)
    return _finish(error, result)


def update(actor: str, org: str, assessment_id: str, payload: dict[str, Any], revision: Any) -> dict[str, Any]:
    if not isinstance(revision, int) or isinstance(revision, bool):
        raise InvalidInput("revision must be an integer.")
    db.dialect()
    blob = encrypt_payload(payload, _aad(assessment_id, actor))
    error: Exception | None = None
    row: dict[str, Any] | None = None
    with db.transaction() as conn:
        changed = conn.execute(
            "UPDATE assessments SET ciphertext = ?, revision = revision + 1, updated_at = ? "
            "WHERE id = ? AND org_id = ? AND author_sub = ? AND state = ? AND revision = ? AND disposed_at IS NULL",
            (blob, audit.now(), assessment_id, org, actor, DRAFT, revision),
        ).rowcount
        row = _load(conn, assessment_id, org)
        if changed:
            outcome = "ok"
        elif row is None or row["author_sub"] != actor:
            error, outcome = AssessmentNotFound(assessment_id), "denied_or_missing"
        elif row["disposed_at"] is not None:
            error, outcome = RecordDisposed(assessment_id), "rejected_disposed"
        elif row["state"] != DRAFT:
            error, outcome = TransitionNotAllowed("Only draft assessments can be edited."), "rejected_state"
        else:
            error, outcome = RevisionConflict("The assessment changed; reload and retry."), "rejected_revision"
        audit.append(conn, actor, "assessment.edit", "assessment", assessment_id, outcome, org=org)
    return _finish(error, row and _meta(row))


def list_for_client(actor: str, org: str, client_id: str) -> list[dict[str, Any]]:
    """Metadata only. Disposed versions are listed as tombstones (disposed_at set)."""
    error: Exception | None = None
    rows: list[dict[str, Any]] = []
    with db.transaction() as conn:
        client = client_row(conn, client_id, org)
        if client is None or client["owner_sub"] != actor:
            error = AssessmentNotFound(client_id)
            audit.append(conn, actor, "assessment.list", "client", client_id, "denied_or_missing", org=org)
        else:
            rows = conn.execute(
                "SELECT * FROM assessments WHERE client_id = ? AND org_id = ? ORDER BY created_at, version",
                (client_id, org),
            ).fetchall()
            audit.append(conn, actor, "assessment.list", "client", client_id, "ok", org=org)
    return _finish(error, [_meta(r) for r in rows])


# --------------------------------------------------------------------------- workflow


def submit(actor: str, org: str, assessment_id: str, safety_flags: Any) -> dict[str, Any]:
    if safety_flags is None:
        safety_flags = []
    if not isinstance(safety_flags, list) or len(safety_flags) > MAX_FLAGS:
        raise InvalidInput(f"safety_flags must be a list of at most {MAX_FLAGS} codes.")
    codes = sorted({_code(c, "safety flag code") for c in safety_flags})
    error: Exception | None = None
    row: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = _load(conn, assessment_id, org)
        if row is None or row["author_sub"] != actor:
            error, outcome = AssessmentNotFound(assessment_id), "denied_or_missing"
        elif row["disposed_at"] is not None:
            error, outcome = RecordDisposed(assessment_id), "rejected_disposed"
        elif row["state"] != DRAFT:
            error, outcome = TransitionNotAllowed(f"Cannot submit from state '{row['state']}'."), "rejected_state"
        else:
            try:
                digest = content_hash(decrypt_payload(row["ciphertext"], _aad(assessment_id, actor)))
            except Exception as exc:
                error, outcome = exc, "integrity_failure"
            else:
                stamp = audit.now()
                submission = row["submission"] + 1
                conn.execute(
                    "UPDATE assessments SET state = ?, submission = ?, content_hash = ?, submitted_at = ?, "
                    "reviewer_sub = NULL, review_started_at = NULL, updated_at = ? WHERE id = ? AND state = ?",
                    (SUBMITTED, submission, digest, stamp, stamp, assessment_id, DRAFT),
                )
                for code in codes:
                    flag_id = str(uuid.uuid4())
                    conn.execute(
                        "INSERT INTO safety_flags (id, assessment_id, submission, code, raised_by, raised_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (flag_id, assessment_id, submission, code, actor, stamp),
                    )
                    audit.append(conn, actor, "safety_flag.raise", "safety_flag", flag_id, "ok", org=org)
                outcome = "ok"
        audit.append(conn, actor, "assessment.submit", "assessment", assessment_id, outcome, org=org)
        row = _load(conn, assessment_id, org)
    return _finish(error, row and _meta(row))


def review_queue(actor: str, org: str) -> list[dict[str, Any]]:
    """Metadata only (no payloads): submitted work by others in the organisation, plus reviews held."""
    with db.transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM assessments WHERE org_id = ? AND disposed_at IS NULL AND "
            "((state = ? AND author_sub <> ?) OR (state = ? AND reviewer_sub = ?)) ORDER BY submitted_at",
            (org, SUBMITTED, actor, IN_REVIEW, actor),
        ).fetchall()
        queue = [_meta(r) | {"unacknowledged_safety_flags": _unacknowledged(conn, r["id"], r["submission"])}
                 for r in rows]
        audit.append(conn, actor, "review_queue.read", "review_queue", None, "ok", org=org)
    return queue


def list_flags(actor: str, org: str, roles: Iterable[str], assessment_id: str) -> list[dict[str, Any]]:
    """Flag metadata for the author, or for any reviewer while the work awaits or is in review."""
    roles = set(roles)
    error: Exception | None = None
    flags: list[dict[str, Any]] = []
    with db.transaction() as conn:
        row = _load(conn, assessment_id, org)
        visible = row is not None and (
            (CLINICIAN in roles and row["author_sub"] == actor)
            or (REVIEWER in roles and row["state"] in (SUBMITTED, IN_REVIEW) and row["author_sub"] != actor)
            or (REVIEWER in roles and row["reviewer_sub"] == actor)
        )
        if not visible:
            error = AssessmentNotFound(assessment_id)
            audit.append(conn, actor, "safety_flag.list", "assessment", assessment_id, "denied_or_missing", org=org)
        else:
            flags = _flags(conn, assessment_id, row["submission"])
            audit.append(conn, actor, "safety_flag.list", "assessment", assessment_id, "ok", org=org)
    return _finish(error, flags)


def acknowledge_flag(actor: str, org: str, roles: Iterable[str], assessment_id: str, flag_id: str) -> dict[str, Any]:
    roles = set(roles)
    error: Exception | None = None
    flag: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = _load(conn, assessment_id, org)
        allowed = row is not None and (
            (CLINICIAN in roles and row["author_sub"] == actor)
            or (REVIEWER in roles and row["state"] in (SUBMITTED, IN_REVIEW))
        )
        current = None
        if allowed:
            current = conn.execute(
                "SELECT * FROM safety_flags WHERE id = ? AND assessment_id = ? AND submission = ?",
                (flag_id, assessment_id, row["submission"]),
            ).fetchone()
        if not allowed or current is None:
            error, outcome = AssessmentNotFound(flag_id), "denied_or_missing"
        elif row["state"] not in (SUBMITTED, IN_REVIEW):
            error, outcome = TransitionNotAllowed("Flags can be acknowledged only while submitted or in review."), "rejected_state"
        elif current["acknowledged_by"] is not None:
            error, outcome = TransitionNotAllowed("This safety flag has already been acknowledged."), "rejected_duplicate"
        else:
            conn.execute(
                "UPDATE safety_flags SET acknowledged_by = ?, acknowledged_at = ? WHERE id = ? AND acknowledged_by IS NULL",
                (actor, audit.now(), flag_id),
            )
            outcome = "ok"
            flag = conn.execute(
                "SELECT id, code, raised_by, raised_at, acknowledged_by, acknowledged_at FROM safety_flags WHERE id = ?",
                (flag_id,),
            ).fetchone()
        audit.append(conn, actor, "safety_flag.acknowledge", "safety_flag", flag_id, outcome, org=org)
    return _finish(error, flag)


def start_review(actor: str, org: str, assessment_id: str) -> dict[str, Any]:
    error: Exception | None = None
    row: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = _load(conn, assessment_id, org)
        if row is None:
            error, outcome = AssessmentNotFound(assessment_id), "denied_or_missing"
        elif row["author_sub"] == actor:
            error, outcome = SelfReviewForbidden("You cannot review an assessment you authored."), "rejected_self_review"
        elif row["state"] != SUBMITTED:
            error, outcome = TransitionNotAllowed(f"Cannot start review from state '{row['state']}'."), "rejected_state"
        elif _unacknowledged(conn, assessment_id, row["submission"]):
            error = ReviewBlocked("Every safety flag must be acknowledged by a clinician or reviewer before review starts.")
            outcome = "rejected_unacknowledged_flags"
        else:
            stamp = audit.now()
            changed = conn.execute(
                "UPDATE assessments SET state = ?, reviewer_sub = ?, review_started_at = ?, updated_at = ? "
                "WHERE id = ? AND state = ? AND author_sub <> ?",
                (IN_REVIEW, actor, stamp, stamp, assessment_id, SUBMITTED, actor),
            ).rowcount
            if changed:
                outcome = "ok"
            else:
                error, outcome = TransitionNotAllowed("Review was started by someone else."), "rejected_state"
        audit.append(conn, actor, "assessment.start_review", "assessment", assessment_id, outcome, org=org)
        row = _load(conn, assessment_id, org)
    return _finish(error, row and _meta(row))


def _held_review(
    conn: db.Conn, actor: str, org: str, assessment_id: str
) -> tuple[dict[str, Any] | None, Exception | None, str]:
    row = _load(conn, assessment_id, org)
    if row is None or (row["reviewer_sub"] != actor and row["author_sub"] != actor):
        return row, AssessmentNotFound(assessment_id), "denied_or_missing"
    if row["author_sub"] == actor:
        return row, SelfReviewForbidden("You cannot review or sign off an assessment you authored."), "rejected_self_review"
    if row["state"] != IN_REVIEW:
        return row, TransitionNotAllowed(f"Not in review (state '{row['state']}')."), "rejected_state"
    return row, None, "ok"


def return_for_changes(actor: str, org: str, assessment_id: str, reason: Any) -> dict[str, Any]:
    reason = _note(reason, "reason")
    db.dialect()
    note_blob = encrypt_payload({"note": reason}, _note_aad(assessment_id))
    with db.transaction() as conn:
        row, error, outcome = _held_review(conn, actor, org, assessment_id)
        if error is None:
            stamp = audit.now()
            conn.execute(
                "UPDATE assessments SET state = ?, returned_at = ?, note_ciphertext = ?, updated_at = ? "
                "WHERE id = ? AND state = ? AND reviewer_sub = ?",
                (RETURNED, stamp, note_blob, stamp, assessment_id, IN_REVIEW, actor),
            )
        audit.append(conn, actor, "assessment.return", "assessment", assessment_id, outcome, org=org)
        row = _load(conn, assessment_id, org)
    return _finish(error, row and _meta(row))


def sign_off(actor: str, org: str, assessment_id: str, quoted_hash: Any) -> dict[str, Any]:
    if not isinstance(quoted_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", quoted_hash):
        raise InvalidInput("content_hash must be the 64-character SHA-256 hex digest that was reviewed.")
    with db.transaction() as conn:
        row, error, outcome = _held_review(conn, actor, org, assessment_id)
        if error is None:
            try:
                actual = content_hash(decrypt_payload(row["ciphertext"], _aad(assessment_id, row["author_sub"])))
            except Exception as exc:
                error, outcome = exc, "integrity_failure"
            else:
                if not (actual == row["content_hash"] == quoted_hash):
                    error = ContentHashMismatch("The content hash does not match the submitted assessment.")
                    outcome = "rejected_hash_mismatch"
                else:
                    stamp = audit.now()
                    conn.execute(
                        "UPDATE assessments SET state = ?, signed_off_by = ?, signed_off_at = ?, updated_at = ? "
                        "WHERE id = ? AND state = ? AND reviewer_sub = ? AND author_sub <> ?",
                        (SIGNED_OFF, actor, stamp, stamp, assessment_id, IN_REVIEW, actor, actor),
                    )
        audit.append(conn, actor, "assessment.sign_off", "assessment", assessment_id, outcome, org=org)
        row = _load(conn, assessment_id, org)
    return _finish(error, row and _meta(row))


def reopen(actor: str, org: str, assessment_id: str) -> dict[str, Any]:
    error: Exception | None = None
    with db.transaction() as conn:
        row = _load(conn, assessment_id, org)
        if row is None or row["author_sub"] != actor:
            error, outcome = AssessmentNotFound(assessment_id), "denied_or_missing"
        elif row["disposed_at"] is not None:
            error, outcome = RecordDisposed(assessment_id), "rejected_disposed"
        elif row["state"] != RETURNED:
            error, outcome = TransitionNotAllowed(f"Cannot reopen from state '{row['state']}'."), "rejected_state"
        else:
            conn.execute(
                "UPDATE assessments SET state = ?, updated_at = ? WHERE id = ? AND state = ? AND author_sub = ?",
                (DRAFT, audit.now(), assessment_id, RETURNED, actor),
            )
            outcome = "ok"
        audit.append(conn, actor, "assessment.reopen", "assessment", assessment_id, outcome, org=org)
        row = _load(conn, assessment_id, org)
    return _finish(error, row and _meta(row))


def amend(actor: str, org: str, parent_id: str, payload: dict[str, Any], reason: Any) -> dict[str, Any]:
    """Create a new draft version of a signed-off assessment. The original is never changed."""
    reason = _note(reason, "reason")
    db.dialect()
    new_id = str(uuid.uuid4())
    blob = encrypt_payload(payload, _aad(new_id, actor))
    note_blob = encrypt_payload({"note": reason}, _note_aad(new_id))
    error: Exception | None = None
    row: dict[str, Any] | None = None
    with db.transaction() as conn:
        parent = _load(conn, parent_id, org)
        if parent is None or parent["author_sub"] != actor:
            error, outcome = AssessmentNotFound(parent_id), "denied_or_missing"
        elif parent["disposed_at"] is not None:
            error, outcome = RecordDisposed(parent_id), "rejected_disposed"
        elif parent["state"] != SIGNED_OFF:
            error, outcome = TransitionNotAllowed("Only signed-off assessments are amended; edit drafts directly."), "rejected_state"
        elif conn.execute("SELECT 1 AS x FROM assessments WHERE parent_id = ?", (parent_id,)).fetchone():
            error, outcome = TransitionNotAllowed("A newer version exists; amend the latest version."), "rejected_superseded"
        else:
            stamp = audit.now()
            conn.execute(
                "INSERT INTO assessments (id, org_id, client_id, author_sub, version, parent_id, form_id, form_version, "
                "state, revision, submission, ciphertext, note_ciphertext, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?)",
                (new_id, org, parent["client_id"], actor, parent["version"] + 1, parent_id, parent["form_id"],
                 parent["form_version"], DRAFT, blob, note_blob, stamp, stamp),
            )
            audit.append(conn, actor, "assessment.create", "assessment", new_id, "ok", org=org)
            outcome = "ok"
            row = _load(conn, new_id, org)
        audit.append(conn, actor, "assessment.amend", "assessment", parent_id, outcome, org=org)
    return _finish(error, row and _meta(row))


# --------------------------------------------------------------------------- export


def export(actor: str, org: str, roles: Iterable[str], assessment_id: str, reason_code: Any) -> dict[str, Any]:
    """Export one signed-off assessment as a JSON document and log it.

    Allowed for its author (clinician role) or the reviewer who signed it off
    (reviewer role). The export log and the audit event hold the document hash
    and reason code, never the payload.
    """
    reason_code = _code(reason_code, "reason_code")
    roles = set(roles)
    error: Exception | None = None
    document: dict[str, Any] | None = None
    export_hash: str | None = None
    with db.transaction() as conn:
        row = _load(conn, assessment_id, org)
        visible = row is not None and (
            (CLINICIAN in roles and row["author_sub"] == actor)
            or (REVIEWER in roles and row["signed_off_by"] == actor)
        )
        if not visible:
            error, outcome = AssessmentNotFound(assessment_id), "denied_or_missing"
        elif row["disposed_at"] is not None:
            error, outcome = RecordDisposed(assessment_id), "rejected_disposed"
        elif row["state"] != SIGNED_OFF:
            error, outcome = TransitionNotAllowed("Only signed-off assessments can be exported."), "rejected_state"
        else:
            try:
                payload = _payload(row)
            except Exception as exc:
                error, outcome = exc, "integrity_failure"
            else:
                stamp = audit.now()
                document = {
                    "format": EXPORT_FORMAT,
                    "exported_at": stamp,
                    "exported_by": actor,
                    "reason_code": reason_code,
                    "organisation": org,
                    "assessment": _meta(row),
                    "payload": payload,
                }
                export_hash = content_hash(document)
                conn.execute(
                    "INSERT INTO exports (id, org_id, assessment_id, exported_by, exported_at, reason_code, export_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), org, assessment_id, actor, stamp, reason_code, export_hash),
                )
                outcome = "ok"
        audit.append(conn, actor, "assessment.export", "assessment", assessment_id, outcome, org=org,
                     content_hash=export_hash)
    return _finish(error, document and {"export": document, "export_hash": export_hash})
