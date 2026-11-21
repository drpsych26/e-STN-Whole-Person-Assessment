"""Authenticated client-record routes. Every route requires a verified identity.

Access rule: a clinician can create, read and update only records they own.
Missing and not-owned records both return 404. Payloads are capped in size.
The payload schema is intentionally generic: clinical field definitions must be
approved through clinical governance before any real client data is entered.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from . import store
from .crypto import DataKeyError, RecordIntegrityError
from .ratelimit import limit_by_subject
from .rbac import require_permission

router = APIRouter(prefix="/v1/clients", tags=["client-records"])

MAX_PAYLOAD_BYTES = 64 * 1024


async def _payload(request: Request) -> dict[str, Any]:
    raw = await request.body()
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Payload exceeds the size limit.")
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Body must be a JSON object.") from exc
    if not isinstance(body, dict):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Body must be a JSON object.")
    return body


def _map_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, store.StoreNotConfigured) or isinstance(exc, DataKeyError):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Client record storage is not available.")
    if isinstance(exc, RecordIntegrityError):
        return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Record could not be verified.")
    raise exc


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_client_record(request: Request, identity: dict = Depends(require_permission("client:create")),
                               _limit: dict = Depends(limit_by_subject("client-write", 30))) -> dict:
    payload = await _payload(request)
    try:
        record_id = store.create_record(identity["sub"], payload)
    except (store.StoreNotConfigured, DataKeyError) as exc:
        raise _map_errors(exc) from exc
    return {"id": record_id}


@router.get("/{record_id}")
def read_client_record(record_id: str, identity: dict = Depends(require_permission("clinical:read_assigned")),
                       _limit: dict = Depends(limit_by_subject("client-read", 120))) -> dict:
    try:
        payload = store.read_record(identity["sub"], record_id)
    except store.RecordNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.") from exc
    except (store.StoreNotConfigured, DataKeyError, RecordIntegrityError) as exc:
        raise _map_errors(exc) from exc
    return {"id": record_id, "payload": payload}


@router.put("/{record_id}")
async def update_client_record(
    record_id: str, request: Request, identity: dict = Depends(require_permission("clinical:write_assigned")),
    _limit: dict = Depends(limit_by_subject("client-write", 30)),
) -> dict:
    payload = await _payload(request)
    try:
        store.update_record(identity["sub"], record_id, payload)
    except store.RecordNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.") from exc
    except (store.StoreNotConfigured, DataKeyError) as exc:
        raise _map_errors(exc) from exc
    return {"id": record_id, "updated": True}
