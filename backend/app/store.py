"""Encrypted client-record store. Every access is recorded in the hash-chained audit trail.

Only ciphertext and non-clinical metadata (ids, owner subject, timestamps) are stored.
Audit detail carries identifiers and outcomes only, never payload content. The database
path comes from STN_DATA_DB and must sit on encrypted storage in any deployed environment.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from . import audit, migrate
from .crypto import decrypt_payload, encrypt_payload

DB_ENV = "STN_DATA_DB"


class StoreNotConfigured(RuntimeError):
    """Raised when STN_DATA_DB is not set."""


class RecordNotFound(LookupError):
    """Raised for missing records and for records the actor does not own (indistinguishable)."""


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
    migrate.apply(conn)
    try:
        yield conn
    finally:
        conn.close()


def _tx(fn):
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            result = fn(conn)
            conn.execute("COMMIT")
            return result
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise


def _tx_recording_denials(fn):
    """Like _tx, but a denial is audited and committed before RecordNotFound is raised."""
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            outcome = fn(conn)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    if isinstance(outcome, RecordNotFound):
        raise outcome
    return outcome


def _aad(record_id: str, owner_sub: str) -> bytes:
    return f"{record_id}\x1f{owner_sub}".encode("utf-8")


def _audit(conn: sqlite3.Connection, actor: str, action: str, record_id: str, outcome: str) -> None:
    audit.append_in_tx(conn, actor, f"client.{action}", f"record:{record_id}", {"outcome": outcome})


def create_record(actor: str, payload: dict[str, Any]) -> str:
    record_id = str(uuid.uuid4())
    blob = encrypt_payload(payload, _aad(record_id, actor))
    stamp = _now()

    def _do(conn):
        conn.execute(
            "INSERT INTO client_records (id, owner_sub, created_at, updated_at, ciphertext) VALUES (?, ?, ?, ?, ?)",
            (record_id, actor, stamp, stamp, blob),
        )
        _audit(conn, actor, "create", record_id, "ok")
        return record_id

    return _tx(_do)


def read_record(actor: str, record_id: str) -> dict[str, Any]:
    def _do(conn):
        row = conn.execute(
            "SELECT owner_sub, ciphertext FROM client_records WHERE id = ?", (record_id,)
        ).fetchone()
        if row is None or row["owner_sub"] != actor:
            _audit(conn, actor, "read", record_id, "denied_or_missing")
            return RecordNotFound(record_id)
        try:
            payload = decrypt_payload(row["ciphertext"], _aad(record_id, row["owner_sub"]))
        except Exception:
            _audit(conn, actor, "read", record_id, "integrity_failure")
            conn.execute("COMMIT")
            raise
        _audit(conn, actor, "read", record_id, "ok")
        return payload

    return _tx_recording_denials(_do)


def update_record(actor: str, record_id: str, payload: dict[str, Any]) -> None:
    blob = encrypt_payload(payload, _aad(record_id, actor))

    def _do(conn):
        cur = conn.execute(
            "UPDATE client_records SET ciphertext = ?, updated_at = ? WHERE id = ? AND owner_sub = ?",
            (blob, _now(), record_id, actor),
        )
        if cur.rowcount == 0:
            _audit(conn, actor, "update", record_id, "denied_or_missing")
            return RecordNotFound(record_id)
        _audit(conn, actor, "update", record_id, "ok")
        return None

    _tx_recording_denials(_do)


def audit_entries(record_id: str | None = None) -> list[dict[str, Any]]:
    """Client-record audit entries from the hash-chained trail, in order."""
    with _connect() as conn:
        if record_id is None:
            rows = conn.execute(
                "SELECT * FROM audit_chain WHERE subject_ref LIKE 'record:%' ORDER BY seq"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_chain WHERE subject_ref = ? ORDER BY seq", (f"record:{record_id}",)
            ).fetchall()
    import json

    entries = []
    for r in rows:
        detail = json.loads(r["detail"])
        entries.append({
            "seq": r["seq"],
            "ts": r["ts"],
            "actor_sub": r["actor"],
            "action": r["action"],
            "record_id": r["subject_ref"].split(":", 1)[1],
            "outcome": detail.get("outcome", ""),
        })
    return entries
