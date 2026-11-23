"""Shared fixtures. Synthetic data and throwaway keys only.

Workflow tests run on both SQLite and PostgreSQL. PostgreSQL runs when
STN_TEST_DATABASE_URL is set; CI also sets STN_REQUIRE_PG_TESTS=1 so a missing
database fails the run instead of skipping it.
"""
from __future__ import annotations

import base64
import os
import secrets
import sqlite3
from typing import Any, Callable

import pytest

from app import auth, crypto, db, ratelimit
from app.main import app

ORG = "org-synthetic-1"


@pytest.fixture(autouse=True)
def _isolated_limits_and_keys():
    """Fresh rate-limit windows and key-provider selection for every test."""
    ratelimit.limiter().reset()
    crypto.set_key_provider(None)
    yield
    ratelimit.limiter().reset()
    crypto.set_key_provider(None)


@pytest.fixture(params=["sqlite", "postgres"])
def backend(request, tmp_path, monkeypatch) -> str:
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    if request.param == "sqlite":
        monkeypatch.delenv(db.URL_ENV, raising=False)
        monkeypatch.setenv(db.DB_ENV, str(tmp_path / "stn.sqlite3"))
        return "sqlite"
    url = os.getenv("STN_TEST_DATABASE_URL", "").strip()
    if not url:
        if os.getenv("STN_REQUIRE_PG_TESTS") == "1":
            pytest.fail("STN_REQUIRE_PG_TESTS=1 but STN_TEST_DATABASE_URL is not set.")
        pytest.skip("PostgreSQL tests need STN_TEST_DATABASE_URL.")
    import psycopg

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        conn.execute("CREATE SCHEMA public")
    db.reset_migration_cache()
    monkeypatch.delenv(db.DB_ENV, raising=False)
    monkeypatch.setenv(db.URL_ENV, url)
    return "postgres"


@pytest.fixture
def raw(backend) -> Callable[..., list[tuple]]:
    """Execute SQL directly against the test database, bypassing the API (tamper tests)."""

    def run(sql: str, params: tuple = ()) -> list[tuple]:
        if backend == "sqlite":
            conn = sqlite3.connect(os.environ[db.DB_ENV])
            try:
                cur = conn.execute(sql, params)
                rows = cur.fetchall()
                conn.commit()
                return rows
            finally:
                conn.close()
        import psycopg

        with psycopg.connect(os.environ[db.URL_ENV], autocommit=True) as conn:
            cur = conn.execute(sql.replace("?", "%s"), params)
            return cur.fetchall() if cur.description else []

    return run


@pytest.fixture
def act(monkeypatch) -> Callable[..., None]:
    """Switch the verified identity seen by the API: act("sub", "clinician", mfa=True, org=ORG)."""
    current: dict[str, Any] = {"sub": "nobody", "roles": (), "mfa": True, "org": ORG}
    monkeypatch.setitem(app.dependency_overrides, auth.require_identity, lambda: dict(current))

    def switch(sub: str, *roles: str, mfa: bool = True, org: str | None = ORG) -> None:
        current.update(sub=sub, roles=tuple(roles), mfa=mfa, org=org)

    yield switch
    app.dependency_overrides.pop(auth.require_identity, None)
