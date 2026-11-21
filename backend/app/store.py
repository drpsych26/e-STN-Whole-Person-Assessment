"""SQLite-backed encrypted client record store with an append-only audit log.

Only ciphertext and non-clinical metadata (ids, owner subject, timestamps) are
stored. Audit rows record who touched which record id and the outcome; they never
contain payload content. The database path must be supplied in STN_DATA_DB and
should point at encrypted storage (full-disk or managed-database encryption).
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from . import schemas
from .crypto import decrypt_payload, encrypt_payload

DB_ENV = "STN_DATA_DB"

SCHEMA = """
CREATE TABLE IF NOT EXISTS client_records (
    id         TEXT PRIMARY KEY,
    owner_sub  TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    ciphertext BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    actor_sub TEXT NOT NULL,
    action    TEXT NOT NULL,
    record_id TEXT,
    outcome   TEXT NOT NULL
);
"""


class StoreNotConfigured(RuntimeError):
    """Raised when STN_DATA_DB is not set."""


class RecordNotFound(LookupError):
    """Raised for missing records and for records the actor does not own.

    Both cases return the same error so record ids cannot be enumerated.
    """


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> str:
    path = os.getenv(DB_ENV, "").strip()
    if not path:
        raise StoreNotConfigured("Client record store is not configured.")
    return path


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path(), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    schemas.apply(conn)
    try:
        yield conn
    finally:
        conn.close()


def _aad(record_id: str, owner_sub: str) -> bytes:
    return f"{record_id}\x1f{owner_sub}".encode("utf-8")


def _audit(conn: sqlite3.Connection, actor: str, action: str, record_id: str | None, outcome: str) -> None:
    conn.execute(
        "INSERT INTO audit_log (ts, actor_sub, action, record_id, outcome) VALUES (?, ?, ?, ?, ?)",
        (_now(), actor, action, record_id, outcome),
    )


def create_record(actor: str, payload: dict[str, Any]) -> str:
    record_id = str(uuid.uuid4())
    blob = encrypt_payload(payload, _aad(record_id, actor))
    stamp = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO client_records (id, owner_sub, created_at, updated_at, ciphertext) VALUES (?, ?, ?, ?, ?)",
            (record_id, actor, stamp, stamp, blob),
        )
        _audit(conn, actor, "create", record_id, "ok")
    return record_id


def read_record(actor: str, record_id: str) -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT owner_sub, ciphertext FROM client_records WHERE id = ?", (record_id,)
        ).fetchone()
        if row is None or row["owner_sub"] != actor:
            _audit(conn, actor, "read", record_id, "denied_or_missing")
            raise RecordNotFound(record_id)
        try:
            payload = decrypt_payload(row["ciphertext"], _aad(record_id, row["owner_sub"]))
        except Exception:
            _audit(conn, actor, "read", record_id, "integrity_failure")
            raise
        _audit(conn, actor, "read", record_id, "ok")
        return payload


def update_record(actor: str, record_id: str, payload: dict[str, Any]) -> None:
    blob = encrypt_payload(payload, _aad(record_id, actor))
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE client_records SET ciphertext = ?, updated_at = ? WHERE id = ? AND owner_sub = ?",
            (blob, _now(), record_id, actor),
        )
        if cur.rowcount == 0:
            _audit(conn, actor, "update", record_id, "denied_or_missing")
            raise RecordNotFound(record_id)
        _audit(conn, actor, "update", record_id, "ok")


def audit_entries(record_id: str | None = None) -> list[dict[str, Any]]:
    with _connect() as conn:
        if record_id is None:
            rows = conn.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE record_id = ? ORDER BY id", (record_id,)
            ).fetchall()
        return [dict(r) for r in rows]
