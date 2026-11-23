"""Shared (Redis) rate-limit store: configuration, fail-closed behaviour and live Redis tests.

Live tests run when STN_TEST_REDIS_URL is set; CI also sets STN_REQUIRE_REDIS_TESTS=1 so
a missing Redis fails the run instead of skipping it. Keys use a per-test prefix.
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app import ratelimit
from app.main import app
from app.ratelimit import RateLimitConfigError, RateLimitUnavailable, RedisRateLimiter

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def restore_limiter():
    saved = ratelimit.limiter()
    yield
    ratelimit.set_rate_limiter(saved)


@pytest.fixture
def redis_url() -> str:
    url = os.getenv("STN_TEST_REDIS_URL", "").strip()
    if not url:
        if os.getenv("STN_REQUIRE_REDIS_TESTS") == "1":
            pytest.fail("STN_REQUIRE_REDIS_TESTS=1 but STN_TEST_REDIS_URL is not set.")
        pytest.skip("Redis tests need STN_TEST_REDIS_URL.")
    return url


@pytest.fixture
def redis_limiter(redis_url):
    limiter = RedisRateLimiter(redis_url, prefix=f"stn:test:{uuid.uuid4().hex}:")
    yield limiter
    limiter.reset()


# --------------------------------------------------------------------------- configuration (no Redis needed)


def test_backend_selection_fails_closed(monkeypatch):
    monkeypatch.delenv(ratelimit.BACKEND_ENV, raising=False)
    assert isinstance(ratelimit.limiter_from_env(), ratelimit.InMemoryRateLimiter)
    monkeypatch.setenv(ratelimit.BACKEND_ENV, "memcached")
    with pytest.raises(RateLimitConfigError, match="Unknown"):
        ratelimit.limiter_from_env()
    monkeypatch.setenv(ratelimit.BACKEND_ENV, "redis")
    monkeypatch.delenv(ratelimit.REDIS_URL_ENV, raising=False)
    with pytest.raises(RateLimitConfigError, match="STN_REDIS_URL"):
        ratelimit.limiter_from_env()
    monkeypatch.setenv(ratelimit.REDIS_URL_ENV, "redis://127.0.0.1:6379/0")
    assert isinstance(ratelimit.limiter_from_env(), RedisRateLimiter), "built lazily; no connection yet"


def test_unreachable_redis_refuses_requests(act, restore_limiter):
    broken = RedisRateLimiter("redis://127.0.0.1:1/0", prefix="stn:test:broken:")
    with pytest.raises(RateLimitUnavailable):
        broken.hit("k", 5, 60)
    ratelimit.set_rate_limiter(broken)
    act("clin-redis", "clinician")
    response = client.get("/v1/me/access")
    assert response.status_code == 503 and "unavailable" in response.json()["detail"]
    assert client.get("/health/live").status_code == 200, "health stays outside /v1"


# --------------------------------------------------------------------------- live Redis


def test_redis_window_limit_and_retry_after(redis_limiter):
    assert redis_limiter.hit("k", 2, 2) == (True, 0)
    assert redis_limiter.hit("k", 2, 2) == (True, 0)
    allowed, retry = redis_limiter.hit("k", 2, 2)
    assert not allowed and 1 <= retry <= 2
    over, retry = redis_limiter.exceeded("k", 2, 2)
    assert over and 1 <= retry <= 2
    assert redis_limiter.exceeded("other", 2, 2) == (False, 0)
    time.sleep(2.2)
    assert redis_limiter.exceeded("k", 2, 2) == (False, 0)
    assert redis_limiter.hit("k", 2, 2) == (True, 0)


def test_redis_state_is_shared_between_instances(redis_url, redis_limiter):
    prefix = redis_limiter._prefix
    second_instance = RedisRateLimiter(redis_url, prefix=prefix)
    assert redis_limiter.hit("shared", 2, 60)[0] and second_instance.hit("shared", 2, 60)[0]
    assert redis_limiter.hit("shared", 2, 60)[0] is False, "the other instance's hit counts"
    unrelated = RedisRateLimiter(redis_url, prefix=f"stn:test:{uuid.uuid4().hex}:")
    assert unrelated.hit("shared", 2, 60) == (True, 0), "prefixes isolate deployments"
    redis_limiter.reset()
    assert redis_limiter.hit("shared", 2, 60) == (True, 0)
    assert unrelated.exceeded("shared", 1, 60)[0] is True, "reset only clears its own prefix"
    unrelated.reset()


def test_api_limits_through_redis(act, monkeypatch, redis_limiter, restore_limiter):
    ratelimit.set_rate_limiter(redis_limiter)
    monkeypatch.setenv("STN_RATE_LIMIT_IP_PER_MINUTE", "3")
    act("clin-redis-api", "clinician")
    statuses = [client.get("/v1/me/access").status_code for _ in range(4)]
    assert statuses == [200, 200, 200, 429]
