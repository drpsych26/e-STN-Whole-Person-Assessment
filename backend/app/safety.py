"""Safety escalation: open, acknowledge and resolve, with ownership and unresolved-case visibility.

Rules:
- Anyone may open an escalation about themselves (the crisis panel's "I need help now" path),
  and clinical staff may open one about anyone. Opening never waits for an account check.
- Only clinical staff may acknowledge or resolve. The opener cannot acknowledge their own
  escalation when they are not clinical staff (they are not, by this rule).
- Resolution requires a coded outcome and a documentation record that exists as a client
  record owned by the resolving clinician. Free text is not accepted as documentation.
- Every transition is audited. Rows cannot be deleted and their opening facts cannot change.
- An escalation older than OVERDUE_MINUTES without acknowledgement is flagged as overdue.

Limitation: escalations are recorded in the platform database. The crisis panel's telephone
resources are static content and do not depend on this API, so a display never waits on it.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from . import audit, store
from .auth import require_identity
from .rbac import Role, roles_for

CLINICAL_ROLES = frozenset({Role.AUTHORISED_CLINICIAN, Role.CLINICAL_SUPERVISOR, Role.CLINICAL_DIRECTOR})
SOURCES = frozenset({"crisis_panel", "assessment_item", "clinician_report", "manual"})
SEVERITIES = frozenset({"urgent", "high", "routine"})
RESOLUTION_CODES = frozenset({
    "safety_plan_agreed", "referred_emergency", "referred_crisis_team",
    "no_risk_identified_documented", "other_documented",
})
OVERDUE_MINUTES = 15


class SafetyError(Exception):
    status_code = 409


class EscalationNotFound(SafetyError):
    status_code = 404


class NotPermitted(SafetyError):
    status_code = 403


class InvalidState(SafetyError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tx(fn):
    with store._connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            result = fn(conn)
            conn.execute("COMMIT")
            return result
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise


def _is_clinical(conn, actor: str) -> bool:
    return bool(roles_for(conn, actor) & CLINICAL_ROLES)


def _load(conn: sqlite3.Connection, escalation_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM safety_escalations WHERE id = ?", (escalation_id,)).fetchone()
    if row is None:
        raise EscalationNotFound("Escalation not found.")
    return row


def open_escalation(actor: str, subject: str, source: str, severity: str) -> dict[str, Any]:
    if source not in SOURCES or severity not in SEVERITIES:
        raise InvalidState("Unknown source or severity.")
    escalation_id = str(uuid.uuid4())

    def _do(conn):
        if subject != actor and not _is_clinical(conn, actor):
            audit.append_in_tx(conn, actor, "safety.denied", f"escalation:{escalation_id}", {})
            conn.execute("COMMIT")
            raise NotPermitted("Not permitted to open an escalation for another person.")
        stamp = _now().isoformat()
        conn.execute(
            "INSERT INTO safety_escalations (id, subject, source, severity, status, opened_at, opened_by) "
            "VALUES (?, ?, ?, ?, 'open', ?, ?)",
            (escalation_id, subject, source, severity, stamp, actor),
        )
        audit.append_in_tx(conn, actor, "safety.opened", f"escalation:{escalation_id}",
                           {"source": source, "severity": severity})
        return {"id": escalation_id, "status": "open", "opened_at": stamp}

    return _tx(_do)


def acknowledge(actor: str, escalation_id: str) -> dict[str, Any]:
    def _do(conn):
        row = _load(conn, escalation_id)
        if not _is_clinical(conn, actor):
            audit.append_in_tx(conn, actor, "safety.denied", f"escalation:{escalation_id}", {})
            conn.execute("COMMIT")
            raise NotPermitted("Only clinical staff can acknowledge an escalation.")
        if row["status"] != "open":
            raise InvalidState("Only an open escalation can be acknowledged.")
        stamp = _now().isoformat()
        conn.execute("UPDATE safety_escalations SET status = 'acknowledged', acknowledged_at = ?, "
                     "acknowledged_by = ? WHERE id = ?", (stamp, actor, escalation_id))
        audit.append_in_tx(conn, actor, "safety.acknowledged", f"escalation:{escalation_id}", {})
        return {"id": escalation_id, "status": "acknowledged", "acknowledged_at": stamp}

    return _tx(_do)


def resolve(actor: str, escalation_id: str, resolution_code: str, documentation_record: str) -> dict[str, Any]:
    if resolution_code not in RESOLUTION_CODES:
        raise InvalidState("Unknown resolution code.")

    def _do(conn):
        row = _load(conn, escalation_id)
        if not _is_clinical(conn, actor):
            audit.append_in_tx(conn, actor, "safety.denied", f"escalation:{escalation_id}", {})
            conn.execute("COMMIT")
            raise NotPermitted("Only clinical staff can resolve an escalation.")
        if row["status"] != "acknowledged":
            raise InvalidState("Only an acknowledged escalation can be resolved.")
        if row["acknowledged_by"] != actor:
            raise NotPermitted("The clinician who acknowledged the escalation must resolve it.")
        doc = conn.execute("SELECT owner_sub FROM client_records WHERE id = ?", (documentation_record,)).fetchone()
        if doc is None or doc["owner_sub"] != actor:
            raise InvalidState("Documentation must cite a client record you own.")
        stamp = _now().isoformat()
        conn.execute("UPDATE safety_escalations SET status = 'resolved', resolved_at = ?, resolved_by = ?, "
                     "resolution_code = ?, documentation_record = ? WHERE id = ?",
                     (stamp, actor, resolution_code, documentation_record, escalation_id))
        audit.append_in_tx(conn, actor, "safety.resolved", f"escalation:{escalation_id}",
                           {"code": resolution_code})
        return {"id": escalation_id, "status": "resolved", "resolved_at": stamp}

    return _tx(_do)


def list_unresolved(actor: str) -> list[dict[str, Any]]:
    """Unresolved escalations, oldest first, with age and overdue flag. Clinical staff only."""
    with store._connect() as conn:
        if not _is_clinical(conn, actor):
            raise NotPermitted("Only clinical staff can view unresolved escalations.")
        rows = conn.execute(
            "SELECT id, subject, source, severity, status, opened_at, acknowledged_at FROM safety_escalations "
            "WHERE status != 'resolved' ORDER BY opened_at"
        ).fetchall()
    now = _now()
    out = []
    for r in rows:
        opened = datetime.fromisoformat(r["opened_at"])
        overdue = r["status"] == "open" and now - opened > timedelta(minutes=OVERDUE_MINUTES)
        out.append({
            "id": r["id"], "subject": r["subject"], "source": r["source"], "severity": r["severity"],
            "status": r["status"], "opened_at": r["opened_at"], "overdue": overdue,
        })
    return out


# ---------- routes ----------

router = APIRouter(prefix="/v1/safety", tags=["safety"])


class OpenBody(BaseModel):
    subject: str | None = None
    source: str
    severity: str


class ResolveBody(BaseModel):
    resolution_code: str
    documentation_record: str


def _map(exc: SafetyError) -> HTTPException:
    return HTTPException(exc.status_code, str(exc) or "Request could not be completed.")


@router.post("/escalations", status_code=status.HTTP_201_CREATED)
def open_route(body: OpenBody, identity: dict = Depends(require_identity)) -> dict:
    try:
        return open_escalation(identity["sub"], body.subject or identity["sub"], body.source, body.severity)
    except SafetyError as exc:
        raise _map(exc) from exc


@router.get("/escalations/unresolved")
def unresolved_route(identity: dict = Depends(require_identity)) -> list[dict]:
    try:
        return list_unresolved(identity["sub"])
    except SafetyError as exc:
        raise _map(exc) from exc


@router.post("/escalations/{escalation_id}/acknowledge")
def acknowledge_route(escalation_id: str, identity: dict = Depends(require_identity)) -> dict:
    try:
        return acknowledge(identity["sub"], escalation_id)
    except SafetyError as exc:
        raise _map(exc) from exc


@router.post("/escalations/{escalation_id}/resolve")
def resolve_route(escalation_id: str, body: ResolveBody, identity: dict = Depends(require_identity)) -> dict:
    try:
        return resolve(identity["sub"], escalation_id, body.resolution_code, body.documentation_record)
    except SafetyError as exc:
        raise _map(exc) from exc


@router.get("/crisis-resources")
def crisis_resources_route() -> dict:
    """Public and unauthenticated: the panel must show these whether or not anyone is signed in."""
    from .crisis_resources import CRISIS_RESOURCES, PANEL_STATUS, VERIFIED_ON

    return {"resources": list(CRISIS_RESOURCES), "verified_on": VERIFIED_ON, "panel_status": PANEL_STATUS}
