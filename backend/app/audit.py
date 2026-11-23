"""Append-only, hash-chained audit events.

Each event stores the SHA-256 of the previous event's hash plus its own canonical
fields, so editing, deleting or reordering any earlier row breaks verification.
The database also rejects UPDATE/DELETE on audit_events (triggers in migrations).
Audit rows carry actor, organisation, action, object type/id, outcome and, for
exports, the SHA-256 of the exported document: never clinical payloads, notes,
tokens or secrets. org_id and content_hash enter the hash only when present, so
events written before those columns existed still verify unchanged. The chain is
platform-wide; listing is scoped to the caller's organisation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from . import db

GENESIS = "0" * 64


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(prev_hash: str, fields: dict[str, Any]) -> str:
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{prev_hash}|{canonical}".encode("utf-8")).hexdigest()


_BASE_FIELDS = ("ts", "actor_sub", "action", "object_type", "record_id", "outcome")
_OPTIONAL_FIELDS = ("org_id", "content_hash")


def _fields(row: dict[str, Any]) -> dict[str, Any]:
    fields = {k: row[k] for k in _BASE_FIELDS}
    for key in _OPTIONAL_FIELDS:
        if row.get(key) is not None:
            fields[key] = row[key]
    return fields


def append(
    conn: db.Conn,
    actor: str,
    action: str,
    object_type: str,
    record_id: str | None,
    outcome: str,
    *,
    org: str | None = None,
    content_hash: str | None = None,
) -> None:
    db.lock_audit_chain(conn)
    last = conn.execute("SELECT hash FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = last["hash"] if last else GENESIS
    row = {
        "ts": now(),
        "actor_sub": actor,
        "action": action,
        "object_type": object_type,
        "record_id": record_id,
        "outcome": outcome,
        "org_id": org,
        "content_hash": content_hash,
    }
    conn.execute(
        "INSERT INTO audit_events (ts, actor_sub, action, object_type, record_id, outcome, org_id, content_hash, "
        "prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row["ts"], actor, action, object_type, record_id, outcome, org, content_hash,
            prev_hash, _digest(prev_hash, _fields(row)),
        ),
    )


def entries(
    record_id: str | None = None, limit: int = 500, after_id: int = 0, org: str | None = None
) -> list[dict[str, Any]]:
    """Audit rows, optionally for one record id and/or one organisation."""
    clauses, params = ["id > ?"], [after_id]
    if record_id is not None:
        clauses.append("record_id = ?")
        params.append(record_id)
    if org is not None:
        clauses.append("org_id = ?")
        params.append(org)
    with db.transaction() as conn:
        return conn.execute(
            f"SELECT * FROM audit_events WHERE {' AND '.join(clauses)} ORDER BY id LIMIT ?", (*params, limit)
        ).fetchall()


def verify_chain() -> dict[str, Any]:
    """Recompute every hash in order. Returns ok plus the first broken event id, if any."""
    with db.transaction() as conn:
        rows = conn.execute("SELECT * FROM audit_events ORDER BY id").fetchall()
    prev_hash = GENESIS
    for row in rows:
        if row["prev_hash"] != prev_hash or row["hash"] != _digest(prev_hash, _fields(row)):
            return {"ok": False, "events_checked": len(rows), "first_broken_event_id": row["id"]}
        prev_hash = row["hash"]
    return {"ok": True, "events_checked": len(rows), "first_broken_event_id": None}
