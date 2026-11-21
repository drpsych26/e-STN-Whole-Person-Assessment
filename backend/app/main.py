"""Non-live STN API skeleton. No clinical record endpoints are enabled."""
from fastapi import Depends, FastAPI

from .auth import require_identity
from .clients import router as clients_router
from .onboarding import router as onboarding_router
from .rbac import router as admin_router
from .verification import router as verification_router

app = FastAPI(
    title="STN API",
    version="0.1.0",
    description=(
        "Integration API. Client records are encrypted at rest and owner-scoped; "
        "clinical decisions and crisis workflows are not exposed."
    ),
)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/v1/me", tags=["identity"])
def current_identity(identity: dict = Depends(require_identity)) -> dict:
    """Return only verified token identity; permissions are not yet implemented."""
    return {"subject": identity["sub"], "authenticated": True}

app.include_router(clients_router)
app.include_router(onboarding_router)
app.include_router(admin_router)
app.include_router(verification_router)
