"""Synthetic identity-provider key and signed verification events. Test use only; no network."""
from __future__ import annotations

import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import identity_events

ISSUER = "https://idp.synthetic.test/"
API_AUDIENCE = "stn-api-synthetic"
EVENT_AUDIENCE = "stn-identity-events-synthetic"
JWKS_URL = "https://idp.synthetic.test/jwks"

PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Key:
    def __init__(self, key):
        self.key = key


class _Jwks:
    def get_signing_key_from_jwt(self, token):
        return _Key(PRIVATE.public_key())


@pytest.fixture
def idp(monkeypatch):
    monkeypatch.setenv("STN_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("STN_OIDC_AUDIENCE", API_AUDIENCE)
    monkeypatch.setenv("STN_OIDC_JWKS_URL", JWKS_URL)
    monkeypatch.setenv("STN_IDP_EVENT_AUDIENCE", EVENT_AUDIENCE)
    monkeypatch.setattr(identity_events, "_jwks_client", lambda url: _Jwks())
    return event


def event(subject: str, kind: str = "email_verified", *, key=None, **overrides) -> str:
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": EVENT_AUDIENCE, "sub": subject, "iat": now, "exp": now + 300,
              "jti": "evt-" + uuid.uuid4().hex, "event": kind, "verified": True}
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key or PRIVATE, algorithm="RS256")
