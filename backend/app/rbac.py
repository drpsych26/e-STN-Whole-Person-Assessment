"""Server-side roles and MFA enforcement derived only from verified token claims.

Roles come from a configurable claim (default "roles", as issued by Microsoft
Entra ID app roles). Provider role values map to STN roles through
STN_OIDC_ROLE_MAP, e.g. "STN.Clinician=clinician,STN.Reviewer=reviewer,STN.Admin=admin".
Without a map, only the exact values clinician, reviewer and admin are accepted.
Unknown values are ignored. No role means no access to protected routes.

MFA: when STN_REQUIRE_MFA is on (the default; only "false", "0", "no" or "off"
disable it), role-protected routes accept a token only if it shows a strong
authentication method through one of:
- amr claim containing a value in STN_MFA_AMR_VALUES (default "mfa"),
- acr claim equal to a value in STN_MFA_ACR_VALUES (default none),
- acrs claim (Entra authentication context) containing a value in STN_MFA_ACRS_VALUES (default none).

Organisation: every role-protected route needs an organisation id from the claim
named by STN_OIDC_ORG_CLAIM (default "stn_org"; for one organisation per Entra
tenant set it to "tid"). Values must be 1-128 letters, digits, '_', '.', ':' or '-'.
A token without a valid organisation is refused (403). All records, audit events,
consents, holds, disposals and exports are scoped to that organisation; records of
another organisation are indistinguishable from missing ones (404).

Write requests are rate limited per subject after authorisation (app.ratelimit).
"""
from __future__ import annotations

import os
import re
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status

from . import ratelimit

CLINICIAN = "clinician"
REVIEWER = "reviewer"
ADMIN = "admin"
STN_ROLES = frozenset({CLINICIAN, REVIEWER, ADMIN})
_ORG = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def _csv(name: str, default: str = "") -> set[str]:
    return {v.strip() for v in os.getenv(name, default).split(",") if v.strip()}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return value.split()
    if isinstance(value, (list, tuple)):
        return [v for v in value if isinstance(v, str)]
    return []


def _role_map() -> dict[str, str]:
    raw = os.getenv("STN_OIDC_ROLE_MAP", "").strip()
    if not raw:
        return {r: r for r in STN_ROLES}
    mapping: dict[str, str] = {}
    for pair in raw.split(","):
        if "=" not in pair:
            continue
        provider_value, stn_role = (p.strip() for p in pair.split("=", 1))
        if provider_value and stn_role in STN_ROLES:
            mapping[provider_value] = stn_role
    return mapping


def roles_from_claims(claims: dict[str, Any]) -> tuple[str, ...]:
    claim = os.getenv("STN_OIDC_ROLES_CLAIM", "roles").strip() or "roles"
    mapping = _role_map()
    return tuple(sorted({mapping[v] for v in _as_list(claims.get(claim)) if v in mapping}))


def org_from_claims(claims: dict[str, Any]) -> str | None:
    claim = os.getenv("STN_OIDC_ORG_CLAIM", "stn_org").strip() or "stn_org"
    value = claims.get(claim)
    return value if isinstance(value, str) and _ORG.match(value) else None


def mfa_from_claims(claims: dict[str, Any]) -> bool:
    if set(_as_list(claims.get("amr"))) & _csv("STN_MFA_AMR_VALUES", "mfa"):
        return True
    acr = claims.get("acr")
    if isinstance(acr, str) and acr in _csv("STN_MFA_ACR_VALUES"):
        return True
    return bool(set(_as_list(claims.get("acrs"))) & _csv("STN_MFA_ACRS_VALUES"))


def mfa_required() -> bool:
    return os.getenv("STN_REQUIRE_MFA", "true").strip().lower() not in {"false", "0", "no", "off"}


def require_roles(*allowed: str) -> Callable[..., dict[str, Any]]:
    """Dependency factory: verified identity, MFA (when required) and one of the allowed roles."""
    from .auth import require_identity  # local import avoids a cycle

    wanted = frozenset(allowed)

    def dependency(request: Request, identity: dict = Depends(require_identity)) -> dict[str, Any]:
        roles = set(identity.get("roles") or ())
        org = identity.get("org")
        if mfa_required() and not identity.get("mfa", False):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Multi-factor authentication is required.")
        if not roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No STN role is assigned to this account.")
        if not isinstance(org, str) or not _ORG.match(org):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No organisation is assigned to this account.")
        if not roles & wanted:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This account's role does not permit this action.")
        ratelimit.check_write(request, org, identity["sub"])
        return identity

    dependency.__name__ = "require_" + "_or_".join(sorted(wanted))
    return dependency
