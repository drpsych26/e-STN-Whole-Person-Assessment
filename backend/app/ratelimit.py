"""Request rate limiting behind a small interface.

Three limits (per rolling 60-second window), each configurable:
- STN_RATE_LIMIT_IP_PER_MINUTE (default 600): every /v1 request, per client IP.
- STN_RATE_LIMIT_WRITES_PER_MINUTE (default 120): POST/PUT/PATCH/DELETE per
  authenticated subject (scoped by organisation).
- STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE (default 20): rejected bearer tokens per
  client IP. Once reached, that IP gets 429 until the window passes.
STN_RATE_LIMIT_ENABLED=false turns limiting off (local debugging only).

Store (STN_RATE_LIMIT_BACKEND):
- "memory" (default): InMemoryRateLimiter, state in one process. Single instance only.
- "redis": RedisRateLimiter, a sliding-window log in Redis shared by every API
  instance (for example Azure Cache for Redis). Needs STN_REDIS_URL (rediss:// for
  TLS) and the redis client (pip extra "redis"); STN_REDIS_KEY_PREFIX defaults to
  "stn:rl:". Window arithmetic uses Redis server time inside one atomic script, so
  instances with skewed clocks agree.
Fail closed: an unknown backend, "redis" without a URL, or a missing client library
raises RateLimitConfigError when the limiter is first built (the API does not
start). If Redis cannot be reached at request time the request gets 503, never an
unlimited pass. Gateway limits (Azure Front Door / API Management) can sit in front
as well. The client IP is the socket peer unless STN_TRUST_FORWARDED_FOR is
true, in which case the first X-Forwarded-For address is used; enable that only
behind a proxy that overwrites the header.
"""
from __future__ import annotations

import math
import os
import threading
import time
import uuid
from collections import deque
from typing import Any, Protocol

from fastapi import HTTPException, Request, status

WINDOW_SECONDS = 60
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
DEFAULTS = {
    "STN_RATE_LIMIT_IP_PER_MINUTE": 600,
    "STN_RATE_LIMIT_WRITES_PER_MINUTE": 120,
    "STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE": 20,
}


BACKEND_ENV = "STN_RATE_LIMIT_BACKEND"
REDIS_URL_ENV = "STN_REDIS_URL"
REDIS_PREFIX_ENV = "STN_REDIS_KEY_PREFIX"


class RateLimitConfigError(RuntimeError):
    """The configured rate-limit store is unknown or incomplete."""


class RateLimitUnavailable(RuntimeError):
    """The shared rate-limit store could not be reached; the request is refused."""


class RateLimiter(Protocol):
    def hit(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Record one event. Returns (allowed, retry_after_seconds)."""

    def exceeded(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Check without recording. Returns (exceeded, retry_after_seconds)."""

    def reset(self) -> None: ...


class InMemoryRateLimiter:
    """Sliding-window log per key, single process only."""

    def __init__(self, clock=time.monotonic) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._clock = clock
        self._calls = 0

    def _window(self, key: str, window: int, now: float) -> deque[float]:
        events = self._events.setdefault(key, deque())
        while events and events[0] <= now - window:
            events.popleft()
        return events

    def _retry_after(self, events: deque[float], window: int, now: float) -> int:
        return max(1, math.ceil(events[0] + window - now)) if events else 1

    def _prune(self, now: float, window: int) -> None:
        self._calls += 1
        if self._calls % 1000:
            return
        for key in [k for k, v in self._events.items() if not v or v[-1] <= now - window]:
            del self._events[key]

    def hit(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        with self._lock:
            now = self._clock()
            self._prune(now, window)
            events = self._window(key, window, now)
            if len(events) >= limit:
                return False, self._retry_after(events, window, now)
            events.append(now)
            return True, 0

    def exceeded(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        with self._lock:
            now = self._clock()
            events = self._window(key, window, now)
            if len(events) >= limit:
                return True, self._retry_after(events, window, now)
            return False, 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


# Sliding-window log in a sorted set, atomically: drop events older than the window,
# refuse if the count has reached the limit (returning ms until the oldest expires),
# otherwise record this event when asked to. Times come from Redis (TIME), in ms.
_REDIS_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local record = ARGV[3] == '1'
local member = ARGV[4]
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window_ms)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry = window_ms
  if oldest[2] then retry = tonumber(oldest[2]) + window_ms - now end
  return {0, retry}
end
if record then
  redis.call('ZADD', key, now, member)
  redis.call('PEXPIRE', key, window_ms)
end
return {1, 0}
"""


class RedisRateLimiter:
    """Shared sliding-window log in Redis, for more than one API instance."""

    def __init__(self, url: str, prefix: str = "stn:rl:", client: Any = None) -> None:
        if not url and client is None:
            raise RateLimitConfigError(f"{REDIS_URL_ENV} is required for the redis rate-limit backend.")
        if client is None:
            try:
                import redis  # optional dependency (pip extra "redis")
            except ImportError as exc:
                raise RateLimitConfigError("The redis client library is not installed.") from exc
            client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        self._redis = client
        self._prefix = prefix
        self._script = client.register_script(_REDIS_SCRIPT)

    def _run(self, key: str, limit: int, window: int, record: bool) -> tuple[int, int]:
        try:
            allowed, retry_ms = self._script(
                keys=[self._prefix + key],
                args=[limit, window * 1000, "1" if record else "0", uuid.uuid4().hex],
            )
        except Exception as exc:  # connection, timeout or server error: fail closed
            raise RateLimitUnavailable("Rate-limit store is unavailable.") from exc
        return int(allowed), int(retry_ms)

    @staticmethod
    def _seconds(retry_ms: int) -> int:
        return max(1, math.ceil(retry_ms / 1000))

    def hit(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        allowed, retry_ms = self._run(key, limit, window, True)
        return (True, 0) if allowed else (False, self._seconds(retry_ms))

    def exceeded(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        allowed, retry_ms = self._run(key, limit, window, False)
        return (False, 0) if allowed else (True, self._seconds(retry_ms))

    def ping(self) -> None:
        """Readiness probe: the shared store answers (raises RateLimitUnavailable otherwise)."""
        try:
            if not self._redis.ping():
                raise RateLimitUnavailable("Rate-limit store is unavailable.")
        except RateLimitUnavailable:
            raise
        except Exception as exc:
            raise RateLimitUnavailable("Rate-limit store is unavailable.") from exc

    def reset(self) -> None:
        """Delete this limiter's keys (tests and operator use)."""
        try:
            keys = list(self._redis.scan_iter(match=self._prefix + "*", count=500))
            if keys:
                self._redis.delete(*keys)
        except Exception as exc:
            raise RateLimitUnavailable("Rate-limit store is unavailable.") from exc


def limiter_from_env() -> RateLimiter:
    """Build the limiter named by STN_RATE_LIMIT_BACKEND. Raises RateLimitConfigError if misconfigured."""
    backend = os.getenv(BACKEND_ENV, "memory").strip().lower() or "memory"
    if backend == "memory":
        return InMemoryRateLimiter()
    if backend == "redis":
        url = os.getenv(REDIS_URL_ENV, "").strip()
        if not url:
            raise RateLimitConfigError(f"{REDIS_URL_ENV} is required when {BACKEND_ENV}=redis.")
        return RedisRateLimiter(url, os.getenv(REDIS_PREFIX_ENV, "stn:rl:").strip() or "stn:rl:")
    raise RateLimitConfigError(f"Unknown {BACKEND_ENV} {backend!r}; use 'memory' or 'redis'.")


_limiter: RateLimiter | None = None
_limiter_lock = threading.Lock()


def set_rate_limiter(limiter: RateLimiter | None) -> None:
    """Replace the process limiter (None rebuilds it from the environment on next use)."""
    global _limiter
    _limiter = limiter


def limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        with _limiter_lock:
            if _limiter is None:
                _limiter = limiter_from_env()
    return _limiter


def enabled() -> bool:
    return os.getenv("STN_RATE_LIMIT_ENABLED", "true").strip().lower() not in {"false", "0", "no", "off"}


def limit(name: str) -> int:
    try:
        value = int(os.getenv(name, "").strip() or DEFAULTS[name])
    except ValueError:
        value = DEFAULTS[name]
    return max(1, value)


def client_ip(request: Request) -> str:
    if os.getenv("STN_TRUST_FORWARDED_FOR", "false").strip().lower() in {"true", "1", "yes", "on"}:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def unavailable() -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Rate limiting is unavailable; retry later.")


def too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Too many requests; slow down and retry later.",
        headers={"Retry-After": str(retry_after)},
    )


def check_ip(request: Request) -> tuple[bool, int]:
    """Used by the /v1 middleware. Raises RateLimitUnavailable if the store cannot be reached."""
    if not enabled():
        return True, 0
    return limiter().hit(f"ip:{client_ip(request)}", limit("STN_RATE_LIMIT_IP_PER_MINUTE"), WINDOW_SECONDS)


def check_write(request: Request, org: str, subject: str) -> None:
    if not enabled() or request.method not in WRITE_METHODS:
        return
    try:
        allowed, retry = limiter().hit(
            f"writes:{org}:{subject}", limit("STN_RATE_LIMIT_WRITES_PER_MINUTE"), WINDOW_SECONDS
        )
    except RateLimitUnavailable as exc:
        raise unavailable() from exc
    if not allowed:
        raise too_many(retry)


def auth_blocked(request: Request) -> None:
    if not enabled():
        return
    try:
        over, retry = limiter().exceeded(
            f"authfail:{client_ip(request)}", limit("STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE"), WINDOW_SECONDS
        )
    except RateLimitUnavailable as exc:
        raise unavailable() from exc
    if over:
        raise too_many(retry)


def record_auth_failure(request: Request) -> None:
    if enabled():
        try:
            limiter().hit(
                f"authfail:{client_ip(request)}", limit("STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE"), WINDOW_SECONDS
            )
        except RateLimitUnavailable as exc:
            raise unavailable() from exc
