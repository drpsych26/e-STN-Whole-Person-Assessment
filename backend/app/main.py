"""STN API (non-live). Synthetic data only until every production go-live gate is signed."""
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from . import health, ratelimit
from .assessment_routes import audit_router
from .assessment_routes import router as assessments_router
from .auth import require_identity
from .clients import router as clients_router
from .governance_routes import admin_router, consent_router
from .lifecycle_routes import admin_router as lifecycle_admin_router
from .lifecycle_routes import clinician_router as privacy_router
from .rbac import mfa_required
from .safety_routes import router as safety_router
from .identity_events import router as identity_router
from .onboarding_routes import router as onboarding_router
from .notification_routes import router as notification_router
from .crisis_resources import router as crisis_router

app = FastAPI(
    title="STN API",
    version="0.5.0",
    description=(
        "Non-live integration API (synthetic data only). Clinician and client sign-in via OIDC; "
        "server-side roles (clinician, reviewer, admin, client), MFA and organisation scoping; "
        "verified-registration enforcement for clinical routes; identity-provider verification "
        "events; client invitation, onboarding and own-record access; encrypted, owner-scoped "
        "records with key rotation; human review and sign-off; consent, legal holds and two-person "
        "disposal; reviewer assignment; account registry; privacy access and correction requests; "
        "safety escalations (open, acknowledge, hand over, resolve) with a notification outbox; a "
        "public crisis-resource register; rate limiting; hash-chained audit with verified export. "
        "No diagnosis, scoring, risk disposition or automated crisis response is exposed, and "
        "nothing here is clinically approved."
    ),
)


# Build the rate limiter now so a misconfigured store stops the API from starting (fail closed).
ratelimit.limiter()


@app.middleware("http")
async def per_ip_rate_limit(request: Request, call_next):
    """Per-IP request limit on the /v1 API (see app.ratelimit)."""
    if request.url.path.startswith("/v1/"):
        try:
            allowed, retry_after = ratelimit.check_ip(request)
        except ratelimit.RateLimitUnavailable:
            return JSONResponse({"detail": "Rate limiting is unavailable; retry later."}, status_code=503)
        if not allowed:
            return JSONResponse(
                {"detail": "Too many requests; slow down and retry later."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


# JSON API responses never need to load scripts, styles or frames. The interactive API docs do,
# so they keep FastAPI's defaults and get every header except the CSP.
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Security headers on every response, including rate-limit refusals and errors."""
    response = await call_next(request)
    for name, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if not request.url.path.startswith(_DOCS_PATHS):
        response.headers.setdefault("Content-Security-Policy", _API_CSP)
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    """Kept for existing callers; /healthz is the platform liveness probe."""
    return {"status": "alive"}


app.include_router(health.make_router(health.api_readiness))


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
app.include_router(lifecycle_admin_router)
app.include_router(privacy_router)
app.include_router(audit_router)
app.include_router(safety_router)
app.include_router(identity_router)
app.include_router(onboarding_router)
app.include_router(notification_router)
app.include_router(crisis_router)


# Registered last, so it is the outermost middleware: every response (including rate-limit
# refusals and errors) gets an X-Request-ID and one structured access-log line.
from . import observability  # noqa: E402

app.middleware("http")(observability.middleware)
