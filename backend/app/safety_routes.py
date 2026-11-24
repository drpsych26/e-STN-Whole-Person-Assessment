"""Routes for safety escalations (see app.safety_escalations for the rules).

Clinical staff (clinician or reviewer) open, acknowledge, resolve and read escalations.
Admins read the unresolved queue only. Status codes: 404 for missing or other-organisation
objects, 409 for a state conflict, 422 for invalid input.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from . import db
from . import safety_escalations as svc
from .clients import _payload
from .crypto import DataKeyError
from .rbac import ADMIN, CLINICIAN, REVIEWER, require_roles

router = APIRouter(prefix="/v1/safety-escalations", tags=["safety"])
clinical = require_roles(CLINICIAN, REVIEWER)
queue_viewer = require_roles(CLINICIAN, REVIEWER, ADMIN)


def _call(fn, *args: Any) -> Any:
    try:
        return fn(*args)
    except svc.EscalationNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.") from exc
    except svc.EscalationStateConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except svc.EscalationInvalidInput as exc:
        raise HTTPException(422, str(exc)) from exc
    except (db.StoreNotConfigured, DataKeyError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Record storage is not available.") from exc


@router.post("", status_code=status.HTTP_201_CREATED)
async def open_escalation(request: Request, identity: dict = Depends(clinical)) -> dict:
    """Body: client_id, source, severity, optional assessment_id (required for assessment sources)."""
    body = await _payload(request)
    return _call(svc.open_escalation, identity["sub"], identity["org"], body)


@router.get("")
def unresolved_queue(identity: dict = Depends(queue_viewer)) -> list[dict]:
    """Open and acknowledged escalations: overdue first, then highest tier, then oldest. Codes and ids only."""
    return _call(svc.unresolved, identity["sub"], identity["org"])


@router.get("/{escalation_id}")
def read_escalation(escalation_id: str, identity: dict = Depends(clinical)) -> dict:
    return _call(svc.get, identity["sub"], identity["org"], escalation_id)


@router.post("/{escalation_id}/acknowledge")
def acknowledge(escalation_id: str, identity: dict = Depends(clinical)) -> dict:
    """Take ownership (first acknowledgement) or take over ownership (handover)."""
    return _call(svc.acknowledge, identity["sub"], identity["org"], escalation_id)


@router.post("/{escalation_id}/resolve")
async def resolve(escalation_id: str, request: Request, identity: dict = Depends(clinical)) -> dict:
    """Body: resolution_code, documentation_ref (an assessment of the same client)."""
    body = await _payload(request)
    return _call(svc.resolve, identity["sub"], identity["org"], escalation_id, body)


@router.get("/by-client/{client_id}")
def client_history(client_id: str, identity: dict = Depends(clinical)) -> list[dict]:
    return _call(svc.for_client, identity["sub"], identity["org"], client_id)
