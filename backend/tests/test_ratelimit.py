"""Rate limiting: per-subject writes, per-IP requests and per-IP auth failures."""
from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from app.ratelimit import InMemoryRateLimiter

client = TestClient(app, raise_server_exceptions=False)
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_writes_are_limited_per_subject(backend, act, monkeypatch):
    monkeypatch.setenv("STN_RATE_LIMIT_WRITES_PER_MINUTE", "3")
    act("clin-rl", "clinician")
    for _ in range(3):
        assert client.post("/v1/clients", json={"x": 1}).status_code == 201
    limited = client.post("/v1/clients", json={"x": 1})
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) >= 1
    act("clin-rl-2", "clinician")
    assert client.post("/v1/clients", json={"x": 1}).status_code == 201
    act("clin-rl", "clinician")
    assert client.get("/v1/me/access").status_code == 200  # reads are not write-limited


def test_requests_are_limited_per_ip(backend, act, monkeypatch):
    monkeypatch.setenv("STN_RATE_LIMIT_IP_PER_MINUTE", "5")
    act("clin-ip", "clinician")
    statuses = [client.get("/v1/me/access").status_code for _ in range(6)]
    assert statuses == [200] * 5 + [429]
    assert client.get("/health/live").status_code == 200  # health is outside /v1


def test_limits_can_be_disabled(backend, act, monkeypatch):
    monkeypatch.setenv("STN_RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("STN_RATE_LIMIT_IP_PER_MINUTE", "1")
    act("clin-off", "clinician")
    assert {client.get("/v1/me/access").status_code for _ in range(3)} == {200}


@pytest.fixture
def real_tokens(monkeypatch):
    class _Jwks:
        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": _KEY.public_key()})()

    monkeypatch.setenv("STN_OIDC_ISSUER", "https://idp.example.test/")
    monkeypatch.setenv("STN_OIDC_AUDIENCE", "stn-api-test")
    monkeypatch.setenv("STN_OIDC_JWKS_URL", "https://idp.example.test/jwks")
    monkeypatch.setattr(auth, "_jwks_client", lambda url: _Jwks())
    app.dependency_overrides.pop(auth.require_identity, None)
    now = int(time.time())
    return jwt.encode({"iss": "https://idp.example.test/", "aud": "stn-api-test", "sub": "clin-tok",
                       "iat": now, "exp": now + 300}, _KEY, algorithm="RS256")


def test_repeated_auth_failures_block_the_ip(monkeypatch, real_tokens):
    monkeypatch.setenv("STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE", "2")
    bad = {"Authorization": "Bearer not-a-token"}
    assert client.get("/v1/me", headers=bad).status_code == 401
    assert client.get("/v1/me", headers=bad).status_code == 401
    blocked = client.get("/v1/me", headers=bad)
    assert blocked.status_code == 429 and "Retry-After" in blocked.headers
    good = {"Authorization": f"Bearer {real_tokens}"}
    assert client.get("/v1/me", headers=good).status_code == 429


def test_forwarded_for_is_used_only_when_trusted(monkeypatch, real_tokens):
    monkeypatch.setenv("STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE", "1")
    bad = {"Authorization": "Bearer junk", "X-Forwarded-For": "203.0.113.7"}
    assert client.get("/v1/me", headers=bad).status_code == 401
    assert client.get("/v1/me", headers={**bad, "X-Forwarded-For": "203.0.113.8"}).status_code == 429
    monkeypatch.setenv("STN_TRUST_FORWARDED_FOR", "true")
    assert client.get("/v1/me", headers={**bad, "X-Forwarded-For": "203.0.113.9"}).status_code == 401
    assert client.get("/v1/me", headers={**bad, "X-Forwarded-For": "203.0.113.9"}).status_code == 429


def test_in_memory_limiter_window_expires():
    now = [1000.0]
    limiter = InMemoryRateLimiter(clock=lambda: now[0])
    assert limiter.hit("k", 2, 60) == (True, 0)
    assert limiter.hit("k", 2, 60) == (True, 0)
    allowed, retry = limiter.hit("k", 2, 60)
    assert not allowed and retry == 60
    now[0] += 61
    assert limiter.hit("k", 2, 60) == (True, 0)
    assert limiter.exceeded("k", 2, 60) == (False, 0)
