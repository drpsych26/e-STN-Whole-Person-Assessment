"""Sliding-window rate limits for write and sensitive-read routes.

Limits are keyed by the authenticated subject, or by client address for unauthenticated
ingestion. State is held in process memory: each API process enforces its own limit, so a
multi-instance deployment needs a shared store (for example Redis or the managed database)
before the limit is effective across instances. This is recorded as an open item (D-010).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from .auth import require_identity


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, bucket: str, key: str, max_requests: int, window_seconds: float) -> bool:
        """Record a request. Returns False (and does not record it) when the limit is reached."""
        now = self._clock()
        with self._lock:
            events = self._events[(bucket, key)]
            while events and now - events[0] >= window_seconds:
                events.popleft()
            if len(events) >= max_requests:
                return False
            events.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


LIMITER = RateLimiter()


def limit_by_subject(bucket: str, max_requests: int, window_seconds: float = 60.0):
    """Dependency: authenticate, then enforce the per-subject limit for this bucket."""

    def _dependency(identity: dict = Depends(require_identity)) -> dict:
        if not LIMITER.hit(bucket, f"sub:{identity['sub']}", max_requests, window_seconds):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Try again shortly.",
                                headers={"Retry-After": str(int(window_seconds))})
        return identity

    return _dependency


def limit_by_address(bucket: str, max_requests: int, window_seconds: float = 60.0):
    """Dependency for unauthenticated ingestion: enforce the limit per client address."""

    def _dependency(request: Request) -> None:
        host = request.client.host if request.client else "unknown"
        if not LIMITER.hit(bucket, f"addr:{host}", max_requests, window_seconds):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Try again shortly.",
                                headers={"Retry-After": str(int(window_seconds))})

    return _dependency
