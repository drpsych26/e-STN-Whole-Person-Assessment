"""Signed-token authorisation tests for GET /v1/me (synthetic keys only).

These exercise the success and failure paths of require_identity() that the
original suite did not cover. The JWKS lookup is replaced by a local RSA key,
so no network or identity-provider access is needed.
"""
from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import auth
from app.main import app

ISSUER = "https://idp.example.test/"
AUDIENCE = "stn-api-test"
JWKS_URL = "https://idp.example.test/.well-known/jwks.json"

_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC = _PRIVATE.public_key()
_OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJwks:
    def get_signing_key_from_jwt(self, token):  # noqa: D401 - PyJWKClient interface
        return _FakeSigningKey(_PUBLIC)


@pytest.fixture(autouse=True)
def _configured_provider(monkeypatch):
    monkeypatch.setenv("STN_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("STN_OIDC_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("STN_OIDC_JWKS_URL", JWKS_URL)
    monkeypatch.setattr(auth, "_jwks_client", lambda url: _FakeJwks())


def _claims(**overrides):
    now = int(time.time())
    base = {"iss": ISSUER, "aud": AUDIENCE, "sub": "clinician-001", "iat": now, "exp": now + 300}
    base.update(overrides)
    return base


def _rs256(claims, key=_PRIVATE):
    return jwt.encode(claims, key, algorithm="RS256")


client = TestClient(app)


def _get(token):
    return client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})


def test_valid_signed_token_is_accepted():
    response = _get(_rs256(_claims()))
    assert response.status_code == 200
    assert response.json() == {"subject": "clinician-001", "authenticated": True}


def test_expired_token_is_rejected():
    response = _get(_rs256(_claims(exp=int(time.time()) - 60, iat=int(time.time()) - 400)))
    assert response.status_code == 401


def test_wrong_audience_is_rejected():
    response = _get(_rs256(_claims(aud="some-other-api")))
    assert response.status_code == 401


def test_wrong_issuer_is_rejected():
    response = _get(_rs256(_claims(iss="https://attacker.example.test/")))
    assert response.status_code == 401


def test_token_signed_by_untrusted_key_is_rejected():
    response = _get(_rs256(_claims(), key=_OTHER))
    assert response.status_code == 401


def test_unsigned_alg_none_token_is_rejected():
    token = jwt.encode(_claims(), key=None, algorithm="none")
    response = _get(token)
    assert response.status_code == 401


def test_hs256_key_confusion_token_is_rejected():
    """Attacker HMAC-signs using the public key PEM as the shared secret.

    PyJWT refuses to *create* such a token, so the header/signature are built by hand.
    """
    import base64
    import hashlib
    import hmac
    import json

    def b64(data: bytes) -> bytes:
        return base64.urlsafe_b64encode(data).rstrip(b"=")

    pem = _PUBLIC.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64(json.dumps(_claims()).encode())
    signing_input = header + b"." + payload
    sig = b64(hmac.new(pem, signing_input, hashlib.sha256).digest())
    token = (signing_input + b"." + sig).decode()
    response = _get(token)
    assert response.status_code == 401


def test_token_without_subject_is_rejected():
    claims = _claims()
    claims.pop("sub")
    response = _get(_rs256(claims))
    assert response.status_code == 401


def test_blank_subject_is_rejected():
    response = _get(_rs256(_claims(sub="   ")))
    assert response.status_code == 401
