"""Roles and MFA from real signed tokens (local RSA key, no network). Synthetic only."""
from __future__ import annotations

import base64
import secrets
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import auth
from app.main import app

ISSUER = "https://idp.example.test/"
AUDIENCE = "stn-api-test"
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Jwks:
    def get_signing_key_from_jwt(self, token):
        return type("K", (), {"key": _KEY.public_key()})()


@pytest.fixture(autouse=True)
def configured(monkeypatch, tmp_path):
    for name in ("STN_REQUIRE_MFA", "STN_OIDC_ROLE_MAP", "STN_OIDC_ROLES_CLAIM", "STN_MFA_AMR_VALUES",
                 "STN_MFA_ACR_VALUES", "STN_MFA_ACRS_VALUES", "STN_DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("STN_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("STN_OIDC_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("STN_OIDC_JWKS_URL", "https://idp.example.test/jwks")
    monkeypatch.setattr(auth, "_jwks_client", lambda url: _Jwks())
    monkeypatch.setenv("STN_DATA_DB", str(tmp_path / "rbac.sqlite3"))
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    app.dependency_overrides.clear()


client = TestClient(app)


def token(**claims) -> str:
    now = int(time.time())
    body = {"iss": ISSUER, "aud": AUDIENCE, "sub": "clinician-001", "iat": now, "exp": now + 300}
    body.update(claims)
    return jwt.encode(body, _KEY, algorithm="RS256")


def create_client(tok: str):
    return client.post("/v1/clients", json={"display_code": "SYN-1"}, headers={"Authorization": f"Bearer {tok}"})


def test_clinician_with_mfa_can_create_records():
    assert create_client(token(roles=["clinician"], amr=["pwd", "mfa"])).status_code == 201


def test_missing_roles_fail_closed():
    response = create_client(token(amr=["mfa"]))
    assert response.status_code == 403 and "No STN role" in response.json()["detail"]


def test_unknown_role_values_are_ignored():
    assert create_client(token(roles=["superuser", "Clinician"], amr=["mfa"])).status_code == 403


def test_mfa_is_required_by_default():
    response = create_client(token(roles=["clinician"], amr=["pwd"]))
    assert response.status_code == 403 and "Multi-factor" in response.json()["detail"]


def test_mfa_cannot_be_disabled_by_an_unrecognised_value(monkeypatch):
    monkeypatch.setenv("STN_REQUIRE_MFA", "maybe")
    assert create_client(token(roles=["clinician"])).status_code == 403


def test_mfa_can_be_disabled_explicitly_for_non_production(monkeypatch):
    monkeypatch.setenv("STN_REQUIRE_MFA", "false")
    assert create_client(token(roles=["clinician"])).status_code == 201


def test_acr_and_acrs_satisfy_mfa_when_configured(monkeypatch):
    monkeypatch.setenv("STN_MFA_ACRS_VALUES", "c1")
    assert create_client(token(roles=["clinician"], acrs=["c1"])).status_code == 201
    assert create_client(token(roles=["clinician"], acrs=["c2"])).status_code == 403
    monkeypatch.setenv("STN_MFA_ACR_VALUES", "urn:stn:mfa")
    assert create_client(token(roles=["clinician"], acr="urn:stn:mfa")).status_code == 201


def test_provider_role_names_map_to_stn_roles(monkeypatch):
    monkeypatch.setenv("STN_OIDC_ROLE_MAP", "STN.Clinician=clinician,STN.Reviewer=reviewer,Bad=superuser")
    assert create_client(token(roles=["STN.Clinician"], amr=["mfa"])).status_code == 201
    assert create_client(token(roles=["clinician"], amr=["mfa"])).status_code == 403, "unmapped once a map is set"
    assert create_client(token(roles=["Bad"], amr=["mfa"])).status_code == 403


def test_custom_roles_claim_and_space_separated_values(monkeypatch):
    monkeypatch.setenv("STN_OIDC_ROLES_CLAIM", "stn_roles")
    assert create_client(token(stn_roles="reviewer clinician", amr=["mfa"])).status_code == 201
    assert create_client(token(roles=["clinician"], amr=["mfa"])).status_code == 403


def test_wrong_role_for_route_is_forbidden():
    headers = {"Authorization": f"Bearer {token(roles=['reviewer'], amr=['mfa'])}"}
    assert client.post("/v1/clients", json={}, headers=headers).status_code == 403
    admin = {"Authorization": f"Bearer {token(roles=['admin'], amr=['mfa'])}"}
    assert client.get("/v1/review-queue", headers=admin).status_code == 403
    assert client.get("/v1/audit/verify", headers=admin).status_code == 200


def test_access_endpoint_reports_effective_roles():
    headers = {"Authorization": f"Bearer {token(roles=['reviewer', 'clinician'], amr=['mfa'])}"}
    body = client.get("/v1/me/access", headers=headers).json()
    assert body == {"subject": "clinician-001", "roles": ["clinician", "reviewer"], "mfa": True, "mfa_required": True}


def test_invalid_token_is_401_before_any_role_check():
    assert client.post("/v1/clients", json={}, headers={"Authorization": "Bearer junk"}).status_code == 401
