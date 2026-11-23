"""Routes for consent records, retention, legal holds, disposal and key rotation.

Consent routes need the clinician role and act only on the caller's own clients.
Administrative routes need the admin role, except disposal approval, which a
second person with the admin or reviewer role gives. Admin routes return
metadata only: ids, codes, people, times and counts, never clinical payloads.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from . import governance as gov
from . import rekey
from .assessment_routes import _call
from .clients import _payload
from .rbac import ADMIN, CLINICIAN, REVIEWER, require_roles

consent_router = APIRouter(prefix="/v1/clients/{client_id}/consents", tags=["consent"])
admin_router = APIRouter(prefix="/v1/admin", tags=["governance"])

clinician = require_roles(CLINICIAN)
admin = require_roles(ADMIN)
second_person = require_roles(ADMIN, REVIEWER)


@consent_router.post("", status_code=status.HTTP_201_CREATED)
async def record_consent(client_id: str, request: Request, identity: dict = Depends(clinician)) -> dict:
    """Record a consent: scope code and a reference to the consent-text version shown to the client."""
    body = await _payload(request)
    return _call(gov.record_consent, identity["sub"], identity["org"], client_id, body.get("scope"),
                 body.get("consent_text_ref"))


@consent_router.get("")
def list_consents(client_id: str, identity: dict = Depends(clinician)) -> list[dict]:
    return _call(gov.list_consents, identity["sub"], identity["org"], client_id)


@consent_router.post("/{consent_id}/withdraw")
def withdraw_consent(client_id: str, consent_id: str, identity: dict = Depends(clinician)) -> dict:
    return _call(gov.withdraw_consent, identity["sub"], identity["org"], client_id, consent_id)


@admin_router.get("/retention/policy")
def retention_policy(identity: dict = Depends(admin)) -> dict:
    return gov.policy()


@admin_router.get("/retention/due")
def retention_due(identity: dict = Depends(admin)) -> list[dict]:
    return _call(gov.due_for_disposal, identity["sub"], identity["org"])


@admin_router.post("/legal-holds", status_code=status.HTTP_201_CREATED)
async def place_legal_hold(request: Request, identity: dict = Depends(admin)) -> dict:
    body = await _payload(request)
    return _call(gov.place_hold, identity["sub"], identity["org"], body.get("client_id") or "",
                 body.get("reason_code"))


@admin_router.get("/legal-holds")
def list_legal_holds(client_id: str | None = Query(None), identity: dict = Depends(admin)) -> list[dict]:
    return _call(gov.list_holds, identity["sub"], identity["org"], client_id)


@admin_router.post("/legal-holds/{hold_id}/release")
def release_legal_hold(hold_id: str, identity: dict = Depends(admin)) -> dict:
    return _call(gov.release_hold, identity["sub"], identity["org"], hold_id)


@admin_router.post("/disposals", status_code=status.HTTP_201_CREATED)
async def request_disposal(request: Request, identity: dict = Depends(admin)) -> dict:
    body = await _payload(request)
    return _call(gov.request_disposal, identity["sub"], identity["org"], body.get("client_id") or "",
                 body.get("reason_code"))


@admin_router.get("/disposals")
def list_disposals(identity: dict = Depends(admin)) -> list[dict]:
    return _call(gov.list_disposals, identity["sub"], identity["org"])


@admin_router.post("/disposals/{disposal_id}/approve")
def approve_disposal(disposal_id: str, identity: dict = Depends(second_person)) -> dict:
    """Second-person approval. Executes the disposal after re-checking eligibility."""
    return _call(gov.approve_disposal, identity["sub"], identity["org"], disposal_id)


@admin_router.post("/disposals/{disposal_id}/cancel")
def cancel_disposal(disposal_id: str, identity: dict = Depends(admin)) -> dict:
    return _call(gov.cancel_disposal, identity["sub"], identity["org"], disposal_id)


@admin_router.get("/keys/status")
def key_status(identity: dict = Depends(admin)) -> dict:
    """Key ids in use for this organisation's records. Never returns key material."""
    return _call(rekey.status, identity["org"])


@admin_router.post("/keys/re-encrypt")
def reencrypt(limit: int = Query(500, ge=1, le=5000), identity: dict = Depends(admin)) -> dict:
    """Move up to `limit` of this organisation's records onto the active data key."""
    return _call(rekey.reencrypt, identity["sub"], identity["org"], limit)
