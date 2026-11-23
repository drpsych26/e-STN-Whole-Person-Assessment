"""Request rate limiting behind a small interface.

Three limits (per rolling 60-second window), each configurable:
- STN_RATE_LIMIT_IP_PER_MINUTE (default 600): every /v1 request, per client IP.
- STN_RATE_LIMIT_WRITES_PER_MINUTE (default 120): POST/PUT/PATCH/DELETE per
  authenticated subject (scoped by organisation).
- STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE (default 20): rejected bearer tokens per
  client IP. Once reached, that IP gets 429 until the window passes.
STN_RATE_LIMIT_ENABLED=false turns limiting off (local debugging only).

The default InMemoryRateLimiter keeps state in one process. Production runs more
than one instance, so it needs a shared store (for example Azure Cache for Redis)
behind the same interface, or limits enforced at the gateway (Azure Front Door /
API Management). The client IP is the socket peer unless STN_TRUST_FORWARDED_FOR is
true, in which case the first X-Forwarded-For address is used; enable that only
behind a proxy that overwrites the header.
"""
from __future__ import annotations

import math
import os
import threading
import time
from collections import deque
from typing import Protocol

from fastapi import HTTPException, Request, status

WINDOW_SECONDS = 60
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
DEFAULTS = {
    "STN_RATE_LIMIT_IP_PER_MINUTE": 600,
    "STN_RATE_LIMIT_WRITES_PER_MINUTE": 120,
    "STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE": 20,
}


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


_limiter: RateLimiter = InMemoryRateLimiter()


def set_rate_limiter(limiter: RateLimiter) -> None:
    global _limiter
    _limiter = limiter


def limiter() -> RateLimiter:
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


def too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Too many requests; slow down and retry later.",
        headers={"Retry-After": str(retry_after)},
    )


def check_ip(request: Request) -> tuple[bool, int]:
    if not enabled():
        return True, 0
    return _limiter.hit(f"ip:{client_ip(request)}", limit("STN_RATE_LIMIT_IP_PER_MINUTE"), WINDOW_SECONDS)


def check_write(request: Request, org: str, subject: str) -> None:
    if not enabled() or request.method not in WRITE_METHODS:
        return
    allowed, retry = _limiter.hit(
        f"writes:{org}:{subject}", limit("STN_RATE_LIMIT_WRITES_PER_MINUTE"), WINDOW_SECONDS
    )
    if not allowed:
        raise too_many(retry)


def auth_blocked(request: Request) -> None:
    if not enabled():
        return
    over, retry = _limiter.exceeded(
        f"authfail:{client_ip(request)}", limit("STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE"), WINDOW_SECONDS
    )
    if over:
        raise too_many(retry)


def record_auth_failure(request: Request) -> None:
    if enabled():
        _limiter.hit(
            f"authfail:{client_ip(request)}", limit("STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE"), WINDOW_SECONDS
        )
