"""Liveness and readiness probes for the platform (App Service health check, deploy smoke tests).

GET /healthz   liveness: the process answers. No dependency is touched.
GET /readyz    readiness: every dependency this process needs is usable. 200 or 503.

Both are unauthenticated, so they disclose nothing but a status and the build id (the image's
STN_BUILD_ID, restricted to a short safe token). Which check failed is written to the server log
only. Readiness results are cached briefly (STN_READINESS_CACHE_SECONDS, default 5, 0 disables)
so the probe cannot be used to hammer the database.

Checks for the API role:
- database: reachable with the configured authentication, and the schema is at this build's
  migration version (so an API started with STN_DATABASE_AUTO_MIGRATE=false is not ready until
  the separate migration step has run);
- keys: the data keyring loads and has an active key;
- rate_limit: when rate limiting is on, the store answers (Redis ping; in-process always does).
The migration role checks the database only.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from . import crypto, db, ratelimit

log = logging.getLogger("stn.health")

BUILD_ENV = "STN_BUILD_ID"
CACHE_ENV = "STN_READINESS_CACHE_SECONDS"
_SAFE_BUILD = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def build_id() -> str:
    value = os.getenv(BUILD_ENV, "").strip()
    return value if _SAFE_BUILD.fullmatch(value) else "unknown"


def check_database() -> None:
    version = db.schema_version()
    expected = db.head_version()
    if db.auto_migrate() and (version is None or version < expected):
        # Applying migrations is part of normal request handling in this mode.
        version = db.migrate()
    if version is None or version != expected:
        raise RuntimeError(f"schema version {version} does not match this build ({expected})")


def check_keys() -> None:
    crypto.keyring().active_key()


def check_rate_limit() -> None:
    if not ratelimit.enabled():
        return
    probe = getattr(ratelimit.limiter(), "ping", None)
    if probe is not None:
        probe()


API_CHECKS: dict[str, Callable[[], None]] = {
    "database": check_database,
    "keys": check_keys,
    "rate_limit": check_rate_limit,
}
MIGRATION_CHECKS: dict[str, Callable[[], None]] = {"database": check_database}


class Readiness:
    def __init__(self, checks: dict[str, Callable[[], None]]) -> None:
        self._checks = checks
        self._cached: tuple[float, bool] | None = None
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._cached = None

    def _ttl(self) -> float:
        try:
            return max(0.0, float(os.getenv(CACHE_ENV, "5")))
        except ValueError:
            return 5.0

    def ready(self) -> bool:
        ttl = self._ttl()
        with self._lock:
            if ttl and self._cached and self._cached[0] > time.monotonic():
                return self._cached[1]
            ok = True
            for name, check in self._checks.items():
                try:
                    check()
                except Exception as exc:  # noqa: BLE001 - every failure means not ready
                    ok = False
                    log.warning("readiness check failed: %s (%s)", name, type(exc).__name__)
            self._cached = (time.monotonic() + ttl, ok)
            return ok


def make_router(readiness: Readiness) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "alive", "build": build_id()}

    @router.get("/readyz")
    def readyz() -> JSONResponse:
        if readiness.ready():
            return JSONResponse({"status": "ready", "build": build_id()})
        return JSONResponse({"status": "not_ready", "build": build_id()}, status_code=503)

    return router


api_readiness = Readiness(API_CHECKS)
migration_readiness = Readiness(MIGRATION_CHECKS)
