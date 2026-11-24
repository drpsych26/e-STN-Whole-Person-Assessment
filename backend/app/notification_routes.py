"""Routes for notification preferences (any signed-in role) and the admin outbox view (metadata only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from . import db
from . import notifications as svc
from .clients import _payload
from .rbac import ADMIN, CLIENT, CLINICIAN, REVIEWER, require_roles

router = APIRouter(tags=["notifications"])
any_role = require_roles(CLINICIAN, REVIEWER, ADMIN, CLIENT, check_registration=False)
admin = require_roles(ADMIN)


@router.post("/v1/me/notification-preferences")
async def set_preference(request: Request, identity: dict = Depends(any_role)) -> dict:
    """Body: category, opted_out (bool). Safety and security notices cannot be turned off."""
    body = await _payload(request)
    try:
        return svc.set_preference(identity["sub"], identity["org"], body.get("category"), body.get("opted_out"))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except db.StoreNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Record storage is not available.") from exc


@router.get("/v1/admin/notifications")
def outbox(status_filter: str | None = Query(None, alias="status", pattern="^(pending|sent|dead|suppressed)$"),
           identity: dict = Depends(admin)) -> dict:
    """Provider state and recent notifications (no content, no parameters). Use status=dead for failures."""
    try:
        return svc.list_for_admin(identity["sub"], identity["org"], status_filter)
    except db.StoreNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Record storage is not available.") from exc
