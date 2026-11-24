"""Routes for client accounts, the client's own portal endpoints, and clinician registration.

Status codes: 404 for missing or other-organisation objects (indistinguishable), 403 for a
role or account-status refusal or self-attestation, 409 for a state conflict, 422 for invalid
input or unmet onboarding requirements, 503 when onboarding is not configured.

Client routes (/v1/me/client-*) resolve the client from the verified token subject and
organisation; none accepts a client id.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from . import client_accounts as ca
from . import clinician_registry as reg
from . import db
from .clients import _payload
from .crypto import DataKeyError
from .rbac import ADMIN, CLIENT, CLINICIAN, REVIEWER, require_roles

client_role = require_roles(CLIENT)
clinician = require_roles(CLINICIAN)
clinical = require_roles(CLINICIAN, REVIEWER)
clinician_or_admin = require_roles(CLINICIAN, ADMIN)
admin = require_roles(ADMIN)

# Registration routes must work for unverified clinicians (that is how they get verified).
clinical_unverified = require_roles(CLINICIAN, REVIEWER, check_registration=False)


def _call(fn, *args: Any) -> Any:
    try:
        return fn(*args)
    except (ca.ClientAccountNotFound, reg.RegistryNotFound) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.") from exc
    except ca.InvitationInvalid as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except (ca.ClientAccessDenied, reg.SelfAttestation) as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except (ca.ClientAccountConflict, reg.RegistryConflict) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except ca.RequirementsNotMet as exc:
        raise HTTPException(422, {"message": "Onboarding requirements are not met.", "missing": exc.missing}) from exc
    except (ca.ClientAccountInvalidInput, reg.RegistryInvalidInput) as exc:
        raise HTTPException(422, str(exc)) from exc
    except (ca.OnboardingNotConfigured, reg.RegistryNotConfigured) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except (db.StoreNotConfigured, DataKeyError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Record storage is not available.") from exc


def _client_access(*allowed: str):
    def dependency(identity: dict = Depends(client_role)) -> dict:
        try:
            ca.enforce(identity["org"], identity["sub"], allowed)
        except ca.ClientAccessDenied as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
        except db.StoreNotConfigured as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Record storage is not available.") from exc
        return identity
    return dependency


onboarding_client = _client_access(ca.PROVISIONAL, ca.ACTIVE)
active_client = _client_access(ca.ACTIVE)

router = APIRouter(tags=["client-accounts"])


# --------------------------------------------------------------------------- staff: client accounts


@router.post("/v1/clients/{client_id}/client-account/invitation", status_code=status.HTTP_201_CREATED)
def invite_client(client_id: str, identity: dict = Depends(clinician)) -> dict:
    """Issue (or reissue) a one-time invitation code for the client of a record you own. Shown once."""
    return _call(ca.invite, identity["sub"], identity["org"], client_id)


@router.get("/v1/clients/{client_id}/client-account")
def client_account_status(client_id: str, identity: dict = Depends(clinician_or_admin)) -> dict:
    is_admin = ADMIN in set(identity.get("roles") or ())
    return _call(ca.get_for_staff, identity["sub"], identity["org"], client_id, is_admin)


@router.post("/v1/clients/{client_id}/client-account/activate")
def activate_client(client_id: str, identity: dict = Depends(clinician)) -> dict:
    return _call(ca.activate, identity["sub"], identity["org"], client_id)


@router.post("/v1/admin/client-accounts/{client_id}/{action}")
async def admin_client_status(client_id: str, action: str, request: Request, identity: dict = Depends(admin)) -> dict:
    """action: suspend | reactivate | deactivate. Body: reason_code (required for suspend and deactivate)."""
    if action not in {"suspend", "reactivate", "deactivate"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    body = await _payload(request)
    return _call(ca.change_status, identity["sub"], identity["org"], client_id, action, body.get("reason_code"))


# --------------------------------------------------------------------------- client: own account


@router.post("/v1/me/client-invitation/claim")
async def claim_invitation(request: Request, identity: dict = Depends(client_role)) -> dict:
    body = await _payload(request)
    return _call(ca.claim, identity["sub"], identity["org"], body.get("code"))


@router.get("/v1/me/client-account")
def my_client_account(identity: dict = Depends(onboarding_client)) -> dict:
    return _call(ca.my_status, identity["sub"], identity["org"])


@router.post("/v1/me/client-acknowledgements", status_code=status.HTTP_201_CREATED)
async def acknowledge(request: Request, identity: dict = Depends(onboarding_client)) -> dict:
    """Body: kind (terms | privacy_notice | consent), version (must be the current version)."""
    body = await _payload(request)
    return _call(ca.acknowledge, identity["sub"], identity["org"], body.get("kind"), body.get("version"))


@router.get("/v1/me/client-assessments")
def my_assessments(identity: dict = Depends(active_client)) -> list[dict]:
    """Metadata of your own assessments (no answers or clinician notes). Active accounts only."""
    return _call(ca.my_assessments, identity["sub"], identity["org"])


# --------------------------------------------------------------------------- clinician registration


@router.post("/v1/me/clinician-registration", status_code=status.HTTP_201_CREATED)
async def submit_registration(request: Request, identity: dict = Depends(clinical_unverified)) -> dict:
    body = await _payload(request)
    return _call(reg.submit, identity["sub"], identity["org"], body)


@router.get("/v1/me/clinician-registration")
def my_registration(identity: dict = Depends(clinical_unverified)) -> dict:
    return _call(reg.my_status, identity["sub"], identity["org"])


@router.get("/v1/admin/clinician-registrations")
def list_registrations(identity: dict = Depends(admin)) -> list[dict]:
    return _call(reg.list_status, identity["sub"], identity["org"])


@router.post("/v1/admin/clinician-registrations/{registration_id}/attest", status_code=status.HTTP_201_CREATED)
async def attest_registration(registration_id: str, request: Request, identity: dict = Depends(admin)) -> dict:
    """Body: source_url (https public-register entry), checked_on (YYYY-MM-DD)."""
    body = await _payload(request)
    return _call(reg.attest, identity["sub"], identity["org"], registration_id, body)


@router.post("/v1/admin/attestations/{attestation_id}/revoke")
def revoke_attestation(attestation_id: str, identity: dict = Depends(admin)) -> dict:
    return _call(reg.revoke, identity["sub"], identity["org"], attestation_id)
