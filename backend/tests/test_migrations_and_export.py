"""Migration framework and immutable audit export tests. Synthetic data only."""
from __future__ import annotations

import base64
import secrets
import sqlite3

import pytest

from app import audit, audit_export, migrate, store


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv(store.DB_ENV, str(tmp_path / "m.sqlite3"))
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    return tmp_path


def test_migrations_are_discovered_in_order():
    versions = [v for v, _, _ in migrate.discover()]
    assert versions == sorted(versions) == ["0001", "0002", "0003", "0004", "0005"]


def test_apply_is_idempotent(env):
    with store._connect() as conn:
        assert migrate.apply(conn) == []  # already applied on connect
        count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert count == 5


def test_legacy_audit_log_is_dropped_and_chain_is_the_only_trail(env):
    with store._connect() as conn:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "audit_log" not in names
    assert "audit_chain" in names


def test_edited_applied_migration_is_refused(env, monkeypatch):
    with store._connect() as conn:
        pass
    real = migrate.discover()
    tampered = [(v, n, sql + "\n-- edited") if v == "0001" else (v, n, sql) for v, n, sql in real]
    monkeypatch.setattr(migrate, "discover", lambda: tampered)
    with sqlite3.connect(str(env / "m.sqlite3")) as conn:
        conn.row_factory = sqlite3.Row
        with pytest.raises(migrate.MigrationError, match="modified after it was applied"):
            migrate.apply(conn)


def test_failed_migration_rolls_back(env, monkeypatch):
    bad = [("0001", "broken", "CREATE TABLE t1 (a TEXT);\nTHIS IS NOT SQL;")]
    monkeypatch.setattr(migrate, "discover", lambda: bad)
    conn = sqlite3.connect(str(env / "fresh.sqlite3"), isolation_level=None)
    conn.row_factory = sqlite3.Row
    with pytest.raises(sqlite3.OperationalError):
        migrate.apply(conn)
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='t1'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 0


def test_invalid_migration_filename_is_refused(tmp_path, monkeypatch):
    (tmp_path / "bad.sql").write_text("SELECT 1;", encoding="utf-8")
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)
    with pytest.raises(migrate.MigrationError, match="Invalid migration file name"):
        migrate.discover()


def test_export_segment_verifies_independently(env, tmp_path):
    audit.append("a", "onboarding.create", "case:1", {"stage": "registered"})
    audit.append("a", "onboarding.create", "case:1", {"stage": "contact_verified"})
    out = tmp_path / "exports"
    manifest = audit_export.export_segment(out)
    assert manifest["row_count"] == 2
    assert audit_export.verify_segment(out, f"{manifest['segment'].removesuffix('.jsonl')}.manifest.json")


def test_tampered_export_fails_verification(env, tmp_path):
    audit.append("a", "onboarding.suspend", "case:1", {})
    audit.append("a", "onboarding.suspend", "case:1", {})
    out = tmp_path / "exports"
    manifest = audit_export.export_segment(out)
    manifest_name = f"{manifest['segment'].removesuffix('.jsonl')}.manifest.json"
    segment = out / manifest["segment"]
    segment.write_text(segment.read_text(encoding="utf-8").replace('"actor":"a"', '"actor":"b"', 1), encoding="utf-8")
    assert audit_export.verify_segment(out, manifest_name) is False
