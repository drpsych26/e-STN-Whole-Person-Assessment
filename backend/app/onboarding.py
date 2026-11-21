"""Customer onboarding state machine.

Stages advance one at a time, in the order required by the implementation directive.
Each stage needs specific evidence. Registration never sets clinical approval: there is
no clinical-approval field and no stage that grants it. Suspended cases cannot advance.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from . import audit, store
from .auth import require_identity
from .rbac import Role, grant_system_role, require_permission

STAGES: tuple[str, ...] = (
    "registered",
    "contact_verified",
    "account_active",
    "privacy_acknowledged",
    "consented",
    "intake_eligible",
    "screened",
    "allocated",
    "team_assigned",
    "complete",
)

REQUIRED_EVIDENCE: dict[str, tuple[str, ...]] = {
    "contact_verified": ("email_verified", "phone_verified"),
    "account_active": ("mfa_enrolled", "terms_accepted"),
    "privacy_acknowledged": ("privacy_notice_version",),
    "consented": ("consent_record_id",),
    "intake_eligible": ("eligibility_checked",),
    "screened": ("screening_record_id",),
    "allocated": ("allocation_ref",),
    "team_assigned": ("clinician_subject",),
    "complete": (),
}


class OnboardingError(Exception):
    status_code = 409


class CaseNotFound(OnboardingError):
    status_code = 404


class CaseSuspended(OnboardingError):
    pass


class CaseAlreadyOpen(OnboardingError):
    pass


class InvalidTransition(OnboardingError):
    pass


class MissingEvidence(OnboardingError):
    status_code = 422


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def create_case(subject: str) -> dict[str, Any]:
    case_id = str(uuid.uuid4())

    def _do(conn: sqlite3.Connection):
        open_case = conn.execute(
            "SELECT 1 FROM onboarding_cases WHERE subject = ? AND stage != 'complete' AND suspended = 0",
            (subject,),
        ).fetchone()
        if open_case:
            raise CaseAlreadyOpen("An onboarding case is already open for this account.")
        now = _now()
        conn.execute(
            "INSERT INTO onboarding_cases (id, subject, stage, suspended, evidence, created_at, updated_at) "
            "VALUES (?, ?, 'registered', 0, '{}', ?, ?)",
            (case_id, subject, now, now),
        )
        audit.append_in_tx(conn, "system:onboarding", "onboarding.create", f"case:{case_id}", {"stage": "registered"})
        return {"id": case_id, "stage": "registered"}

    result = _tx(_do)
    grant_system_role(subject, Role.CUSTOMER)
    return result


def _load(conn: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM onboarding_cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise CaseNotFound("Onboarding case not found.")
    return row


def advance(actor: str, case_id: str, to_stage: str, evidence: dict[str, Any]) -> dict[str, Any]:
    if to_stage not in STAGES:
        raise InvalidTransition("Unknown stage.")
    evidence = evidence or {}

    def _do(conn: sqlite3.Connection):
        row = _load(conn, case_id)
        if row["suspended"]:
            raise CaseSuspended("This onboarding case is suspended.")
        current = row["stage"]
        position = STAGES.index(current)
        expected = STAGES[position + 1] if position + 1 < len(STAGES) else None
        if to_stage != expected:
            raise InvalidTransition(f"Cannot move from {current} to {to_stage}; the next stage is {expected}.")
        required = REQUIRED_EVIDENCE[to_stage]
        missing = [k for k in required if not evidence.get(k)]
        if missing:
            raise MissingEvidence(f"Missing evidence: {', '.join(missing)}.")
        stored = json.loads(row["evidence"])
        stored.update({k: evidence[k] for k in required})
        conn.execute(
            "UPDATE onboarding_cases SET stage = ?, evidence = ?, updated_at = ? WHERE id = ?",
            (to_stage, json.dumps(stored, sort_keys=True), _now(), case_id),
        )
        audit.append_in_tx(conn, actor, "onboarding.advance", f"case:{case_id}",
                           {"from": current, "to": to_stage})
        return {"id": case_id, "stage": to_stage}

    return _tx(_do)


def suspend(actor: str, case_id: str) -> dict[str, Any]:
    def _do(conn: sqlite3.Connection):
        _load(conn, case_id)
        conn.execute("UPDATE onboarding_cases SET suspended = 1, updated_at = ? WHERE id = ?", (_now(), case_id))
        audit.append_in_tx(conn, actor, "onboarding.suspend", f"case:{case_id}", {})
        return {"id": case_id, "suspended": True}

    return _tx(_do)


def get_case_for_subject(subject: str) -> dict[str, Any] | None:
    with store._connect() as conn:
        row = conn.execute(
            "SELECT id, stage, suspended FROM onboarding_cases WHERE subject = ? ORDER BY created_at DESC LIMIT 1",
            (subject,),
        ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "stage": row["stage"], "suspended": bool(row["suspended"])}


def _map(exc: OnboardingError) -> HTTPException:
    return HTTPException(exc.status_code, str(exc) or "Request could not be completed.")


router = APIRouter(prefix="/v1/onboarding", tags=["onboarding"])


class AdvanceBody(BaseModel):
    to_stage: str
    evidence: dict[str, Any] = {}


@router.post("", status_code=status.HTTP_201_CREATED)
def open_case(identity: dict = Depends(require_identity)) -> dict:
    try:
        return create_case(identity["sub"])
    except OnboardingError as exc:
        raise _map(exc) from exc
    except store.StoreNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Onboarding is not available.") from exc


@router.get("/me")
def my_case(identity: dict = Depends(require_permission("customer:read_own"))) -> dict:
    case = get_case_for_subject(identity["sub"])
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No onboarding case found.")
    return case


@router.post("/{case_id}/advance")
def advance_route(case_id: str, body: AdvanceBody,
                  identity: dict = Depends(require_permission("intake:manage"))) -> dict:
    try:
        return advance(identity["sub"], case_id, body.to_stage, body.evidence)
    except OnboardingError as exc:
        raise _map(exc) from exc


@router.post("/{case_id}/suspend")
def suspend_route(case_id: str, identity: dict = Depends(require_permission("intake:manage"))) -> dict:
    try:
        return suspend(identity["sub"], case_id)
    except OnboardingError as exc:
        raise _map(exc) from exc
