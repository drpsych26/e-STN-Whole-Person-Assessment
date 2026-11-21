"""Forward-only SQL migration runner.

Migrations live in app/migrations as NNNN_name.sql and are applied in order. Each applied
migration's SHA-256 is recorded. An edited, already-applied migration is refused, so history
cannot be silently rewritten. Each migration runs in one transaction.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class MigrationError(RuntimeError):
    pass


def discover() -> list[tuple[str, str, str]]:
    """Return (version, name, sql) for each migration file, in order."""
    found = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version, _, name = path.stem.partition("_")
        if not version.isdigit() or not name:
            raise MigrationError(f"Invalid migration file name: {path.name}")
        found.append((version, name, path.read_text(encoding="utf-8")))
    versions = [v for v, _, _ in found]
    if len(set(versions)) != len(versions):
        raise MigrationError("Duplicate migration version.")
    return found


def checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def apply(conn: sqlite3.Connection) -> list[str]:
    """Apply pending migrations. Returns the versions applied in this call."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version TEXT PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
    )
    applied = {r["version"]: r["checksum"] for r in conn.execute("SELECT version, checksum FROM schema_migrations")}
    newly: list[str] = []
    for version, name, sql in discover():
        digest = checksum(sql)
        if version in applied:
            if applied[version] != digest:
                raise MigrationError(f"Migration {version} was modified after it was applied.")
            continue
        try:
            conn.executescript(
                "BEGIN IMMEDIATE;\n" + sql + "\n"
                + "INSERT INTO schema_migrations (version, name, checksum, applied_at) VALUES ("
                + f"'{version}', '{name}', '{digest}', '{datetime.now(timezone.utc).isoformat()}');\n"
                + "COMMIT;"
            )
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        newly.append(version)
    return newly
