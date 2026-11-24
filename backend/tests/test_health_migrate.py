"""Liveness/readiness probes, the separate migration step, runtime-role grants and managed-identity
database authentication. Synthetic configuration only."""
from __future__ import annotations

import os
import types
import uuid

import pytest
from fastapi.testclient import TestClient

from app import crypto, db, health, migrate, migrate_server, ratelimit
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
migrate_client = TestClient(migrate_server.app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _fresh_probes(monkeypatch):
    monkeypatch.setenv(health.CACHE_ENV, "0")
    monkeypatch.delenv(db.AUTH_ENV, raising=False)
    monkeypatch.delenv(db.AUTO_MIGRATE_ENV, raising=False)
    health.api_readiness.reset()
    health.migration_readiness.reset()
    db.set_token_credential(None)
    yield
    health.api_readiness.reset()
    health.migration_readiness.reset()
    db.set_token_credential(None)
    ratelimit.set_rate_limiter(None)


# ---------------------------------------------------------------- liveness


def test_healthz_reports_alive_and_build_only(monkeypatch):
    monkeypatch.setenv(health.BUILD_ENV, "abc123.4-x")
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "alive", "build": "abc123.4-x"}


def test_build_id_is_restricted_to_a_safe_token(monkeypatch):
    monkeypatch.setenv(health.BUILD_ENV, "<script>alert(1)</script>")
    assert client.get("/healthz").json()["build"] == "unknown"
    monkeypatch.delenv(health.BUILD_ENV)
    assert client.get("/healthz").json()["build"] == "unknown"


def test_healthz_needs_no_dependencies(monkeypatch):
    monkeypatch.delenv(db.URL_ENV, raising=False)
    monkeypatch.delenv(db.DB_ENV, raising=False)
    assert client.get("/healthz").status_code == 200


def test_legacy_liveness_path_still_answers():
    assert client.get("/health/live").json() == {"status": "alive"}


# ---------------------------------------------------------------- readiness


def test_readyz_ready_when_database_keys_and_limiter_are_usable(backend):
    res = client.get("/readyz")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
    assert set(res.json()) == {"status", "build"}  # no dependency or configuration detail


def test_readyz_not_ready_without_a_database(monkeypatch):
    monkeypatch.delenv(db.URL_ENV, raising=False)
    monkeypatch.delenv(db.DB_ENV, raising=False)
    res = client.get("/readyz")
    assert res.status_code == 503
    assert set(res.json()) == {"status", "build"}
    assert res.json()["status"] == "not_ready"


def test_readyz_not_ready_without_data_keys(backend, monkeypatch):
    monkeypatch.delenv("STN_DATA_KEY", raising=False)
    monkeypatch.delenv("STN_DATA_KEYS", raising=False)
    assert client.get("/readyz").status_code == 503


def test_readyz_not_ready_when_shared_rate_limit_store_is_down(backend):
    class DownLimiter(ratelimit.InMemoryRateLimiter):
        def ping(self) -> None:
            raise ratelimit.RateLimitUnavailable("down")

    ratelimit.set_rate_limiter(DownLimiter())
    assert client.get("/readyz").status_code == 503


def test_failed_check_is_logged_by_name_without_detail(backend, monkeypatch, caplog):
    monkeypatch.delenv("STN_DATA_KEY", raising=False)
    with caplog.at_level("WARNING", logger="stn.health"):
        client.get("/readyz")
    assert "readiness check failed: keys" in caplog.text


def test_without_auto_migrate_api_is_not_ready_until_the_migration_step_runs(backend, monkeypatch):
    monkeypatch.setenv(db.AUTO_MIGRATE_ENV, "false")
    assert db.schema_version() is None
    assert client.get("/readyz").status_code == 503
    assert migrate.main([]) == 0
    assert db.schema_version() == db.head_version()
    assert client.get("/readyz").status_code == 200


def test_readiness_result_is_cached_for_the_configured_time(backend, monkeypatch):
    calls = []
    probe = health.Readiness({"counted": lambda: calls.append(1)})
    monkeypatch.setenv(health.CACHE_ENV, "60")
    assert probe.ready() and probe.ready() and probe.ready()
    assert len(calls) == 1
    monkeypatch.setenv(health.CACHE_ENV, "0")
    probe.reset()
    probe.ready()
    probe.ready()
    assert len(calls) == 3


# ---------------------------------------------------------------- migration role


def test_migration_server_exposes_only_health(backend, monkeypatch):
    monkeypatch.setenv(db.AUTO_MIGRATE_ENV, "false")
    assert migrate_client.get("/readyz").status_code == 503
    assert migrate.main([]) == 0
    assert migrate_client.get("/readyz").status_code == 200
    assert migrate_client.get("/healthz").status_code == 200
    for path in ("/v1/me", "/docs", "/openapi.json", "/v1/audit"):
        assert migrate_client.get(path).status_code == 404


def test_migration_server_does_not_need_data_keys(backend, monkeypatch):
    monkeypatch.delenv("STN_DATA_KEY", raising=False)
    assert migrate.main([]) == 0
    assert migrate_client.get("/readyz").status_code == 200


def test_migrate_cli_is_idempotent_and_reports_status(backend, capsys):
    assert migrate.main([]) == 0
    assert migrate.main([]) == 0
    assert migrate.main(["--status"]) == 0
    out = capsys.readouterr().out
    assert f"schema version {db.head_version()}" in out
    assert "postgresql://" not in out


def test_migrate_cli_without_a_database_is_a_configuration_error(monkeypatch, capsys):
    monkeypatch.delenv(db.URL_ENV, raising=False)
    monkeypatch.delenv(db.DB_ENV, raising=False)
    assert migrate.main([]) == 2


def test_bootstrap_admin_is_registered_and_activated_once(backend, capsys):
    from app import accounts

    args = ["--bootstrap-admin-org", "org-synthetic", "--bootstrap-admin-subject", "subject-admin-1"]
    assert migrate.main(args) == 0
    assert "registered and activated" in capsys.readouterr().out
    rows = accounts.list_accounts(accounts.CLI_ACTOR, "org-synthetic")
    assert [(r["subject"], r["status"]) for r in rows] == [("subject-admin-1", "active")]
    history = accounts.account_history(accounts.CLI_ACTOR, "org-synthetic", "subject-admin-1")
    assert sorted(h["to_status"] for h in history) == ["active", "invited"]
    assert {h["reason_code"] for h in history} == {migrate.BOOTSTRAP_REASON}

    assert migrate.main(args) == 0
    assert "left unchanged" in capsys.readouterr().out
    assert len(accounts.account_history(accounts.CLI_ACTOR, "org-synthetic", "subject-admin-1")) == 2


def test_bootstrap_never_reactivates_a_suspended_account(backend, monkeypatch):
    from app import accounts

    monkeypatch.setenv(migrate.BOOTSTRAP_ORG_ENV, "org-synthetic")
    monkeypatch.setenv(migrate.BOOTSTRAP_SUBJECT_ENV, "subject-admin-2")
    assert migrate.main([]) == 0
    accounts.change_status("subject-admin-other", "org-synthetic", "subject-admin-2", "suspend", "synthetic_test")
    assert migrate.main([]) == 0
    row = accounts.list_accounts(accounts.CLI_ACTOR, "org-synthetic")[0]
    assert row["status"] == "suspended"


@pytest.mark.parametrize("args", [
    ["--bootstrap-admin-org", "org-synthetic"],
    ["--bootstrap-admin-subject", "subject-admin-3"],
    ["--bootstrap-admin-org", "bad org!", "--bootstrap-admin-subject", "subject-admin-3"],
    ["--bootstrap-admin-org", "org-synthetic", "--bootstrap-admin-subject", "bad subject"],
])
def test_bootstrap_admin_configuration_errors(backend, args):
    from app import accounts

    assert migrate.main(args) == 2
    assert accounts.list_accounts(accounts.CLI_ACTOR, "org-synthetic") == []


def test_runtime_role_grants_are_postgres_only(backend):
    if backend != "sqlite":
        pytest.skip("SQLite case")
    assert migrate.main(["--grant-runtime-role", "stn_runtime"]) == 2


def test_runtime_role_name_is_validated(backend):
    if backend != "postgres":
        pytest.skip("PostgreSQL case")
    assert migrate.main(["--grant-runtime-role", 'bad"; DROP ROLE x; --']) == 2


def test_runtime_role_gets_data_privileges_but_cannot_change_the_schema(backend):
    if backend != "postgres":
        pytest.skip("PostgreSQL case")
    import psycopg

    role = "stn_rt_" + uuid.uuid4().hex[:8]
    url = os.environ[db.URL_ENV]
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(f'CREATE ROLE "{role}" NOLOGIN')
    try:
        assert migrate.main(["--grant-runtime-role", role]) == 0
        with psycopg.connect(url, autocommit=True) as conn:
            q = lambda sql, *a: conn.execute(sql, a).fetchone()[0]  # noqa: E731
            for table in ("schema_migrations", "audit_events"):
                assert q("SELECT has_table_privilege(%s, %s, 'SELECT')", role, table)
                assert q("SELECT has_table_privilege(%s, %s, 'INSERT')", role, table)
            assert not q("SELECT has_schema_privilege(%s, 'public', 'CREATE')", role)
            assert not q("SELECT has_database_privilege(%s, current_database(), 'CREATE')", role)
            assert q("SELECT has_table_privilege(%s, 'schema_migrations', 'TRUNCATE')", role) is False
        # A missing role is a configuration error, not a silent success.
        assert migrate.main(["--grant-runtime-role", role + "_missing"]) == 2
    finally:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute(f'DROP OWNED BY "{role}"')
            conn.execute(f'DROP ROLE "{role}"')


class _FakeConn:
    def __init__(self, log: list, existing: bool) -> None:
        self._log, self._existing = log, existing

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self._log.append((str(sql), tuple(params)))
        row = (1,) if (self._existing and "pg_roles" in str(sql)) else None
        return types.SimpleNamespace(fetchone=lambda: row)


@pytest.mark.parametrize("existing", [False, True])
def test_entra_principal_is_created_once_in_the_postgres_database(monkeypatch, existing):
    pytest.importorskip("psycopg")
    calls: list = []
    urls: list = []

    def fake_connect(url, psycopg, **kwargs):
        urls.append(url)
        return _FakeConn(calls, existing)

    monkeypatch.setattr(db, "pg_connect", fake_connect)
    created = migrate.create_entra_principal("postgresql://id-stn-api@pg.example/stn?sslmode=require", object(), "id-stn-api")
    assert created is (not existing)
    assert "dbname=postgres" in urls[0]
    principal_calls = [c for c in calls if "pgaadauth_create_principal" in c[0]]
    assert principal_calls == ([] if existing else [("SELECT * FROM pgaadauth_create_principal(%s, false, false)", ("id-stn-api",))])


# ---------------------------------------------------------------- managed-identity database auth


class _Token:
    def __init__(self, token: str) -> None:
        self.token = token


def test_managed_identity_token_is_used_as_the_database_password(monkeypatch):
    monkeypatch.setenv(db.AUTH_ENV, "azure-managed-identity")
    scopes = []

    class Credential:
        def get_token(self, scope):
            scopes.append(scope)
            return _Token("synthetic-access-token")

    db.set_token_credential(Credential())
    seen = {}
    fake_psycopg = types.SimpleNamespace(connect=lambda url, **kw: seen.update(url=url, **kw) or "conn")
    assert db.pg_connect("postgresql://id-stn-api@pg.example/stn", fake_psycopg, autocommit=True) == "conn"
    assert seen["password"] == "synthetic-access-token"
    assert seen["autocommit"] is True
    assert scopes == [db.ENTRA_SCOPE]


def test_password_mode_passes_no_token(monkeypatch):
    seen = {}
    fake_psycopg = types.SimpleNamespace(connect=lambda url, **kw: seen.update(kw) or "conn")
    db.pg_connect("postgresql://u@h/d", fake_psycopg)
    assert "password" not in seen


def test_token_failure_fails_closed(monkeypatch):
    monkeypatch.setenv(db.AUTH_ENV, "azure-managed-identity")

    class Broken:
        def get_token(self, scope):
            raise RuntimeError("identity endpoint unreachable at 169.254.169.254")

    db.set_token_credential(Broken())
    with pytest.raises(db.StoreNotConfigured) as err:
        db.pg_connect("postgresql://u@h/d", types.SimpleNamespace(connect=lambda *a, **k: None))
    assert "169.254" not in str(err.value)


def test_missing_identity_library_fails_closed(monkeypatch):
    import sys

    monkeypatch.setenv(db.AUTH_ENV, "azure-managed-identity")
    monkeypatch.setitem(sys.modules, "azure.identity", None)
    with pytest.raises(db.StoreNotConfigured):
        db.pg_connect("postgresql://u@h/d", types.SimpleNamespace(connect=lambda *a, **k: None))


def test_unknown_auth_mode_fails_closed(monkeypatch):
    monkeypatch.setenv(db.AUTH_ENV, "kerberos")
    with pytest.raises(db.StoreNotConfigured):
        db.pg_connect("postgresql://u@h/d", types.SimpleNamespace(connect=lambda *a, **k: None))


def test_api_with_unknown_auth_mode_is_not_ready(backend, monkeypatch):
    if backend != "postgres":
        pytest.skip("authentication modes apply to PostgreSQL")
    monkeypatch.setenv(db.AUTH_ENV, "kerberos")
    assert client.get("/readyz").status_code == 503
