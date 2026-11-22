"""Routes for assessment records, clinician review and audit metadata.

Role and MFA checks run first (403). Object-level visibility then returns 404 for
both missing and not-visible records. Workflow conflicts return 409, bad input 422.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from . import assessments as svc
from . import audit, db
from .clients import _payload
from .crypto import DataKeyError, RecordIntegrityError
from .rbac import ADMIN, CLINICIAN, REVIEWER, require_roles

router = APIRouter(tags=["assessments"])
audit_router = APIRouter(prefix="/v1/audit", tags=["audit"])

clinician = require_roles(CLINICIAN)
reviewer = require_roles(REVIEWER)
clinician_or_reviewer = require_roles(CLINICIAN, REVIEWER)
admin = require_roles(ADMIN)


def _call(fn, *args: Any) -> Any:
    try:
        return fn(*args)
    except svc.AssessmentNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.") from exc
    except svc.SelfReviewForbidden as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except (svc.TransitionNotAllowed, svc.ReviewBlocked, svc.RevisionConflict, svc.ContentHashMismatch) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except svc.InvalidInput as exc:
        raise HTTPException(422, str(exc)) from exc
    except (db.StoreNotConfigured, DataKeyError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Record storage is not available.") from exc
    except RecordIntegrityError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Record could not be verified.") from exc


def _object(body: dict[str, Any], key: str) -> dict[str, Any]:
    value = body.get(key)
    if not isinstance(value, dict):
        raise HTTPException(422, f"'{key}' must be a JSON object.")
    return value


@router.post("/v1/assessments", status_code=status.HTTP_201_CREATED)
async def create_assessment(request: Request, identity: dict = Depends(clinician)) -> dict:
    body = await _payload(request)
    client_id = body.get("client_id")
    if not isinstance(client_id, str) or not client_id:
        raise HTTPException(422, "'client_id' is required.")
    return _call(svc.create, identity["sub"], client_id, body.get("form_id"), body.get("form_version"),
                 _object(body, "payload"))


@router.get("/v1/clients/{client_id}/assessments")
def list_client_assessments(client_id: str, identity: dict = Depends(clinician)) -> list[dict]:
    return _call(svc.list_for_client, identity["sub"], client_id)


@router.get("/v1/assessments/{assessment_id}")
def read_assessment(assessment_id: str, identity: dict = Depends(clinician_or_reviewer)) -> dict:
    return _call(svc.read, identity["sub"], identity.get("roles", ()), assessment_id)


@router.put("/v1/assessments/{assessment_id}")
async def update_assessment(assessment_id: str, request: Request, identity: dict = Depends(clinician)) -> dict:
    body = await _payload(request)
    return _call(svc.update, identity["sub"], assessment_id, _object(body, "payload"), body.get("revision"))


@router.post("/v1/assessments/{assessment_id}/submit")
async def submit_assessment(assessment_id: str, request: Request, identity: dict = Depends(clinician)) -> dict:
    body = await _payload(request)
    return _call(svc.submit, identity["sub"], assessment_id, body.get("safety_flags", []))


@router.get("/v1/assessments/{assessment_id}/safety-flags")
def list_safety_flags(assessment_id: str, identity: dict = Depends(clinician_or_reviewer)) -> list[dict]:
    return _call(svc.list_flags, identity["sub"], identity.get("roles", ()), assessment_id)


@router.post("/v1/assessments/{assessment_id}/safety-flags/{flag_id}/acknowledge")
def acknowledge_safety_flag(assessment_id: str, flag_id: str, identity: dict = Depends(clinician_or_reviewer)) -> dict:
    return _call(svc.acknowledge_flag, identity["sub"], identity.get("roles", ()), assessment_id, flag_id)


@router.get("/v1/review-queue")
def review_queue(identity: dict = Depends(reviewer)) -> list[dict]:
    return _call(svc.review_queue, identity["sub"])


@router.post("/v1/assessments/{assessment_id}/start-review")
def start_review(assessment_id: str, identity: dict = Depends(reviewer)) -> dict:
    return _call(svc.start_review, identity["sub"], assessment_id)


@router.post("/v1/assessments/{assessment_id}/return")
async def return_assessment(assessment_id: str, request: Request, identity: dict = Depends(reviewer)) -> dict:
    body = await _payload(request)
    return _call(svc.return_for_changes, identity["sub"], assessment_id, body.get("reason"))


@router.post("/v1/assessments/{assessment_id}/sign-off")
async def sign_off_assessment(assessment_id: str, request: Request, identity: dict = Depends(reviewer)) -> dict:
    body = await _payload(request)
    return _call(svc.sign_off, identity["sub"], assessment_id, body.get("content_hash"))


@router.post("/v1/assessments/{assessment_id}/reopen")
def reopen_assessment(assessment_id: str, identity: dict = Depends(clinician)) -> dict:
    return _call(svc.reopen, identity["sub"], assessment_id)


@router.post("/v1/assessments/{assessment_id}/amendments", status_code=status.HTTP_201_CREATED)
async def amend_assessment(assessment_id: str, request: Request, identity: dict = Depends(clinician)) -> dict:
    body = await _payload(request)
    return _call(svc.amend, identity["sub"], assessment_id, _object(body, "payload"), body.get("reason"))


@audit_router.get("")
def list_audit_events(
    after_id: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    identity: dict = Depends(admin),
) -> list[dict]:
    """Audit metadata only. Admins get no clinical payload access anywhere in the API."""
    return _call(audit.entries, None, limit, after_id)


@audit_router.get("/verify")
def verify_audit_chain(identity: dict = Depends(admin)) -> dict:
    return _call(audit.verify_chain)
