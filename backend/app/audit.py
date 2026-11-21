"""Append-only, hash-chained audit trail.

Each row stores the SHA-256 of its own content plus the previous row's hash, so any
edit or deletion breaks verification. SQLite triggers also block UPDATE and DELETE.
Callers must pass identifiers and state names only in `detail`, never client content.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from . import store

GENESIS = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(prev_hash: str, ts: str, actor: str, action: str, subject_ref: str, detail: str) -> str:
    material = "|".join([prev_hash, ts, actor, action, subject_ref, detail])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def append_in_tx(conn: sqlite3.Connection, actor: str, action: str, subject_ref: str, detail: dict[str, Any]) -> int:
    """Append inside a transaction the caller has already opened."""
    last = conn.execute("SELECT hash FROM audit_chain ORDER BY seq DESC LIMIT 1").fetchone()
    prev = last["hash"] if last else GENESIS
    ts = _now()
    detail_json = json.dumps(detail, sort_keys=True, separators=(",", ":"))
    digest = _digest(prev, ts, actor, action, subject_ref, detail_json)
    cur = conn.execute(
        "INSERT INTO audit_chain (ts, actor, action, subject_ref, detail, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ts, actor, action, subject_ref, detail_json, prev, digest),
    )
    return int(cur.lastrowid)


def append(actor: str, action: str, subject_ref: str, detail: dict[str, Any]) -> int:
    with store._connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            seq = append_in_tx(conn, actor, action, subject_ref, detail)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return seq


def verify() -> tuple[bool, int | None]:
    """Recompute the chain. Returns (True, None) if intact, else (False, first bad seq)."""
    with store._connect() as conn:
        expected_prev = GENESIS
        for row in conn.execute("SELECT * FROM audit_chain ORDER BY seq"):
            if row["prev_hash"] != expected_prev:
                return False, row["seq"]
            digest = _digest(row["prev_hash"], row["ts"], row["actor"], row["action"],
                             row["subject_ref"], row["detail"])
            if digest != row["hash"]:
                return False, row["seq"]
            expected_prev = row["hash"]
    return True, None
