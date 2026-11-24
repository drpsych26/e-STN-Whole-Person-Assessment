"""Database access layer: one interface over SQLite (tests, local) and PostgreSQL.

Selection (fail closed):
- STN_DATABASE_URL (postgresql://...) selects PostgreSQL. It takes precedence.
- Otherwise STN_DATA_DB (a file path) selects SQLite.
- With neither, StoreNotConfigured is raised and routes return 503.

SQL in this package is written with "?" placeholders; they are translated to
"%s" for psycopg. Every unit of work runs in one transaction so a write and its
audit event commit or roll back together. Schema changes are applied from the
versioned files in app/migrations/<dialect>/ and recorded in schema_migrations.

Deployment settings (all fail closed):
- STN_DATABASE_AUTH: "password" (default; credentials, if any, are in the URL) or
  "azure-managed-identity" (PostgreSQL only: a Microsoft Entra access token for the
  managed identity named by AZURE_CLIENT_ID is used as the password; no database
  password exists anywhere).
- STN_DATABASE_AUTO_MIGRATE: default on. "false" stops request handling from applying
  migrations (production: a separate migration step does it, see app.migrate, and
  readiness reports not-ready until the schema is at this build's version).
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
AUTH_ENV = "STN_DATABASE_AUTH"
AUTO_MIGRATE_ENV = "STN_DATABASE_AUTO_MIGRATE"
ENTRA_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"
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


def head_version(kind: str | None = None) -> int:
    """Highest migration version shipped with this build for the dialect."""
    versions = [v for v, _ in _migration_files(kind or dialect())]
    return max(versions) if versions else 0


def auto_migrate() -> bool:
    return os.getenv(AUTO_MIGRATE_ENV, "true").strip().lower() not in {"false", "0", "no", "off"}


def auth_mode() -> str:
    mode = os.getenv(AUTH_ENV, "password").strip().lower() or "password"
    if mode not in {"password", "azure-managed-identity"}:
        raise StoreNotConfigured("Unknown database authentication mode.")
    return mode


_credential: Any = None
_credential_lock = threading.Lock()


def set_token_credential(credential: Any) -> None:
    """Test and composition hook: an object with get_token(scope) -> token.token (None rebuilds)."""
    global _credential
    with _credential_lock:
        _credential = credential


def _entra_token() -> str:
    """Access token for the managed identity (AZURE_CLIENT_ID selects a user-assigned one)."""
    global _credential
    with _credential_lock:
        if _credential is None:
            try:
                from azure.identity import ManagedIdentityCredential  # type: ignore[import-not-found]
            except ImportError as exc:
                raise StoreNotConfigured("Azure identity library is not installed.") from exc
            client_id = os.getenv("AZURE_CLIENT_ID", "").strip() or None
            _credential = ManagedIdentityCredential(client_id=client_id)
        credential = _credential
    try:
        token = credential.get_token(ENTRA_SCOPE).token
    except Exception as exc:  # noqa: BLE001 - never expose identity details
        raise StoreNotConfigured("A database access token could not be obtained.") from exc
    if not token:
        raise StoreNotConfigured("A database access token could not be obtained.")
    return token


def pg_connect(url: str, psycopg: Any, **kwargs: Any) -> Any:
    """Open a PostgreSQL connection using the configured authentication mode."""
    if auth_mode() == "azure-managed-identity":
        kwargs["password"] = _entra_token()
    return psycopg.connect(url, **kwargs)


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
        with pg_connect(url, psycopg, autocommit=True) as raw:
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
        if auto_migrate():
            _migrate_postgres(url, psycopg)
        raw = pg_connect(url, psycopg, row_factory=dict_row)
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
        if auto_migrate():
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


def _pg_driver() -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise StoreNotConfigured("PostgreSQL driver is not installed.") from exc
    return psycopg


def migrate() -> int:
    """Apply every pending migration now, whatever STN_DATABASE_AUTO_MIGRATE says. Returns the version."""
    kind = dialect()
    if kind == "postgres":
        url = os.environ[URL_ENV].strip()
        with _pg_lock:
            _pg_migrated.discard(url)
        _migrate_postgres(url, _pg_driver())
    else:
        raw = sqlite3.connect(os.environ[DB_ENV].strip(), timeout=10, isolation_level=None)
        try:
            _migrate_sqlite(raw)
        finally:
            raw.close()
    version = schema_version()
    return version if version is not None else 0


def schema_version() -> int | None:
    """Highest applied migration version, or None when the schema has never been migrated."""
    kind = dialect()
    if kind == "postgres":
        psycopg = _pg_driver()
        with pg_connect(os.environ[URL_ENV].strip(), psycopg, autocommit=True) as raw:
            exists = raw.execute("SELECT to_regclass('schema_migrations') IS NOT NULL").fetchone()[0]
            if not exists:
                return None
            row = raw.execute("SELECT max(version) FROM schema_migrations").fetchone()
            return row[0]
    raw = sqlite3.connect(os.environ[DB_ENV].strip(), timeout=10, isolation_level=None)
    try:
        exists = raw.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if not exists:
            return None
        return raw.execute("SELECT max(version) FROM schema_migrations").fetchone()[0]
    finally:
        raw.close()
