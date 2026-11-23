"""Append-only, hash-chained audit events.

Each event stores the SHA-256 of the previous event's hash plus its own canonical
fields, so editing, deleting or reordering any earlier row breaks verification.
The database also rejects UPDATE/DELETE on audit_events (triggers in migrations).
Audit rows carry actor, action, object type/id and outcome only: never clinical
payloads, notes, tokens or secrets.
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


def append(conn: db.Conn, actor: str, action: str, object_type: str, record_id: str | None, outcome: str) -> None:
    db.lock_audit_chain(conn)
    last = conn.execute("SELECT hash FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = last["hash"] if last else GENESIS
    fields = {
        "ts": now(),
        "actor_sub": actor,
        "action": action,
        "object_type": object_type,
        "record_id": record_id,
        "outcome": outcome,
    }
    conn.execute(
        "INSERT INTO audit_events (ts, actor_sub, action, object_type, record_id, outcome, prev_hash, hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            fields["ts"], actor, action, object_type, record_id, outcome,
            prev_hash, _digest(prev_hash, fields),
        ),
    )


def entries(record_id: str | None = None, limit: int = 500, after_id: int = 0) -> list[dict[str, Any]]:
    with db.transaction() as conn:
        if record_id is None:
            return conn.execute(
                "SELECT * FROM audit_events WHERE id > ? ORDER BY id LIMIT ?", (after_id, limit)
            ).fetchall()
        return conn.execute(
            "SELECT * FROM audit_events WHERE record_id = ? AND id > ? ORDER BY id LIMIT ?",
            (record_id, after_id, limit),
        ).fetchall()


def verify_chain() -> dict[str, Any]:
    """Recompute every hash in order. Returns ok plus the first broken event id, if any."""
    with db.transaction() as conn:
        rows = conn.execute("SELECT * FROM audit_events ORDER BY id").fetchall()
    prev_hash = GENESIS
    for row in rows:
        fields = {k: row[k] for k in ("ts", "actor_sub", "action", "object_type", "record_id", "outcome")}
        if row["prev_hash"] != prev_hash or row["hash"] != _digest(prev_hash, fields):
            return {"ok": False, "events_checked": len(rows), "first_broken_event_id": row["id"]}
        prev_hash = row["hash"]
    return {"ok": True, "events_checked": len(rows), "first_broken_event_id": None}
