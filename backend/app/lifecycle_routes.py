"""Routes for reviewer assignment, the clinician account registry and client
access / correction requests.

Administrative routes need the admin role and return metadata only. The client's
owning clinician (clinician role) prepares access and correction responses and
reads correction statements. Status codes follow app.assessment_routes: 403 for
self-assignment, self-review, self-change, same-person reactivation or a review
assigned to someone else; 404 for missing or other-organisation objects; 409 for
a state conflict or an inactive reviewer; 410 for disposed records; 422 for
invalid input.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from . import accounts
from . import privacy_requests as privacy
from . import review_assignment as assignment
from .assessment_routes import _call
from .clients import _payload
from .rbac import ADMIN, CLINICIAN, require_roles

admin_router = APIRouter(prefix="/v1/admin", tags=["governance"])
clinician_router = APIRouter(tags=["privacy-requests"])

admin = require_roles(ADMIN)
clinician = require_roles(CLINICIAN)


# --------------------------------------------------------------------------- reviewer assignment


@admin_router.post("/assessments/{assessment_id}/reviewer")
async def assign_reviewer(assessment_id: str, request: Request, identity: dict = Depends(admin)) -> dict:
    """Assign (or reassign) the reviewer for the current submission: body `reviewer_sub`."""
    body = await _payload(request)
    return _call(assignment.assign, identity["sub"], identity["org"], assessment_id, body.get("reviewer_sub"))


@admin_router.get("/assessments/{assessment_id}/reviewer-history")
def reviewer_history(assessment_id: str, identity: dict = Depends(admin)) -> list[dict]:
    return _call(assignment.assignment_history, identity["sub"], identity["org"], assessment_id)


@admin_router.get("/review-assignments")
def reassignment_queue(older_than_hours: int | None = Query(None, ge=1, le=24 * 365),
                       identity: dict = Depends(admin)) -> list[dict]:
    """Submitted work that is unassigned or whose assignment is stale (metadata only)."""
    return _call(assignment.reassignment_queue, identity["sub"], identity["org"], older_than_hours)


# --------------------------------------------------------------------------- account registry


@admin_router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def invite_account(request: Request, identity: dict = Depends(admin)) -> dict:
    """Register a token subject in this organisation as invited: body `subject`, optional `reason_code`."""
    body = await _payload(request)
    return _call(accounts.invite, identity["sub"], identity["org"], body.get("subject"), body.get("reason_code"))


@admin_router.get("/accounts")
def list_accounts(status_filter: str | None = Query(None, alias="status"), identity: dict = Depends(admin)) -> list[dict]:
    return _call(accounts.list_accounts, identity["sub"], identity["org"], status_filter)


@admin_router.get("/accounts/{subject}/history")
def account_history(subject: str, identity: dict = Depends(admin)) -> list[dict]:
    return _call(accounts.account_history, identity["sub"], identity["org"], subject)


async def _change(subject: str, request: Request, identity: dict, action: str) -> dict:
    body = await _payload(request)
    return _call(accounts.change_status, identity["sub"], identity["org"], subject, action, body.get("reason_code"))


@admin_router.post("/accounts/{subject}/activate")
async def activate_account(subject: str, request: Request, identity: dict = Depends(admin)) -> dict:
    """Invited or suspended -> active. Deactivated accounts need the two-person reactivation flow."""
    return await _change(subject, request, identity, "activate")


@admin_router.post("/accounts/{subject}/suspend")
async def suspend_account(subject: str, request: Request, identity: dict = Depends(admin)) -> dict:
    """Active -> suspended; `reason_code` required."""
    return await _change(subject, request, identity, "suspend")


@admin_router.post("/accounts/{subject}/deactivate")
async def deactivate_account(subject: str, request: Request, identity: dict = Depends(admin)) -> dict:
    """Invited, active or suspended -> deactivated; `reason_code` required. Ends open review assignments."""
    return await _change(subject, request, identity, "deactivate")


@admin_router.post("/accounts/{subject}/reactivation-requests", status_code=status.HTTP_201_CREATED)
async def request_reactivation(subject: str, request: Request, identity: dict = Depends(admin)) -> dict:
    body = await _payload(request)
    return _call(accounts.request_reactivation, identity["sub"], identity["org"], subject, body.get("reason_code"))


@admin_router.post("/account-reactivations/{request_id}/approve")
def approve_reactivation(request_id: str, identity: dict = Depends(admin)) -> dict:
    """Second-person approval: a different admin from the requester."""
    return _call(accounts.decide_reactivation, identity["sub"], identity["org"], request_id, True)


@admin_router.post("/account-reactivations/{request_id}/cancel")
def cancel_reactivation(request_id: str, identity: dict = Depends(admin)) -> dict:
    return _call(accounts.decide_reactivation, identity["sub"], identity["org"], request_id, False)


@admin_router.get("/access-review")
def access_review(inactive_after_days: int | None = Query(None, ge=1, le=3650),
                  identity: dict = Depends(admin)) -> dict:
    """Periodic access review: status, roles last presented and last activity per registered subject."""
    return _call(accounts.access_review, identity["sub"], identity["org"], inactive_after_days)


# --------------------------------------------------------------------------- privacy requests


@admin_router.get("/privacy-requests/policy")
def privacy_policy(identity: dict = Depends(admin)) -> dict:
    return privacy.policy()


@admin_router.post("/privacy-requests", status_code=status.HTTP_201_CREATED)
async def log_privacy_request(request: Request, identity: dict = Depends(admin)) -> dict:
    """Log an access or correction request: `client_id`, `kind` (access|correction), `received_on` (YYYY-MM-DD)."""
    body = await _payload(request)
    return _call(privacy.log_request, identity["sub"], identity["org"], body.get("client_id"), body.get("kind"),
                 body.get("received_on"))


@admin_router.get("/privacy-requests")
def list_privacy_requests(state: str | None = Query(None), identity: dict = Depends(admin)) -> list[dict]:
    return _call(privacy.list_requests, identity["sub"], identity["org"], state)


@admin_router.post("/privacy-requests/{request_id}/close")
async def close_privacy_request(request_id: str, request: Request, identity: dict = Depends(admin)) -> dict:
    """Close with `outcome_code`: completed (needs a recorded response), refused, transferred or withdrawn."""
    body = await _payload(request)
    return _call(privacy.close_request, identity["sub"], identity["org"], request_id, body.get("outcome_code"))


@clinician_router.post("/v1/privacy-requests/{request_id}/access-response")
def access_response(request_id: str, identity: dict = Depends(clinician)) -> dict:
    """The owning clinician prepares the access-response export (logged with its SHA-256)."""
    return _call(privacy.access_response, identity["sub"], identity["org"], request_id)


@clinician_router.post("/v1/privacy-requests/{request_id}/correction-response")
async def correction_response(request_id: str, request: Request, identity: dict = Depends(clinician)) -> dict:
    """`action`: amended (with `assessment_id` of the new version), client_record_corrected, or declined
    (with the client's `statement` of correction, stored encrypted and attached to the client)."""
    body = await _payload(request)
    return _call(privacy.correction_response, identity["sub"], identity["org"], request_id, body.get("action"),
                 body.get("assessment_id"), body.get("statement"))


@clinician_router.get("/v1/clients/{client_id}/privacy-requests")
def client_privacy_requests(client_id: str, identity: dict = Depends(clinician)) -> list[dict]:
    return _call(privacy.client_requests, identity["sub"], identity["org"], client_id)


@clinician_router.get("/v1/clients/{client_id}/correction-statements")
def client_correction_statements(client_id: str, identity: dict = Depends(clinician)) -> list[dict]:
    return _call(privacy.correction_statements, identity["sub"], identity["org"], client_id)
