"""Fail-closed OIDC access-token verification for the non-live STN API."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from . import ratelimit

_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300)


def require_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """Validate a signed RS256 bearer token; never trust client-supplied roles.

    Rejected tokens count towards a per-IP failure limit (app.ratelimit); an IP over
    the limit gets 429 before its token is examined.
    """
    ratelimit.auth_blocked(request)
    if credentials is None or credentials.scheme.lower() != "bearer":
        ratelimit.record_auth_failure(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid bearer access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    issuer = os.getenv("STN_OIDC_ISSUER", "").strip()
    audience = os.getenv("STN_OIDC_AUDIENCE", "").strip()
    jwks_url = os.getenv("STN_OIDC_JWKS_URL", "").strip()
    if not issuer or not audience or not jwks_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity provider is not configured; protected routes are disabled.",
        )

    token = credentials.credentials
    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "sub"]},
        )
    except Exception as exc:
        # Fail closed. Do not expose token, key, or provider details to callers.
        ratelimit.record_auth_failure(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        ratelimit.record_auth_failure(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has no valid subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from .rbac import mfa_from_claims, org_from_claims, roles_from_claims

    return {
        "sub": subject,
        "issuer": issuer,
        "audience": audience,
        "roles": roles_from_claims(claims),
        "mfa": mfa_from_claims(claims),
        "org": org_from_claims(claims),
    }
