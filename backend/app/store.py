"""Encrypted client record store with hash-chained audit events.

Only ciphertext and non-clinical metadata (ids, organisation, owner subject,
timestamps) are stored. Audit events record who touched which record id, in which
organisation, and the outcome; they never contain payload content. The database is
selected in app.db: PostgreSQL via STN_DATABASE_URL, or SQLite via STN_DATA_DB
(tests and local synthetic runs).

Every lookup is scoped to the caller's organisation. A record in another
organisation, a missing record and a record owned by someone else all raise
RecordNotFound, so ids cannot be enumerated across owners or organisations.
Disposed records (retention workflow, app.governance) keep their metadata as a
tombstone but no payload, and raise RecordDisposed for their owner.
"""
from __future__ import annotations

import uuid
from typing import Any

from . import audit, db
from .crypto import RecordIntegrityError, decrypt_payload, encrypt_payload
from .db import DB_ENV, StoreNotConfigured  # re-exported for callers and tests

__all__ = ["DB_ENV", "StoreNotConfigured", "RecordNotFound", "RecordDisposed", "create_record", "read_record",
           "update_record", "client_row", "client_aad", "audit_entries"]


class RecordNotFound(LookupError):
    """Raised for missing records and for records the actor may not see.

    All cases return the same error so record ids cannot be enumerated.
    """


class RecordDisposed(LookupError):
    """The record was disposed under the retention policy; only its tombstone remains."""


def client_aad(record_id: str, owner_sub: str) -> bytes:
    return f"{record_id}\x1f{owner_sub}".encode("utf-8")


def create_record(actor: str, org: str, payload: dict[str, Any]) -> str:
    db.dialect()  # fail closed before encrypting or touching storage
    record_id = str(uuid.uuid4())
    blob = encrypt_payload(payload, client_aad(record_id, actor))
    stamp = audit.now()
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO client_records (id, org_id, owner_sub, created_at, updated_at, ciphertext) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (record_id, org, actor, stamp, stamp, blob),
        )
        audit.append(conn, actor, "create", "client", record_id, "ok", org=org)
    return record_id


def read_record(actor: str, org: str, record_id: str) -> dict[str, Any]:
    outcome = "ok"
    payload: dict[str, Any] | None = None
    failure: Exception | None = None
    with db.transaction() as conn:
        row = client_row(conn, record_id, org)
        if row is None or row["owner_sub"] != actor:
            outcome, failure = "denied_or_missing", RecordNotFound(record_id)
        elif row["disposed_at"] is not None:
            outcome, failure = "rejected_disposed", RecordDisposed(record_id)
        else:
            try:
                payload = decrypt_payload(row["ciphertext"], client_aad(record_id, row["owner_sub"]))
            except Exception as exc:  # integrity or key failure: audit, then re-raise after commit
                outcome, failure = "integrity_failure", exc
        audit.append(conn, actor, "read", "client", record_id, outcome, org=org)
    if failure is not None:
        raise failure
    if payload is None:  # explicit check: assert statements are removed under python -O
        raise RecordIntegrityError(record_id)
    return payload


def update_record(actor: str, org: str, record_id: str, payload: dict[str, Any]) -> None:
    db.dialect()
    blob = encrypt_payload(payload, client_aad(record_id, actor))
    failure: Exception | None = None
    with db.transaction() as conn:
        updated = conn.execute(
            "UPDATE client_records SET ciphertext = ?, updated_at = ? "
            "WHERE id = ? AND org_id = ? AND owner_sub = ? AND disposed_at IS NULL",
            (blob, audit.now(), record_id, org, actor),
        ).rowcount
        if updated:
            outcome = "ok"
        else:
            row = client_row(conn, record_id, org)
            if row is not None and row["owner_sub"] == actor and row["disposed_at"] is not None:
                outcome, failure = "rejected_disposed", RecordDisposed(record_id)
            else:
                outcome, failure = "denied_or_missing", RecordNotFound(record_id)
        audit.append(conn, actor, "update", "client", record_id, outcome, org=org)
    if failure is not None:
        raise failure


def client_row(conn: db.Conn, client_id: str, org: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT * FROM client_records WHERE id = ? AND org_id = ?", (client_id, org)
    ).fetchone()


def audit_entries(record_id: str | None = None, org: str | None = None) -> list[dict[str, Any]]:
    return audit.entries(record_id, org=org)
