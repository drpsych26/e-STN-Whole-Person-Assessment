"""Append-only, hash-chained audit trail.

Each row stores the SHA-256 of its own content plus the previous row's hash, so any
edit or deletion breaks verification. SQLite triggers also block UPDATE and DELETE.
Callers must pass identifiers and state names only in `detail`, never client content.

Enforcement: every action has an entry in ACTION_SCHEMA listing the only detail keys it may
carry and, for each key, the allowed values (an enumeration) or an identifier pattern.
Unknown actions, unknown keys, free text, and values that do not match fail closed with
AuditSchemaError before anything is written. Actor and subject_ref are checked the same way.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from . import store

GENESIS = "0" * 64

# Identifier: letters, digits and a few separators only. No spaces, no '@', no free text.
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
REF = re.compile(r"^[a-z_]{1,32}:[A-Za-z0-9_.:-]{1,128}$")

CLIENT_OUTCOMES = frozenset({"ok", "denied_or_missing", "integrity_failure"})
ROLE_NAMES = frozenset({
    "platform_administrator", "organisation_administrator", "clinical_director",
    "authorised_clinician", "clinical_supervisor", "intake_coordinator", "customer", "auditor",
})
STAGE_NAMES = frozenset({
    "registered", "contact_verified", "account_active", "privacy_acknowledged", "consented",
    "intake_eligible", "screened", "allocated", "team_assigned", "complete",
})
ACK_KINDS = frozenset({"terms", "privacy_notice", "consent"})
ATTESTATION_KINDS = frozenset({"eligibility", "screening", "allocation", "team_assignment"})
RECORD_TYPES = frozenset({"eligibility_review", "screening_review", "allocation", "team_assignment"})


class AuditSchemaError(ValueError):
    """Raised when an audit entry does not match its action's schema."""


# action -> {detail key: allowed set of values, or IDENTIFIER for opaque identifiers}
ACTION_SCHEMA: dict[str, dict[str, object]] = {
    "client.create": {"outcome": CLIENT_OUTCOMES},
    "client.read": {"outcome": CLIENT_OUTCOMES},
    "client.update": {"outcome": CLIENT_OUTCOMES},
    "rbac.grant": {"role": ROLE_NAMES},
    "rbac.revoke": {"role": ROLE_NAMES},
    "rbac.denied": {"role": ROLE_NAMES},
    "rbac.denied_provisional": {"role": ROLE_NAMES},
    "access.denied": {},
    "access.denied_provisional": {},
    "onboarding.create": {"stage": STAGE_NAMES},
    "onboarding.advance": {"from": STAGE_NAMES, "to": STAGE_NAMES},
    "onboarding.suspend": {},
    "acknowledgement.recorded": {"kind": ACK_KINDS, "version": IDENTIFIER},
    "attestation.denied": {"kind": ATTESTATION_KINDS},
    "attestation.recorded": {"kind": ATTESTATION_KINDS, "record_id": IDENTIFIER},
    "platform_record.created": {"record_type": RECORD_TYPES, "record_id": IDENTIFIER},
    "platform_record.denied": {"record_type": RECORD_TYPES},
    "verification.recorded": {"kind": frozenset({"email", "phone", "mfa"}), "event_id": IDENTIFIER},
    "safety.opened": {"source": frozenset({"crisis_panel", "assessment_item", "clinician_report", "manual"}),
                      "severity": frozenset({"urgent", "high", "routine"})},
    "safety.acknowledged": {},
    "safety.resolved": {"code": frozenset({"safety_plan_agreed", "referred_emergency", "referred_crisis_team",
                                           "no_risk_identified_documented", "other_documented"})},
    "safety.denied": {},
}


def validate_entry(actor: str, action: str, subject_ref: str, detail: dict[str, Any]) -> None:
    """Fail closed unless the entry matches the action's schema. Called before every write."""
    if action not in ACTION_SCHEMA:
        raise AuditSchemaError(f"Unknown audit action: {action}")
    if not IDENTIFIER.match(actor):
        raise AuditSchemaError("Actor identifier does not match the audit identifier format.")
    if not REF.match(subject_ref):
        raise AuditSchemaError("Subject reference does not match the audit reference format.")
    schema = ACTION_SCHEMA[action]
    for key, value in detail.items():
        if key not in schema:
            raise AuditSchemaError(f"Audit key '{key}' is not permitted for {action}.")
        allowed = schema[key]
        if not isinstance(value, str):
            raise AuditSchemaError(f"Audit value for '{key}' must be a string identifier.")
        if allowed is IDENTIFIER:
            if not IDENTIFIER.match(value):
                raise AuditSchemaError(f"Audit value for '{key}' is not an identifier.")
        elif value not in allowed:
            raise AuditSchemaError(f"Audit value for '{key}' is not an allowed value.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(prev_hash: str, ts: str, actor: str, action: str, subject_ref: str, detail: str) -> str:
    material = "|".join([prev_hash, ts, actor, action, subject_ref, detail])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def append_in_tx(conn: sqlite3.Connection, actor: str, action: str, subject_ref: str, detail: dict[str, Any]) -> int:
    """Append inside a transaction the caller has already opened."""
    validate_entry(actor, action, subject_ref, detail)
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
