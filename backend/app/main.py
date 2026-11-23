"""STN API (non-live). Synthetic data only until every production go-live gate is signed."""
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from . import ratelimit
from .assessment_routes import audit_router
from .assessment_routes import router as assessments_router
from .auth import require_identity
from .clients import router as clients_router
from .governance_routes import admin_router, consent_router
from .rbac import mfa_required

app = FastAPI(
    title="STN API",
    version="0.3.0",
    description=(
        "Non-live integration API. Clinician sign-in via OIDC, server-side roles "
        "(clinician, reviewer, admin), MFA enforcement and organisation scoping; encrypted, "
        "owner-scoped client and assessment records with key rotation; human review and "
        "sign-off workflow; consent records, legal holds and two-person disposal; logged "
        "exports; rate limiting; hash-chained audit. No diagnosis, scoring, risk disposition "
        "or crisis automation is exposed."
    ),
)


@app.middleware("http")
async def per_ip_rate_limit(request: Request, call_next):
    """Per-IP request limit on the /v1 API (see app.ratelimit)."""
    if request.url.path.startswith("/v1/"):
        allowed, retry_after = ratelimit.check_ip(request)
        if not allowed:
            return JSONResponse(
                {"detail": "Too many requests; slow down and retry later."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/v1/me", tags=["identity"])
def current_identity(identity: dict = Depends(require_identity)) -> dict:
    """Return only the verified token subject."""
    return {"subject": identity["sub"], "authenticated": True}


@app.get("/v1/me/access", tags=["identity"])
def current_access(identity: dict = Depends(require_identity)) -> dict:
    """Effective STN roles, organisation and MFA status derived from the verified token (no client data)."""
    return {
        "subject": identity["sub"],
        "roles": list(identity.get("roles") or ()),
        "organisation": identity.get("org"),
        "mfa": bool(identity.get("mfa")),
        "mfa_required": mfa_required(),
    }


app.include_router(clients_router)
app.include_router(assessments_router)
app.include_router(consent_router)
app.include_router(admin_router)
app.include_router(audit_router)
