"""STN API (non-live). Synthetic data only until every production go-live gate is signed."""
from fastapi import Depends, FastAPI

from .assessment_routes import audit_router
from .assessment_routes import router as assessments_router
from .auth import require_identity
from .clients import router as clients_router
from .rbac import mfa_required

app = FastAPI(
    title="STN API",
    version="0.2.0",
    description=(
        "Non-live integration API. Clinician sign-in via OIDC, server-side roles "
        "(clinician, reviewer, admin) and MFA enforcement; encrypted, owner-scoped client "
        "and assessment records; human review and sign-off workflow; hash-chained audit. "
        "No diagnosis, scoring, risk disposition or crisis automation is exposed."
    ),
)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/v1/me", tags=["identity"])
def current_identity(identity: dict = Depends(require_identity)) -> dict:
    """Return only the verified token subject."""
    return {"subject": identity["sub"], "authenticated": True}


@app.get("/v1/me/access", tags=["identity"])
def current_access(identity: dict = Depends(require_identity)) -> dict:
    """Effective STN roles and MFA status derived from the verified token (no client data)."""
    return {
        "subject": identity["sub"],
        "roles": list(identity.get("roles") or ()),
        "mfa": bool(identity.get("mfa")),
        "mfa_required": mfa_required(),
    }


app.include_router(clients_router)
app.include_router(assessments_router)
app.include_router(audit_router)
