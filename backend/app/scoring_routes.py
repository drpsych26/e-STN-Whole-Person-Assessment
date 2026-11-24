"""Routes: POST /v1/scoring/{instrument} (clinician or reviewer), GET /v1/scoring/instruments."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from . import audit, db
from . import scoring as svc
from .clients import _payload
from .rbac import ADMIN, CLINICIAN, REVIEWER, require_roles

router = APIRouter(prefix="/v1/scoring", tags=["scoring"])
clinical = require_roles(CLINICIAN, REVIEWER)
staff = require_roles(CLINICIAN, REVIEWER, ADMIN)


@router.get("/instruments")
def instruments(identity: dict = Depends(staff)) -> dict:
    """Licence register: implemented instruments (and whether active) and those not implemented, with reasons."""
    return svc.register()


@router.post("/{instrument_id}")
async def score(instrument_id: str, request: Request, identity: dict = Depends(clinical)) -> dict:
    """Body: {"responses": {"phq9_1": 0, ...}}. Stateless: nothing is stored except an audit event."""
    body = await _payload(request)
    try:
        result = svc.score(instrument_id, body.get("responses"))
    except svc.InstrumentNotActive as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except svc.ScoringError as exc:
        raise HTTPException(422, str(exc)) from exc
    try:
        with db.transaction() as conn:
            audit.append(conn, identity["sub"], f"scoring.{instrument_id}", "instrument", instrument_id,
                         "ok_complete" if result["complete"] else "ok_incomplete", org=identity["org"])
    except db.StoreNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Record storage is not available.") from exc
    return result
