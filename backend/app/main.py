"""Non-live STN API. Consent endpoints only; no assessment content is stored or served."""
from __future__ import annotations

import os
import re
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, StrictBool

from .auth import require_identity
from .store import Store

CLIENT_REF = re.compile(r"^C-[0-9]{4,10}$")
APPROVED_PURPOSES = ("assessment", "follow-up", "care-planning")
CLINICIAN_ROLE = "clinician"

app = FastAPI(
    title="STN API",
    version="0.2.0",
    description=(
        "Non-live integration foundation. Consent records and audit events only; "
        "no client assessment content, clinical decisions or crisis workflows are exposed."
    ),
)


def get_store(request: Request) -> Store:
    store = getattr(request.app.state, "store", None)
    if store is None:
        store = Store(os.getenv("STN_DB_PATH", "stn-dev.db"))
        request.app.state.store = store
    return store


def require_clinician(identity: dict = Depends(require_identity)) -> dict:
    if CLINICIAN_ROLE not in identity.get("roles", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinician role required.")
    return identity


class ConsentIn(BaseModel):
    purpose: Literal["assessment", "follow-up", "care-planning"]
    granted: StrictBool


def _check_ref(client_ref: str) -> None:
    if not CLIENT_REF.fullmatch(client_ref):
        raise HTTPException(status_code=422, detail="Invalid client reference.")


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/v1/me", tags=["identity"])
def current_identity(identity: dict = Depends(require_identity)) -> dict:
    """Return only verified token identity and roles."""
    return {"subject": identity["sub"], "authenticated": True, "roles": identity.get("roles", [])}


@app.post("/v1/clients/{client_ref}/consents", status_code=status.HTTP_201_CREATED, tags=["consent"])
def record_consent(client_ref: str, body: ConsentIn, identity: dict = Depends(require_clinician), store: Store = Depends(get_store)) -> dict:
    _check_ref(client_ref)
    record_id = store.record_consent(client_ref, body.purpose, body.granted, identity["sub"])
    return {"id": record_id, "client_ref": client_ref, "purpose": body.purpose, "granted": body.granted}


@app.get("/v1/clients/{client_ref}/consents", tags=["consent"])
def list_consents(client_ref: str, identity: dict = Depends(require_clinician), store: Store = Depends(get_store)) -> dict:
    _check_ref(client_ref)
    store.append_audit(identity["sub"], "consent.viewed", client_ref, {})
    return {"client_ref": client_ref, "consents": store.consents_for(client_ref)}
