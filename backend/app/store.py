"""Persistent, append-only audit and consent storage (non-live foundation).

Uses SQLite from the standard library for development and tests. Production must
use the managed PostgreSQL-compatible database described in the release requirements.
Audit events are append-only: UPDATE and DELETE are blocked by database triggers.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS consent_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_ref TEXT NOT NULL CHECK (length(client_ref) BETWEEN 1 AND 64),
    purpose TEXT NOT NULL CHECK (length(purpose) BETWEEN 1 AND 200),
    granted INTEGER NOT NULL CHECK (granted IN (0, 1)),
    recorded_at TEXT NOT NULL,
    recorded_by TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    subject_ref TEXT,
    detail TEXT NOT NULL DEFAULT '{}'
);
CREATE TRIGGER IF NOT EXISTS audit_event_no_update
BEFORE UPDATE ON audit_event
BEGIN
    SELECT RAISE(ABORT, 'audit_event is append-only');
END;
CREATE TRIGGER IF NOT EXISTS audit_event_no_delete
BEFORE DELETE ON audit_event
BEGIN
    SELECT RAISE(ABORT, 'audit_event is append-only');
END;
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str | Path):
        self._conn = sqlite3.connect(str(path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def record_consent(self, client_ref: str, purpose: str, granted: bool, recorded_by: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO consent_record (client_ref, purpose, granted, recorded_at, recorded_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (client_ref, purpose, int(granted), _now(), recorded_by),
        )
        self._conn.commit()
        self.append_audit(recorded_by, "consent.recorded", client_ref, {"purpose": purpose, "granted": granted})
        return int(cur.lastrowid)

    def consents_for(self, client_ref: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, purpose, granted, recorded_at, recorded_by FROM consent_record "
            "WHERE client_ref = ? ORDER BY id",
            (client_ref,),
        ).fetchall()
        return [
            {"id": r[0], "purpose": r[1], "granted": bool(r[2]), "recorded_at": r[3], "recorded_by": r[4]}
            for r in rows
        ]

    def append_audit(self, actor: str, action: str, subject_ref: str | None, detail: dict[str, Any] | None = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO audit_event (occurred_at, actor, action, subject_ref, detail) VALUES (?, ?, ?, ?, ?)",
            (_now(), actor, action, subject_ref, json.dumps(detail or {}, sort_keys=True)),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def audit_events(self, subject_ref: str | None = None) -> list[dict[str, Any]]:
        if subject_ref is None:
            rows = self._conn.execute("SELECT id, occurred_at, actor, action, subject_ref, detail FROM audit_event ORDER BY id").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, occurred_at, actor, action, subject_ref, detail FROM audit_event WHERE subject_ref = ? ORDER BY id",
                (subject_ref,),
            ).fetchall()
        return [
            {"id": r[0], "occurred_at": r[1], "actor": r[2], "action": r[3], "subject_ref": r[4], "detail": json.loads(r[5])}
            for r in rows
        ]
