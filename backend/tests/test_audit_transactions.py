"""Transaction-boundary tests for the client-record store and its audit trail.

Synthetic identifiers, payloads and a throwaway key only. These are backend tests; they do
not constitute production validation.
"""
from __future__ import annotations

import base64
import secrets
import sqlite3

import pytest

from app import audit, rbac, store
from app.crypto import RecordIntegrityError
from app.rbac import Role

OWNER = "clinician-owner"
OTHER = "clinician-other"
PAYLOAD = {"synthetic_note": "SYNTHETIC-TX-MARKER"}


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "tx.sqlite3"
    monkeypatch.setenv(store.DB_ENV, str(path))
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    rbac.grant_system_role(OWNER, Role.AUTHORISED_CLINICIAN)
    rbac.grant_system_role(OTHER, Role.AUTHORISED_CLINICIAN)
    return path


def _actions(record_id: str) -> list[tuple[str, str]]:
    return [(e["action"], e["outcome"]) for e in store.audit_entries(record_id)]


def _record_count() -> int:
    conn = sqlite3.connect(store._db_path())
    try:
        return conn.execute("SELECT COUNT(*) FROM client_records").fetchone()[0]
    finally:
        conn.close()


def test_denied_read_leaves_a_durable_audit_entry(db):
    rid = store.create_record(OWNER, PAYLOAD)
    with pytest.raises(store.RecordNotFound):
        store.read_record(OTHER, rid)
    assert ("client.read", "denied_or_missing") in _actions(rid)
    assert audit.verify() == (True, None)


def test_denied_read_does_not_disclose_payload(db):
    rid = store.create_record(OWNER, PAYLOAD)
    with pytest.raises(store.RecordNotFound) as info:
        store.read_record(OTHER, rid)
    assert "SYNTHETIC-TX-MARKER" not in str(info.value)


def test_missing_record_read_is_audited_identically_to_denial(db):
    rid = store.create_record(OWNER, PAYLOAD)
    missing = "00000000-0000-0000-0000-000000000000"
    with pytest.raises(store.RecordNotFound):
        store.read_record(OTHER, missing)
    with pytest.raises(store.RecordNotFound):
        store.read_record(OTHER, rid)
    entries = store.audit_entries()
    outcomes = {e["outcome"] for e in entries if e["action"] == "client.read"}
    assert outcomes == {"denied_or_missing"}


def test_denied_update_leaves_a_durable_audit_entry_and_changes_nothing(db):
    rid = store.create_record(OWNER, PAYLOAD)
    before = store.read_record(OWNER, rid)
    with pytest.raises(store.RecordNotFound):
        store.update_record(OTHER, rid, {"synthetic_note": "OVERWRITE-ATTEMPT"})
    assert ("client.update", "denied_or_missing") in _actions(rid)
    assert store.read_record(OWNER, rid) == before


def test_failed_decryption_records_an_integrity_failure(db):
    rid = store.create_record(OWNER, PAYLOAD)
    conn = sqlite3.connect(store._db_path())
    conn.execute("UPDATE client_records SET ciphertext = ? WHERE id = ?", (b"\x00" * 40, rid))
    conn.commit()
    conn.close()
    with pytest.raises(RecordIntegrityError):
        store.read_record(OWNER, rid)
    assert ("client.read", "integrity_failure") in _actions(rid)
    assert audit.verify() == (True, None)


def test_integrity_failure_is_committed_even_though_the_read_raises(db):
    rid = store.create_record(OWNER, PAYLOAD)
    conn = sqlite3.connect(store._db_path())
    conn.execute("UPDATE client_records SET ciphertext = ? WHERE id = ?", (b"\x01" * 40, rid))
    conn.commit()
    conn.close()
    with pytest.raises(RecordIntegrityError):
        store.read_record(OWNER, rid)
    # A fresh connection sees the committed audit row, not a rolled-back one.
    assert ("client.read", "integrity_failure") in _actions(rid)


def test_application_exception_after_denial_does_not_erase_the_denial(db):
    rid = store.create_record(OWNER, PAYLOAD)

    def caller():
        try:
            store.read_record(OTHER, rid)
        except store.RecordNotFound:
            raise RuntimeError("caller failed after the denial")

    with pytest.raises(RuntimeError):
        caller()
    assert ("client.read", "denied_or_missing") in _actions(rid)


def test_create_is_atomic_when_its_audit_write_fails(db, monkeypatch):
    before = _record_count()
    audit_rows_before = len(store.audit_entries())

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("simulated audit failure")

    with monkeypatch.context() as patch:
        patch.setattr(audit, "append_in_tx", fail)
        with pytest.raises(sqlite3.OperationalError):
            store.create_record(OWNER, PAYLOAD)
    assert _record_count() == before
    assert len(store.audit_entries()) == audit_rows_before


def test_update_is_atomic_when_its_audit_write_fails(db, monkeypatch):
    rid = store.create_record(OWNER, PAYLOAD)
    before = store.read_record(OWNER, rid)

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("simulated audit failure")

    with monkeypatch.context() as patch:
        patch.setattr(audit, "append_in_tx", fail)
        with pytest.raises(sqlite3.OperationalError):
            store.update_record(OWNER, rid, {"synthetic_note": "SHOULD-NOT-PERSIST"})
    assert store.read_record(OWNER, rid) == before


def test_successful_operations_write_data_and_audit_together(db):
    rid = store.create_record(OWNER, PAYLOAD)
    store.update_record(OWNER, rid, {"synthetic_note": "UPDATED"})
    assert store.read_record(OWNER, rid) == {"synthetic_note": "UPDATED"}
    assert _actions(rid) == [("client.create", "ok"), ("client.update", "ok"), ("client.read", "ok")]
    assert audit.verify() == (True, None)


def test_schema_refusal_writes_neither_audit_nor_data(db):
    before = len(store.audit_entries())
    with pytest.raises(audit.AuditSchemaError):
        audit.append("system", "client.read", "record:x", {"outcome": "SYNTHETIC free text"})
    assert len(store.audit_entries()) == before
