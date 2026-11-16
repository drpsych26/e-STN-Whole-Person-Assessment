"""Non-live STN API skeleton. No clinical record endpoints are enabled."""
from fastapi import Depends, FastAPI

from .auth import require_identity

app = FastAPI(
    title="STN API",
    version="0.1.0",
    description=(
        "Non-live integration foundation. No client records, assessment responses, "
        "clinical decisions, or crisis workflows are exposed."
    ),
)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/v1/me", tags=["identity"])
def current_identity(identity: dict = Depends(require_identity)) -> dict:
    """Return only verified token identity; permissions are not yet implemented."""
    return {"subject": identity["sub"], "authenticated": True}
