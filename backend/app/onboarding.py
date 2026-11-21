"""Customer onboarding state machine with provisional-registration restrictions.

Stages advance one at a time. Every stage's requirement is checked against records the
platform itself holds:
- contact and MFA stages: identity-provider verification events (verification.py);
- terms, privacy and consent stages: the customer's own versioned acknowledgements;
- eligibility, screening, allocation and team stages: attestations by a staff member who
  is not the one advancing the case (separation of duties).
Caller-supplied booleans are not accepted as evidence. Registration never sets clinical
approval, and a case that is not complete keeps the account provisional (see rbac.py).
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from . import audit, store
from .auth import require_identity
from .ratelimit import limit_by_subject
from .rbac import Role, grant_system_role, require_permission, roles_for
from .verification import has_verification

STAGES: tuple[str, ...] = (
    "registered", "contact_verified", "account_active", "privacy_acknowledged", "consented",
    "intake_eligible", "screened", "allocated", "team_assigned", "complete",
)

ACK_ENV = {"terms": "STN_TERMS_VERSION", "privacy_notice": "STN_PRIVACY_NOTICE_VERSION",
           "consent": "STN_CONSENT_VERSION"}

ATTESTATION_ROLES = {
    "eligibility": {Role.CLINICAL_SUPERVISOR, Role.AUTHORISED_CLINICIAN},
    "screening": {Role.CLINICAL_SUPERVISOR, Role.AUTHORISED_CLINICIAN},
    "allocation": {Role.INTAKE_COORDINATOR},
    "team_assignment": {Role.INTAKE_COORDINATOR},
}

# Each attestation kind cites a platform record of the matching type (see migration 0004).
RECORD_TYPE_FOR_KIND = {
    "eligibility": "eligibility_review",
    "screening": "screening_review",
    "allocation": "allocation",
    "team_assignment": "team_assignment",
}
# Who may create each record type. The creator becomes the record's responsible staff member.
RECORD_ROLES = {
    "eligibility_review": ATTESTATION_ROLES["eligibility"],
    "screening_review": ATTESTATION_ROLES["screening"],
    "allocation": ATTESTATION_ROLES["allocation"],
    "team_assignment": ATTESTATION_ROLES["team_assignment"],
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


class RequirementNotMet(OnboardingError):
    status_code = 422


class ConfigurationMissing(OnboardingError):
    status_code = 503


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


def _current_version(kind: str) -> str:
    value = os.getenv(ACK_ENV[kind], "").strip()
    if not value:
        raise ConfigurationMissing(f"The current {kind} version is not configured.")
    return value


def _ack_recorded(conn, subject: str, kind: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM acknowledgements WHERE subject = ? AND kind = ? AND version = ? LIMIT 1",
        (subject, kind, _current_version(kind)),
    ).fetchone() is not None


def create_case(subject: str) -> dict[str, Any]:
    case_id = str(uuid.uuid4())

    def _do(conn: sqlite3.Connection):
        if conn.execute(
            "SELECT 1 FROM onboarding_cases WHERE subject = ? AND stage != 'complete' AND suspended = 0",
            (subject,),
        ).fetchone():
            raise CaseAlreadyOpen("An onboarding case is already open for this account.")
        now = _now()
        conn.execute(
            "INSERT INTO onboarding_cases (id, subject, stage, suspended, evidence, created_at, updated_at) "
            "VALUES (?, ?, 'registered', 0, '{}', ?, ?)",
            (case_id, subject, now, now),
        )
        audit.append_in_tx(conn, "system:onboarding", "onboarding.create", f"case:{case_id}",
                           {"stage": "registered"})
        return {"id": case_id, "stage": "registered"}

    result = _tx(_do)
    grant_system_role(subject, Role.CUSTOMER)
    return result


def _load(conn: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM onboarding_cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise CaseNotFound("Onboarding case not found.")
    return row


def _check_requirement(conn, actor: str, row, to_stage: str) -> None:
    subject = row["subject"]
    case_id = row["id"]
    if to_stage == "contact_verified":
        missing = [k for k in ("email", "phone") if not has_verification(conn, subject, k)]
        if missing:
            raise RequirementNotMet(f"Identity provider has not verified: {', '.join(missing)}.")
    elif to_stage == "account_active":
        if not has_verification(conn, subject, "mfa"):
            raise RequirementNotMet("Identity provider has not confirmed MFA enrolment.")
        if not _ack_recorded(conn, subject, "terms"):
            raise RequirementNotMet("Current terms have not been accepted.")
    elif to_stage == "privacy_acknowledged":
        if not _ack_recorded(conn, subject, "privacy_notice"):
            raise RequirementNotMet("Current privacy notice has not been acknowledged.")
    elif to_stage == "consented":
        if not _ack_recorded(conn, subject, "consent"):
            raise RequirementNotMet("Current consent has not been recorded.")
    elif to_stage in ("intake_eligible", "screened", "allocated", "team_assigned"):
        kind = {"intake_eligible": "eligibility", "screened": "screening",
                "allocated": "allocation", "team_assigned": "team_assignment"}[to_stage]
        att = conn.execute(
            "SELECT attested_by, reference FROM attestations WHERE case_id = ? AND kind = ? "
            "ORDER BY id DESC LIMIT 1", (case_id, kind),
        ).fetchone()
        if att is None:
            raise RequirementNotMet(f"No {kind} attestation has been recorded.")
        if att["attested_by"] == actor:
            raise RequirementNotMet("The attester cannot also advance the case (separation of duties).")
        if att["attested_by"] == subject:
            raise RequirementNotMet("A customer cannot attest their own onboarding stage.")
        record = conn.execute(
            "SELECT * FROM platform_records WHERE id = ?", (att["reference"],),
        ).fetchone()
        if (record is None or record["record_type"] != RECORD_TYPE_FOR_KIND[kind]
                or record["case_id"] != case_id or record["subject"] != subject
                or record["status"] != "active" or record["responsible_sub"] != att["attested_by"]):
            raise RequirementNotMet("The attestation does not cite a valid active platform record for this case.")
        if to_stage == "team_assigned":
            assignee = record["assignee_sub"]
            if not assignee:
                raise RequirementNotMet("The team assignment record names no assignee.")
            with store._connect() as c2:
                if Role.AUTHORISED_CLINICIAN not in roles_for(c2, assignee):
                    raise RequirementNotMet("Assigned clinician does not hold the authorised clinician role.")


def advance(actor: str, case_id: str, to_stage: str) -> dict[str, Any]:
    if to_stage not in STAGES:
        raise InvalidTransition("Unknown stage.")

    def _do(conn: sqlite3.Connection):
        row = _load(conn, case_id)
        if row["suspended"]:
            raise CaseSuspended("This onboarding case is suspended.")
        current = row["stage"]
        position = STAGES.index(current)
        expected = STAGES[position + 1] if position + 1 < len(STAGES) else None
        if to_stage != expected:
            raise InvalidTransition(f"Cannot move from {current} to {to_stage}; the next stage is {expected}.")
        _check_requirement(conn, actor, row, to_stage)
        conn.execute("UPDATE onboarding_cases SET stage = ?, updated_at = ? WHERE id = ?",
                     (to_stage, _now(), case_id))
        audit.append_in_tx(conn, actor, "onboarding.advance", f"case:{case_id}",
                           {"from": current, "to": to_stage})
        return {"id": case_id, "stage": to_stage}

    return _tx(_do)


def record_acknowledgement(subject: str, kind: str, version: str) -> dict[str, Any]:
    if kind not in ACK_ENV:
        raise InvalidTransition("Unknown acknowledgement kind.")
    if version != _current_version(kind):
        raise RequirementNotMet("Version does not match the current published version.")

    def _do(conn):
        conn.execute("INSERT INTO acknowledgements (subject, kind, version, recorded_at) VALUES (?, ?, ?, ?)",
                     (subject, kind, version, _now()))
        audit.append_in_tx(conn, subject, "acknowledgement.recorded", f"subject:{subject}",
                           {"kind": kind, "version": version})
        return {"kind": kind, "version": version}

    return _tx(_do)


def create_platform_record(actor: str, case_id: str, record_type: str,
                           assignee_sub: str | None = None) -> dict[str, Any]:
    """Create a platform record. The actor must hold the authorised role for its type."""
    if record_type not in RECORD_ROLES:
        raise InvalidTransition("Unknown record type.")
    if record_type == "team_assignment" and not assignee_sub:
        raise RequirementNotMet("A team assignment record must name the assignee.")
    if assignee_sub and assignee_sub == actor:
        raise RequirementNotMet("A staff member cannot assign a team to themselves.")
    record_id = str(uuid.uuid4())

    def _do(conn: sqlite3.Connection):
        case = _load(conn, case_id)
        roles = roles_for(conn, actor)
        matched = roles & RECORD_ROLES[record_type]
        if not matched:
            audit.append_in_tx(conn, actor, "platform_record.denied", f"case:{case_id}",
                               {"record_type": record_type})
            conn.execute("COMMIT")
            raise PermissionError("Not permitted to create this record.")
        if case["subject"] == actor:
            raise RequirementNotMet("A customer cannot create a record about their own case.")
        if assignee_sub is not None and not assignee_sub.strip():
            raise RequirementNotMet("Assignee is invalid.")
        conn.execute(
            "INSERT INTO platform_records (id, record_type, case_id, subject, responsible_sub, assignee_sub, "
            "authorised_role, status, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)",
            (record_id, record_type, case_id, case["subject"], actor, assignee_sub,
             sorted(r.value for r in matched)[0], actor, _now()),
        )
        audit.append_in_tx(conn, actor, "platform_record.created", f"case:{case_id}",
                           {"record_type": record_type, "record_id": record_id})
        return {"record_id": record_id, "record_type": record_type}

    return _tx(_do)


def record_attestation(actor: str, case_id: str, kind: str, record_id: str) -> dict[str, Any]:
    if kind not in ATTESTATION_ROLES:
        raise InvalidTransition("Unknown attestation kind.")
    if not record_id.strip():
        raise RequirementNotMet("A platform record identifier is required.")

    def _do(conn):
        _load(conn, case_id)
        roles = roles_for(conn, actor)
        if not roles & ATTESTATION_ROLES[kind]:
            audit.append_in_tx(conn, actor, "attestation.denied", f"case:{case_id}", {"kind": kind})
            conn.execute("COMMIT")
            raise PermissionError("Not permitted to attest this stage.")
        record = conn.execute("SELECT * FROM platform_records WHERE id = ?", (record_id,)).fetchone()
        if record is None or record["case_id"] != case_id or record["record_type"] != RECORD_TYPE_FOR_KIND[kind]:
            raise RequirementNotMet("The cited record does not exist for this case and stage.")
        if record["status"] != "active":
            raise RequirementNotMet("The cited record is withdrawn.")
        if record["responsible_sub"] != actor:
            raise RequirementNotMet("Only the record's responsible staff member can attest it.")
        conn.execute("INSERT INTO attestations (case_id, kind, reference, attested_by, recorded_at) "
                     "VALUES (?, ?, ?, ?, ?)", (case_id, kind, record_id, actor, _now()))
        audit.append_in_tx(conn, actor, "attestation.recorded", f"case:{case_id}",
                           {"kind": kind, "record_id": record_id})
        return {"case_id": case_id, "kind": kind, "record_id": record_id}

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


class AcknowledgementBody(BaseModel):
    kind: str
    version: str


class AttestationBody(BaseModel):
    kind: str
    record_id: str


class PlatformRecordBody(BaseModel):
    record_type: str
    assignee_sub: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
def open_case(identity: dict = Depends(limit_by_subject("onboarding-open", 5, 3600))) -> dict:
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


@router.post("/me/acknowledgements", status_code=status.HTTP_201_CREATED)
def acknowledge(body: AcknowledgementBody, identity: dict = Depends(require_permission("customer:update_own")),
                _limit: dict = Depends(limit_by_subject("ack", 30))) -> dict:
    try:
        return record_acknowledgement(identity["sub"], body.kind, body.version)
    except OnboardingError as exc:
        raise _map(exc) from exc


@router.post("/{case_id}/advance")
def advance_route(case_id: str, body: AdvanceBody,
                  identity: dict = Depends(require_permission("intake:manage")),
                  _limit: dict = Depends(limit_by_subject("advance", 60))) -> dict:
    try:
        return advance(identity["sub"], case_id, body.to_stage)
    except OnboardingError as exc:
        raise _map(exc) from exc


@router.post("/{case_id}/attestations", status_code=status.HTTP_201_CREATED)
def attest_route(case_id: str, body: AttestationBody, identity: dict = Depends(limit_by_subject("attest", 60))) -> dict:
    try:
        return record_attestation(identity["sub"], case_id, body.kind, body.record_id)
    except OnboardingError as exc:
        raise _map(exc) from exc
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted.") from exc


@router.post("/{case_id}/records", status_code=status.HTTP_201_CREATED)
def record_route(case_id: str, body: PlatformRecordBody, identity: dict = Depends(limit_by_subject("records", 60))) -> dict:
    try:
        return create_platform_record(identity["sub"], case_id, body.record_type, body.assignee_sub)
    except OnboardingError as exc:
        raise _map(exc) from exc
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted.") from exc


@router.post("/{case_id}/suspend")
def suspend_route(case_id: str, identity: dict = Depends(require_permission("intake:manage"))) -> dict:
    try:
        return suspend(identity["sub"], case_id)
    except OnboardingError as exc:
        raise _map(exc) from exc
