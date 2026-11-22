"""Encrypted client record store with hash-chained audit events.

Only ciphertext and non-clinical metadata (ids, owner subject, timestamps) are
stored. Audit events record who touched which record id and the outcome; they
never contain payload content. The database is selected in app.db: PostgreSQL via
STN_DATABASE_URL, or SQLite via STN_DATA_DB (tests and local synthetic runs).
"""
from __future__ import annotations

import uuid
from typing import Any

from . import audit, db
from .crypto import decrypt_payload, encrypt_payload
from .db import DB_ENV, StoreNotConfigured  # re-exported for callers and tests

__all__ = ["DB_ENV", "StoreNotConfigured", "RecordNotFound", "create_record", "read_record",
           "update_record", "client_owner", "audit_entries"]


class RecordNotFound(LookupError):
    """Raised for missing records and for records the actor does not own.

    Both cases return the same error so record ids cannot be enumerated.
    """


def _aad(record_id: str, owner_sub: str) -> bytes:
    return f"{record_id}\x1f{owner_sub}".encode("utf-8")


def create_record(actor: str, payload: dict[str, Any]) -> str:
    db.dialect()  # fail closed before encrypting or touching storage
    record_id = str(uuid.uuid4())
    blob = encrypt_payload(payload, _aad(record_id, actor))
    stamp = audit.now()
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO client_records (id, owner_sub, created_at, updated_at, ciphertext) VALUES (?, ?, ?, ?, ?)",
            (record_id, actor, stamp, stamp, blob),
        )
        audit.append(conn, actor, "create", "client", record_id, "ok")
    return record_id


def read_record(actor: str, record_id: str) -> dict[str, Any]:
    outcome = "ok"
    payload: dict[str, Any] | None = None
    failure: Exception | None = None
    with db.transaction() as conn:
        row = conn.execute(
            "SELECT owner_sub, ciphertext FROM client_records WHERE id = ?", (record_id,)
        ).fetchone()
        if row is None or row["owner_sub"] != actor:
            outcome = "denied_or_missing"
        else:
            try:
                payload = decrypt_payload(row["ciphertext"], _aad(record_id, row["owner_sub"]))
            except Exception as exc:  # integrity or key failure: audit, then re-raise after commit
                outcome, failure = "integrity_failure", exc
        audit.append(conn, actor, "read", "client", record_id, outcome)
    if failure is not None:
        raise failure
    if payload is None:
        raise RecordNotFound(record_id)
    return payload


def update_record(actor: str, record_id: str, payload: dict[str, Any]) -> None:
    db.dialect()
    blob = encrypt_payload(payload, _aad(record_id, actor))
    with db.transaction() as conn:
        updated = conn.execute(
            "UPDATE client_records SET ciphertext = ?, updated_at = ? WHERE id = ? AND owner_sub = ?",
            (blob, audit.now(), record_id, actor),
        ).rowcount
        audit.append(conn, actor, "update", "client", record_id, "ok" if updated else "denied_or_missing")
    if not updated:
        raise RecordNotFound(record_id)


def client_owner(conn: db.Conn, client_id: str) -> str | None:
    row = conn.execute("SELECT owner_sub FROM client_records WHERE id = ?", (client_id,)).fetchone()
    return None if row is None else row["owner_sub"]


def audit_entries(record_id: str | None = None) -> list[dict[str, Any]]:
    return audit.entries(record_id)
