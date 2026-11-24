"""Safety escalations: open, acknowledge (take ownership) and resolve, with unresolved-case monitoring.

This complements app.assessments' safety flags (raised at submission, acknowledged before
review). An escalation tracks a safety concern about a client through to a documented
outcome, whether it came from an assessment item, an acknowledged flag, a clinician's own
report, client contact or a third-party report.

Rules (enforced here and by the schema; covered by tests/test_safety_escalations.py):
- Clinical staff (clinician or reviewer role) open, acknowledge and resolve. Admins see the
  monitoring queue (identifiers, codes and times only) but cannot act: administrative
  privilege is not clinical authority.
- Severity is one of four tiers (routine_monitoring, increased_concern, urgent_assessment,
  immediate_emergency) and is fixed once opened. If concern rises, open a new escalation at
  the higher tier; the earlier one stays on record.
- Acknowledging makes the acknowledging clinician the owner. Ownership can be taken over by
  another clinical user (handover); every change is audited.
- Resolution needs an acknowledged escalation, a coded outcome and a documentation reference:
  an assessment of the same client in the same organisation. Free text is not accepted.
- Resolved escalations are final. Rows are never deleted (schema triggers).
- An escalation is overdue when it is still open (unacknowledged) past its tier's
  acknowledgement window. Windows come from STN_SAFETY_ACK_MINUTES and default to the
  placeholder values below, which are PENDING CLINICAL APPROVAL
  (docs/clinical/SAFETY-ESCALATION-MATRIX.md).

What this module does not do (deliberately): it does not page, text or email anyone and it
does not imply anyone is watching the queue. A positive screen is not a risk classification:
the tier is a clinician's judgement recorded by that clinician. For immediate danger the
client-facing instruction is always to call 111; nothing here replaces that.

Codes and identifiers only enter the database and the audit chain; no clinical content.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from . import audit, db

SEVERITIES = ("routine_monitoring", "increased_concern", "urgent_assessment", "immediate_emergency")
SOURCES = frozenset({"assessment_item", "safety_flag", "clinician_report", "client_contact", "third_party_report"})
RESOLUTION_CODES = frozenset({
    "emergency_services_contacted", "referred_crisis_team", "safety_plan_agreed",
    "urgent_appointment_booked", "monitoring_plan_documented", "no_current_risk_documented",
})
ACK_ENV = "STN_SAFETY_ACK_MINUTES"
# PLACEHOLDER acknowledgement windows (minutes). Not clinically approved. See module docstring.
DEFAULT_ACK_MINUTES = {
    "immediate_emergency": 5,
    "urgent_assessment": 60,
    "increased_concern": 24 * 60,
    "routine_monitoring": 7 * 24 * 60,
}
_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class EscalationError(Exception):
    """Base class; routes map subclasses to HTTP status codes."""


class EscalationNotFound(EscalationError):
    pass


class EscalationInvalidInput(EscalationError):
    pass


class EscalationStateConflict(EscalationError):
    pass


def ack_minutes() -> dict[str, int]:
    """Per-tier acknowledgement windows: STN_SAFETY_ACK_MINUTES='immediate_emergency=5,urgent_assessment=60'."""
    windows = dict(DEFAULT_ACK_MINUTES)
    for pair in os.getenv(ACK_ENV, "").split(","):
        if "=" not in pair:
            continue
        tier, value = (p.strip() for p in pair.split("=", 1))
        if tier in windows:
            try:
                windows[tier] = max(1, int(value))
            except ValueError:
                continue
    return windows


def _choice(value: Any, allowed, name: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise EscalationInvalidInput(f"{name} must be one of: {', '.join(sorted(allowed))}.")
    return value


def _ident(value: Any, name: str, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not _ID.match(value):
        raise EscalationInvalidInput(f"{name} must be an identifier of 1-128 letters, digits, '_', '.', ':' or '-'.")
    return value


def _client_exists(conn: db.Conn, org: str, client_id: str) -> bool:
    row = conn.execute(
        "SELECT id FROM client_records WHERE id = ? AND org_id = ? AND disposed_at IS NULL", (client_id, org)
    ).fetchone()
    return row is not None


def _assessment_of_client(conn: db.Conn, org: str, client_id: str, assessment_id: str) -> bool:
    row = conn.execute(
        "SELECT id FROM assessments WHERE id = ? AND org_id = ? AND client_id = ? AND disposed_at IS NULL",
        (assessment_id, org, client_id),
    ).fetchone()
    return row is not None


def _load(conn: db.Conn, org: str, escalation_id: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT * FROM safety_escalations WHERE id = ? AND org_id = ?", (escalation_id, org)
    ).fetchone()


def _view(row: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    opened = datetime.fromisoformat(row["opened_at"])
    deadline = opened + timedelta(minutes=ack_minutes()[row["severity"]])
    out = {k: row[k] for k in (
        "id", "client_id", "assessment_id", "source", "severity", "status", "opened_by", "opened_at",
        "owner_sub", "acknowledged_at", "resolved_by", "resolved_at", "resolution_code", "documentation_ref",
    )}
    out["acknowledge_by"] = deadline.isoformat()
    out["overdue"] = row["status"] == "open" and now > deadline
    return out


def _finish(error: Exception | None, result: Any) -> Any:
    if error is not None:
        raise error
    return result


def open_escalation(actor: str, org: str, body: dict[str, Any]) -> dict[str, Any]:
    client_id = _ident(body.get("client_id"), "client_id")
    assessment_id = _ident(body.get("assessment_id"), "assessment_id", required=False)
    source = _choice(body.get("source"), SOURCES, "source")
    severity = _choice(body.get("severity"), SEVERITIES, "severity")
    if source in {"assessment_item", "safety_flag"} and assessment_id is None:
        raise EscalationInvalidInput("assessment_id is required when the source is an assessment item or safety flag.")
    result: dict[str, Any] | None = None
    escalation_id = str(uuid.uuid4())
    with db.transaction() as conn:
        if not _client_exists(conn, org, client_id):
            error, outcome = EscalationNotFound(client_id), "denied_or_missing"
        elif assessment_id is not None and not _assessment_of_client(conn, org, client_id, assessment_id):
            error, outcome = EscalationNotFound(assessment_id), "denied_or_missing"
        else:
            error, outcome = None, "ok"
            stamp = audit.now()
            conn.execute(
                "INSERT INTO safety_escalations (id, org_id, client_id, assessment_id, source, severity, status, "
                "opened_by, opened_at) VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)",
                (escalation_id, org, client_id, assessment_id, source, severity, actor, stamp),
            )
            result = _view(_load(conn, org, escalation_id))
        audit.append(conn, actor, f"safety_escalation.open.{severity}", "safety_escalation",
                     escalation_id if error is None else client_id, outcome, org=org)
    return _finish(error, result)


def acknowledge(actor: str, org: str, escalation_id: str) -> dict[str, Any]:
    """First acknowledgement takes ownership; on an acknowledged escalation it is a handover."""
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = _load(conn, org, escalation_id)
        action = "safety_escalation.acknowledge"
        if row is None:
            error, outcome = EscalationNotFound(escalation_id), "denied_or_missing"
        elif row["status"] == "resolved":
            error, outcome = EscalationStateConflict("This escalation is resolved."), "rejected_state"
        elif row["status"] == "acknowledged" and row["owner_sub"] == actor:
            error, outcome = EscalationStateConflict("You already own this escalation."), "rejected_duplicate"
        else:
            error, outcome = None, "ok"
            stamp = audit.now()
            if row["status"] == "open":
                conn.execute(
                    "UPDATE safety_escalations SET status = 'acknowledged', owner_sub = ?, acknowledged_at = ? "
                    "WHERE id = ? AND org_id = ? AND status = 'open'",
                    (actor, stamp, escalation_id, org),
                )
            else:
                action = "safety_escalation.handover"
                conn.execute(
                    "UPDATE safety_escalations SET owner_sub = ? WHERE id = ? AND org_id = ? AND status = 'acknowledged'",
                    (actor, escalation_id, org),
                )
            result = _view(_load(conn, org, escalation_id))
        audit.append(conn, actor, action, "safety_escalation", escalation_id, outcome, org=org)
    return _finish(error, result)


def resolve(actor: str, org: str, escalation_id: str, body: dict[str, Any]) -> dict[str, Any]:
    code = _choice(body.get("resolution_code"), RESOLUTION_CODES, "resolution_code")
    doc_ref = _ident(body.get("documentation_ref"), "documentation_ref")
    result: dict[str, Any] | None = None
    with db.transaction() as conn:
        row = _load(conn, org, escalation_id)
        if row is None:
            error, outcome = EscalationNotFound(escalation_id), "denied_or_missing"
        elif row["status"] != "acknowledged":
            error = EscalationStateConflict("An escalation must be acknowledged (owned) before it is resolved.")
            outcome = "rejected_state"
        elif not _assessment_of_client(conn, org, row["client_id"], doc_ref):
            error = EscalationInvalidInput("documentation_ref must be an assessment of this client in this organisation.")
            outcome = "rejected_documentation"
        else:
            error, outcome = None, "ok"
            conn.execute(
                "UPDATE safety_escalations SET status = 'resolved', resolved_by = ?, resolved_at = ?, "
                "resolution_code = ?, documentation_ref = ? WHERE id = ? AND org_id = ? AND status = 'acknowledged'",
                (actor, audit.now(), code, doc_ref, escalation_id, org),
            )
            result = _view(_load(conn, org, escalation_id))
        audit.append(conn, actor, f"safety_escalation.resolve.{code}", "safety_escalation", escalation_id,
                     outcome, org=org)
    return _finish(error, result)


def get(actor: str, org: str, escalation_id: str) -> dict[str, Any]:
    with db.transaction() as conn:
        row = _load(conn, org, escalation_id)
        error, outcome = (EscalationNotFound(escalation_id), "denied_or_missing") if row is None else (None, "ok")
        audit.append(conn, actor, "safety_escalation.read", "safety_escalation", escalation_id, outcome, org=org)
    return _finish(error, None if row is None else _view(row))


def unresolved(actor: str, org: str) -> list[dict[str, Any]]:
    """Every open or acknowledged escalation in the organisation: overdue first, then highest tier, then oldest."""
    now = datetime.now(timezone.utc)
    with db.transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM safety_escalations WHERE org_id = ? AND status <> 'resolved' ORDER BY opened_at, id", (org,)
        ).fetchall()
        audit.append(conn, actor, "safety_escalation.queue", "safety_escalation", None, "ok", org=org)
    views = [_view(r, now) for r in rows]
    rank = {s: i for i, s in enumerate(reversed(SEVERITIES))}
    return sorted(views, key=lambda v: (not v["overdue"], rank[v["severity"]], v["opened_at"]))


def for_client(actor: str, org: str, client_id: str) -> list[dict[str, Any]]:
    client_id = _ident(client_id, "client_id")
    with db.transaction() as conn:
        if not _client_exists(conn, org, client_id):
            error, outcome, rows = EscalationNotFound(client_id), "denied_or_missing", []
        else:
            error, outcome = None, "ok"
            rows = conn.execute(
                "SELECT * FROM safety_escalations WHERE org_id = ? AND client_id = ? ORDER BY opened_at, id",
                (org, client_id),
            ).fetchall()
        audit.append(conn, actor, "safety_escalation.client_history", "client", client_id, outcome, org=org)
    return _finish(error, [_view(r) for r in rows])
