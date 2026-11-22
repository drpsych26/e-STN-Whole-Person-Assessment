"""Database access layer: one interface over SQLite (tests, local) and PostgreSQL.

Selection (fail closed):
- STN_DATABASE_URL (postgresql://...) selects PostgreSQL. It takes precedence.
- Otherwise STN_DATA_DB (a file path) selects SQLite.
- With neither, StoreNotConfigured is raised and routes return 503.

SQL in this package is written with "?" placeholders; they are translated to
"%s" for psycopg. Every unit of work runs in one transaction so a write and its
audit event commit or roll back together. Schema changes are applied from the
versioned files in app/migrations/<dialect>/ and recorded in schema_migrations.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

DB_ENV = "STN_DATA_DB"
URL_ENV = "STN_DATABASE_URL"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"

_pg_migrated: set[str] = set()
_pg_lock = threading.Lock()


class StoreNotConfigured(RuntimeError):
    """Raised when no database is configured or the configured driver is unavailable."""


def dialect() -> str:
    if os.getenv(URL_ENV, "").strip():
        return "postgres"
    if os.getenv(DB_ENV, "").strip():
        return "sqlite"
    raise StoreNotConfigured("Record store is not configured.")


class Conn:
    """Thin wrapper giving both drivers the same execute/fetch API (rows as dicts)."""

    def __init__(self, raw: Any, kind: str) -> None:
        self.raw = raw
        self.kind = kind

    def execute(self, sql: str, params: Sequence[Any] = ()) -> "Result":
        if self.kind == "postgres":
            cur = self.raw.execute(sql.replace("?", "%s"), tuple(params))
        else:
            cur = self.raw.execute(sql, tuple(params))
        return Result(cur)


class Result:
    def __init__(self, cur: Any) -> None:
        self._cur = cur

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def fetchone(self) -> dict[str, Any] | None:
        row = self._cur.fetchone()
        return None if row is None else _as_dict(row)

    def fetchall(self) -> list[dict[str, Any]]:
        return [_as_dict(r) for r in self._cur.fetchall()]


def _as_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        out = dict(row)
    else:  # sqlite3.Row
        out = {k: row[k] for k in row.keys()}
    for key, value in out.items():
        if isinstance(value, memoryview):
            out[key] = value.tobytes()
    return out


def _migration_files(kind: str) -> list[tuple[int, str]]:
    files = sorted((MIGRATIONS_DIR / kind).glob("*.sql"))
    return [(int(f.name.split("_", 1)[0]), f.read_text(encoding="utf-8")) for f in files]


def _migrate_sqlite(raw: sqlite3.Connection) -> None:
    raw.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    applied = {r[0] for r in raw.execute("SELECT version FROM schema_migrations")}
    for version, sql in _migration_files("sqlite"):
        if version in applied:
            continue
        raw.executescript(sql)
        raw.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, datetime('now'))",
            (version,),
        )


def _migrate_postgres(url: str, psycopg: Any) -> None:
    with _pg_lock:
        if url in _pg_migrated:
            return
        with psycopg.connect(url, autocommit=True) as raw:
            with raw.transaction():
                raw.execute("SELECT pg_advisory_xact_lock(727270)")
                raw.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations "
                    "(version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
                )
                applied = {r[0] for r in raw.execute("SELECT version FROM schema_migrations").fetchall()}
                for version, sql in _migration_files("postgres"):
                    if version in applied:
                        continue
                    raw.execute(sql)
                    raw.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        _pg_migrated.add(url)


def reset_migration_cache() -> None:
    """Test helper: forget which PostgreSQL URLs have been migrated in this process."""
    with _pg_lock:
        _pg_migrated.clear()


@contextmanager
def transaction() -> Iterator[Conn]:
    """Open one connection and one write transaction; commit on success, roll back on error."""
    kind = dialect()
    if kind == "postgres":
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # driver missing: fail closed, never fall back to SQLite
            raise StoreNotConfigured("PostgreSQL driver is not installed.") from exc
        url = os.environ[URL_ENV].strip()
        _migrate_postgres(url, psycopg)
        raw = psycopg.connect(url, row_factory=dict_row)
        try:
            yield Conn(raw, "postgres")
            raw.commit()
        except BaseException:
            raw.rollback()
            raise
        finally:
            raw.close()
        return

    raw = sqlite3.connect(os.environ[DB_ENV].strip(), timeout=10, isolation_level=None)
    raw.row_factory = sqlite3.Row
    try:
        raw.execute("PRAGMA foreign_keys = ON")
        _migrate_sqlite(raw)
        raw.execute("BEGIN IMMEDIATE")
        try:
            yield Conn(raw, "sqlite")
            raw.execute("COMMIT")
        except BaseException:
            raw.execute("ROLLBACK")
            raise
    finally:
        raw.close()


def lock_audit_chain(conn: Conn) -> None:
    """Serialise audit appends. SQLite's BEGIN IMMEDIATE already holds the write lock."""
    if conn.kind == "postgres":
        conn.execute("SELECT pg_advisory_xact_lock(727271)")
