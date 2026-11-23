"""Reviewer assignment and the reassignment queue.

Rules (enforced here and in app.assessments.start_review; covered by tests):
- An admin of the organisation assigns a named reviewer to a submitted assessment.
  Assigning again replaces the current assignment (a reassignment); the earlier row
  is ended, never deleted.
- Refused: assigning yourself (self-assignment), assigning the assessment's author
  (self-review), assigning a subject whose account is not usable in the
  organisation (app.accounts: suspended, deactivated, invited, or unregistered
  when registration is required), and assigning anything not in the submitted state.
- Only the assigned reviewer can start review. With no assignment, review can start
  only when STN_REVIEW_ASSIGNMENT_REQUIRED is false.
- Assignments belong to one submission. Resubmission ends them; deactivating a
  reviewer ends theirs, returning the work to the reassignment queue.
- The reassignment queue lists submitted work that is unassigned, or assigned for
  longer than the stale threshold without review starting
  (STN_REVIEW_ASSIGNMENT_STALE_HOURS, default 48, or a per-request value).
- Everything is audited (hash-chained, no payloads). Metadata only; admins get no
  payload access.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from . import accounts, audit, db
from .assessments import (
    SUBMITTED, AssessmentNotFound, SelfReviewForbidden, TransitionNotAllowed, _load, _unacknowledged,
    current_assignment,
)
from .store import RecordDisposed

STALE_ENV = "STN_REVIEW_ASSIGNMENT_STALE_HOURS"
DEFAULT_STALE_HOURS = 48


class SelfAssignmentForbidden(PermissionError):
    """An admin may not assign themselves as reviewer."""


def stale_hours() -> int:
    try:
        value = int(os.getenv(STALE_ENV, "").strip() or DEFAULT_STALE_HOURS)
    except ValueError:
        value = DEFAULT_STALE_HOURS
    return max(1, value)


def _finish(error: Exception | None, result: Any) -> Any:
    if error is not None:
        raise error
    return result


def assign(actor: str, org: str, assessment_id: str, reviewer_sub: Any) -> dict[str, Any]:
    reviewer_sub = accounts.valid_subject(reviewer_sub)
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = _load(conn, assessment_id, org)
        action = "review.assign"
        if row is None:
            error, outcome = AssessmentNotFound(assessment_id), "denied_or_missing"
        elif row["disposed_at"] is not None:
            error, outcome = RecordDisposed(assessment_id), "rejected_disposed"
        elif row["state"] != SUBMITTED:
            error = TransitionNotAllowed("Reviewers are assigned while an assessment is submitted, before review starts.")
            outcome = "rejected_state"
        elif reviewer_sub == actor:
            error, outcome = SelfAssignmentForbidden("You cannot assign yourself as reviewer."), "rejected_self_assignment"
        elif reviewer_sub == row["author_sub"]:
            error, outcome = SelfReviewForbidden("The author cannot review their own assessment."), "rejected_self_review"
        elif not accounts.usable(conn, org, reviewer_sub):
            error = accounts.AccountNotUsable("The reviewer's account is not active in this organisation.")
            outcome = "rejected_reviewer_not_active"
        else:
            current = current_assignment(conn, org, assessment_id, row["submission"])
            if current is not None and current["reviewer_sub"] == reviewer_sub:
                error = TransitionNotAllowed("This reviewer is already assigned.")
                outcome = "rejected_duplicate"
            else:
                error, outcome = None, "ok"
                stamp = audit.now()
                if current is not None:
                    action = "review.reassign"
                    conn.execute(
                        "UPDATE review_assignments SET ended_by = ?, ended_at = ?, end_reason = 'reassigned' "
                        "WHERE id = ? AND ended_at IS NULL",
                        (actor, stamp, current["id"]),
                    )
                assignment_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO review_assignments (id, org_id, assessment_id, submission, reviewer_sub, assigned_by, "
                    "assigned_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (assignment_id, org, assessment_id, row["submission"], reviewer_sub, actor, stamp),
                )
                result = {
                    "assessment_id": assessment_id,
                    "submission": row["submission"],
                    "reviewer_sub": reviewer_sub,
                    "assigned_by": actor,
                    "assigned_at": stamp,
                    "replaced_reviewer_sub": current["reviewer_sub"] if current else None,
                }
        audit.append(conn, actor, action, "assessment", assessment_id, outcome, org=org)
    return _finish(error, result)


def assignment_history(actor: str, org: str, assessment_id: str) -> list[dict[str, Any]]:
    with db.transaction() as conn:
        row = _load(conn, assessment_id, org)
        if row is None:
            error, outcome, rows = AssessmentNotFound(assessment_id), "denied_or_missing", []
        else:
            error, outcome = None, "ok"
            rows = conn.execute(
                "SELECT submission, reviewer_sub, assigned_by, assigned_at, ended_by, ended_at, end_reason "
                "FROM review_assignments WHERE org_id = ? AND assessment_id = ? ORDER BY assigned_at, id",
                (org, assessment_id),
            ).fetchall()
        audit.append(conn, actor, "review_assignment.history", "assessment", assessment_id, outcome, org=org)
    return _finish(error, rows)


def reassignment_queue(actor: str, org: str, older_than_hours: int | None = None) -> list[dict[str, Any]]:
    """Submitted work that is unassigned, or assigned longer than the threshold without review starting."""
    hours = older_than_hours if older_than_hours is not None else stale_hours()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    queue: list[dict[str, Any]] = []
    with db.transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM assessments WHERE org_id = ? AND state = ? AND disposed_at IS NULL ORDER BY submitted_at",
            (org, SUBMITTED),
        ).fetchall()
        for r in rows:
            current = current_assignment(conn, org, r["id"], r["submission"])
            if current is None:
                reason = "unassigned"
            elif datetime.fromisoformat(current["assigned_at"]) < cutoff:
                reason = "stale"
            else:
                continue
            queue.append({
                "id": r["id"],
                "client_id": r["client_id"],
                "author_sub": r["author_sub"],
                "form_id": r["form_id"],
                "submission": r["submission"],
                "submitted_at": r["submitted_at"],
                "assigned_reviewer": current["reviewer_sub"] if current else None,
                "assigned_at": current["assigned_at"] if current else None,
                "reason": reason,
                "unacknowledged_safety_flags": _unacknowledged(conn, r["id"], r["submission"]),
            })
        audit.append(conn, actor, "review_assignment.queue.read", "review_queue", None, "ok", org=org)
    return queue
