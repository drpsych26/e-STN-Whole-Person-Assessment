import sqlite3

import pytest

from app.store import Store


def test_consent_survives_reopening_the_database(tmp_path):
    db = tmp_path / "stn.db"
    s = Store(db)
    s.record_consent("C-0001", "assessment", True, "clinician-1")
    s.close()

    reopened = Store(db)
    records = reopened.consents_for("C-0001")
    reopened.close()
    assert len(records) == 1
    assert records[0]["purpose"] == "assessment" and records[0]["granted"] is True


def test_consent_records_write_an_audit_event(tmp_path):
    s = Store(tmp_path / "stn.db")
    s.record_consent("C-0002", "follow-up", False, "clinician-1")
    events = s.audit_events("C-0002")
    s.close()
    assert [e["action"] for e in events] == ["consent.recorded"]
    assert events[0]["detail"] == {"granted": False, "purpose": "follow-up"}


def test_audit_events_cannot_be_updated(tmp_path):
    s = Store(tmp_path / "stn.db")
    s.append_audit("clinician-1", "record.viewed", "C-0003")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        s._conn.execute("UPDATE audit_event SET actor = 'someone-else'")
    s.close()


def test_audit_events_cannot_be_deleted(tmp_path):
    s = Store(tmp_path / "stn.db")
    s.append_audit("clinician-1", "record.viewed", "C-0004")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        s._conn.execute("DELETE FROM audit_event")
    assert len(s.audit_events()) == 1
    s.close()


def test_consent_rejects_blank_client_reference(tmp_path):
    s = Store(tmp_path / "stn.db")
    with pytest.raises(sqlite3.IntegrityError):
        s.record_consent("", "assessment", True, "clinician-1")
    s.close()
