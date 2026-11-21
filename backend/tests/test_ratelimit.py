"""Rate-limit tests: sliding window behaviour and route enforcement. Synthetic identities only."""
from __future__ import annotations

import base64
import secrets

import pytest
from fastapi.testclient import TestClient

from app import auth, ratelimit, rbac, store
from app.main import app

client = TestClient(app)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_window_allows_then_refuses_then_recovers():
    clock = FakeClock()
    limiter = ratelimit.RateLimiter(clock=clock)
    assert limiter.hit("b", "k", 2, 60)
    assert limiter.hit("b", "k", 2, 60)
    assert not limiter.hit("b", "k", 2, 60)
    clock.now = 61.0
    assert limiter.hit("b", "k", 2, 60)


def test_refused_hits_are_not_recorded_so_they_cannot_extend_the_block():
    clock = FakeClock()
    limiter = ratelimit.RateLimiter(clock=clock)
    limiter.hit("b", "k", 1, 60)
    for _ in range(5):
        clock.now += 10
        assert not limiter.hit("b", "k", 1, 60)
    clock.now = 61.0
    assert limiter.hit("b", "k", 1, 60)


def test_keys_and_buckets_are_independent():
    clock = FakeClock()
    limiter = ratelimit.RateLimiter(clock=clock)
    assert limiter.hit("b", "alice", 1, 60)
    assert limiter.hit("b", "bob", 1, 60)
    assert limiter.hit("c", "alice", 1, 60)
    assert not limiter.hit("b", "alice", 1, 60)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv(store.DB_ENV, str(tmp_path / "rl.sqlite3"))
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    rbac.grant_system_role("clinician-rl", rbac.Role.AUTHORISED_CLINICIAN)
    ratelimit.LIMITER.reset()
    app.dependency_overrides[auth.require_identity] = lambda: {"sub": "clinician-rl"}
    yield
    app.dependency_overrides.pop(auth.require_identity, None)
    ratelimit.LIMITER.reset()


def test_client_write_route_returns_429_after_limit(env):
    statuses = [client.post("/v1/clients", json={"synthetic": i}).status_code for i in range(31)]
    assert statuses[:30] == [201] * 30
    assert statuses[30] == 429


def test_429_carries_retry_after_header(env):
    for i in range(30):
        client.post("/v1/clients", json={"synthetic": i})
    response = client.post("/v1/clients", json={"synthetic": "x"})
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "60"


def test_limit_applies_after_authentication_not_before(monkeypatch):
    """Unauthenticated requests are refused by authentication, not counted against a subject."""
    app.dependency_overrides.pop(auth.require_identity, None)
    ratelimit.LIMITER.reset()
    for _ in range(40):
        response = client.post("/v1/clients", json={"x": 1})
        assert response.status_code in (401, 503)
    assert not any(bucket == "client-write" for bucket, _ in ratelimit.LIMITER._events)


def test_verification_ingestion_is_limited_per_address(monkeypatch):
    ratelimit.LIMITER.reset()
    monkeypatch.delenv("STN_OIDC_ISSUER", raising=False)
    codes = [client.post("/v1/verification/events", json={"token": "x"}).status_code for i in range(61)]
    assert codes[-1] == 429
    ratelimit.LIMITER.reset()
