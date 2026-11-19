"""Consent API tests: role enforcement, validation, persistence and audit (synthetic keys only)."""
from __future__ import annotations

import os
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import auth, main
from app.main import app
from app.store import Store

ISSUER = "https://idp.example.test/"
AUDIENCE = "stn-api-test"
JWKS_URL = "https://idp.example.test/.well-known/jwks.json"
_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Key:
    def __init__(self, key):
        self.key = key


class _Jwks:
    def get_signing_key_from_jwt(self, token):
        return _Key(_PRIVATE.public_key())


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("STN_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("STN_OIDC_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("STN_OIDC_JWKS_URL", JWKS_URL)
    monkeypatch.setattr(auth, "_jwks_client", lambda url: _Jwks())
    monkeypatch.setenv("STN_DB_PATH", str(tmp_path / "test.db"))
    app.state.store = None
    yield
    if getattr(app.state, "store", None):
        app.state.store.close()
    app.state.store = None


def _token(roles=None, sub="clinician-001"):
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": sub, "iat": now, "exp": now + 300}
    if roles is not None:
        claims["roles"] = roles
    return jwt.encode(claims, _PRIVATE, algorithm="RS256")


def _h(roles=None, sub="clinician-001"):
    return {"Authorization": f"Bearer {_token(roles, sub)}"}


client = TestClient(app)
BODY = {"purpose": "assessment", "granted": True}


def test_clinician_can_record_and_read_consent():
    r = client.post("/v1/clients/C-0001/consents", json=BODY, headers=_h(["clinician"]))
    assert r.status_code == 201
    r = client.get("/v1/clients/C-0001/consents", headers=_h(["clinician"]))
    assert r.status_code == 200
    assert [c["purpose"] for c in r.json()["consents"]] == ["assessment"]


def test_non_clinician_is_forbidden():
    assert client.post("/v1/clients/C-0001/consents", json=BODY, headers=_h(["admin"])).status_code == 403
    assert client.get("/v1/clients/C-0001/consents", headers=_h(None)).status_code == 403


def test_missing_token_is_unauthorised():
    assert client.post("/v1/clients/C-0001/consents", json=BODY).status_code == 401


def test_invalid_client_reference_is_rejected():
    r = client.post("/v1/clients/bad;drop/consents", json=BODY, headers=_h(["clinician"]))
    assert r.status_code == 422


def test_unapproved_purpose_is_rejected():
    r = client.post("/v1/clients/C-0001/consents", json={"purpose": "marketing", "granted": True}, headers=_h(["clinician"]))
    assert r.status_code == 422


def test_non_boolean_granted_is_rejected():
    r = client.post("/v1/clients/C-0001/consents", json={"purpose": "assessment", "granted": "yes"}, headers=_h(["clinician"]))
    assert r.status_code == 422


def test_reads_and_writes_are_audited():
    client.post("/v1/clients/C-0002/consents", json=BODY, headers=_h(["clinician"], sub="clin-A"))
    client.get("/v1/clients/C-0002/consents", headers=_h(["clinician"], sub="clin-B"))
    store = Store(os.environ["STN_DB_PATH"])
    actions = [(e["actor"], e["action"]) for e in store.audit_events("C-0002")]
    store.close()
    assert ("clin-A", "consent.recorded") in actions
    assert ("clin-B", "consent.viewed") in actions


def test_consent_persists_across_app_store_restart(tmp_path, monkeypatch):
    client.post("/v1/clients/C-0003/consents", json=BODY, headers=_h(["clinician"]))
    app.state.store.close()
    app.state.store = None  # simulate restart: next request reopens the same file
    r = client.get("/v1/clients/C-0003/consents", headers=_h(["clinician"]))
    assert len(r.json()["consents"]) == 1
