"""Safety escalation tests: ownership, acknowledgement, resolution, visibility and audit.
Synthetic identities, data and a throwaway key only. Not production validation."""
from __future__ import annotations

import base64
import secrets
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import audit, auth, crisis_resources, rbac, safety, store
from app.main import app
from app.rbac import Role

PATIENT = "patient-safety-1"
OTHER_PATIENT = "patient-safety-2"
CLINICIAN = "clinician-safety-1"
CLINICIAN_2 = "clinician-safety-2"
CUSTOMER_ONLY = "customer-safety-1"

client = TestClient(app)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv(store.DB_ENV, str(tmp_path / "safety.sqlite3"))
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    rbac.grant_system_role(CLINICIAN, Role.AUTHORISED_CLINICIAN)
    rbac.grant_system_role(CLINICIAN_2, Role.CLINICAL_SUPERVISOR)
    return tmp_path


def _open(actor=PATIENT, subject=PATIENT, source="crisis_panel", severity="urgent"):
    return safety.open_escalation(actor, subject, source, severity)


def _doc(owner: str) -> str:
    return store.create_record(owner, {"synthetic_note": "SYNTHETIC-SAFETY-DOC"})


def _row(escalation_id: str):
    conn = sqlite3.connect(store._db_path())
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM safety_escalations WHERE id = ?", (escalation_id,)).fetchone()
    finally:
        conn.close()


# ---------- opening ----------

def test_person_can_open_an_escalation_about_themselves(env):
    result = _open()
    row = _row(result["id"])
    assert row["status"] == "open" and row["subject"] == PATIENT and row["opened_by"] == PATIENT
    assert row["opened_at"] and row["acknowledged_at"] is None


def test_person_cannot_open_an_escalation_about_someone_else(env):
    with pytest.raises(safety.NotPermitted):
        _open(actor=PATIENT, subject=OTHER_PATIENT)


def test_clinician_can_open_for_a_client(env):
    result = _open(actor=CLINICIAN, subject=PATIENT, source="clinician_report", severity="high")
    assert _row(result["id"])["opened_by"] == CLINICIAN


def test_unknown_source_or_severity_is_refused(env):
    with pytest.raises(safety.InvalidState):
        _open(source="free text")
    with pytest.raises(safety.InvalidState):
        _open(severity="whenever")


# ---------- acknowledgement and resolution ----------

def test_only_clinical_staff_can_acknowledge(env):
    result = _open()
    with pytest.raises(safety.NotPermitted):
        safety.acknowledge(PATIENT, result["id"])
    with pytest.raises(safety.NotPermitted):
        safety.acknowledge(CUSTOMER_ONLY, result["id"])


def test_acknowledgement_records_who_and_when_and_is_single_use(env):
    result = _open()
    safety.acknowledge(CLINICIAN, result["id"])
    row = _row(result["id"])
    assert row["status"] == "acknowledged" and row["acknowledged_by"] == CLINICIAN
    assert row["acknowledged_at"]
    with pytest.raises(safety.InvalidState):
        safety.acknowledge(CLINICIAN_2, result["id"])


def test_resolution_requires_prior_acknowledgement(env):
    result = _open()
    doc = _doc(CLINICIAN)
    with pytest.raises(safety.InvalidState):
        safety.resolve(CLINICIAN, result["id"], "safety_plan_agreed", doc)


def test_only_the_acknowledging_clinician_can_resolve(env):
    result = _open()
    safety.acknowledge(CLINICIAN, result["id"])
    doc = _doc(CLINICIAN_2)
    with pytest.raises(safety.NotPermitted):
        safety.resolve(CLINICIAN_2, result["id"], "safety_plan_agreed", doc)


def test_resolution_needs_a_coded_outcome_and_an_owned_documentation_record(env):
    result = _open()
    safety.acknowledge(CLINICIAN, result["id"])
    with pytest.raises(safety.InvalidState, match="Unknown resolution code"):
        safety.resolve(CLINICIAN, result["id"], "felt fine", _doc(CLINICIAN))
    with pytest.raises(safety.InvalidState, match="client record you own"):
        safety.resolve(CLINICIAN, result["id"], "safety_plan_agreed", "no-such-record")
    other_doc = _doc(CLINICIAN_2)
    with pytest.raises(safety.InvalidState, match="client record you own"):
        safety.resolve(CLINICIAN, result["id"], "safety_plan_agreed", other_doc)


def test_full_lifecycle_resolves_with_documentation(env):
    result = _open()
    safety.acknowledge(CLINICIAN, result["id"])
    doc = _doc(CLINICIAN)
    safety.resolve(CLINICIAN, result["id"], "referred_crisis_team", doc)
    row = _row(result["id"])
    assert row["status"] == "resolved"
    assert row["resolution_code"] == "referred_crisis_team"
    assert row["documentation_record"] == doc
    assert row["resolved_by"] == CLINICIAN and row["resolved_at"]


def test_resolved_escalation_cannot_be_resolved_again(env):
    result = _open()
    safety.acknowledge(CLINICIAN, result["id"])
    safety.resolve(CLINICIAN, result["id"], "safety_plan_agreed", _doc(CLINICIAN))
    with pytest.raises(safety.InvalidState):
        safety.resolve(CLINICIAN, result["id"], "safety_plan_agreed", _doc(CLINICIAN))


# ---------- visibility, integrity and audit ----------

def test_unresolved_list_is_clinical_only_and_excludes_resolved(env):
    open_one = _open()
    resolved = _open(subject=OTHER_PATIENT, actor=OTHER_PATIENT)
    safety.acknowledge(CLINICIAN, resolved["id"])
    safety.resolve(CLINICIAN, resolved["id"], "safety_plan_agreed", _doc(CLINICIAN))
    with pytest.raises(safety.NotPermitted):
        safety.list_unresolved(PATIENT)
    ids = [item["id"] for item in safety.list_unresolved(CLINICIAN)]
    assert open_one["id"] in ids and resolved["id"] not in ids


def test_unacknowledged_escalation_is_flagged_overdue_after_threshold(env, monkeypatch):
    result = _open()
    from datetime import datetime, timedelta, timezone

    future = datetime.now(timezone.utc) + timedelta(minutes=safety.OVERDUE_MINUTES + 1)
    monkeypatch.setattr(safety, "_now", lambda: future)
    item = [i for i in safety.list_unresolved(CLINICIAN) if i["id"] == result["id"]][0]
    assert item["overdue"] is True


def test_rows_cannot_be_deleted_or_have_opening_facts_changed(env):
    result = _open()
    conn = sqlite3.connect(store._db_path())
    try:
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute("DELETE FROM safety_escalations WHERE id = ?", (result["id"],))
        with pytest.raises(sqlite3.DatabaseError, match="opening facts are fixed"):
            conn.execute("UPDATE safety_escalations SET subject = 'someone-else' WHERE id = ?", (result["id"],))
    finally:
        conn.close()


def test_every_transition_is_audited_and_chain_verifies(env):
    result = _open()
    safety.acknowledge(CLINICIAN, result["id"])
    safety.resolve(CLINICIAN, result["id"], "safety_plan_agreed", _doc(CLINICIAN))
    conn = sqlite3.connect(store._db_path())
    try:
        actions = [r[0] for r in conn.execute(
            "SELECT action FROM audit_chain WHERE subject_ref = ? ORDER BY seq", (f"escalation:{result['id']}",))]
    finally:
        conn.close()
    assert actions == ["safety.opened", "safety.acknowledged", "safety.resolved"]
    assert audit.verify() == (True, None)


def test_refused_transition_is_audited(env):
    result = _open()
    with pytest.raises(safety.NotPermitted):
        safety.acknowledge(CUSTOMER_ONLY, result["id"])
    conn = sqlite3.connect(store._db_path())
    try:
        assert conn.execute("SELECT COUNT(*) FROM audit_chain WHERE action = 'safety.denied'").fetchone()[0] == 1
    finally:
        conn.close()


# ---------- crisis resources ----------

def test_crisis_resources_are_public_and_marked_unreviewed():
    response = client.get("/v1/safety/crisis-resources")
    assert response.status_code == 200
    body = response.json()
    assert body["panel_status"]["clinically_reviewed"] is False
    numbers = {r["id"]: r["contact"] for r in body["resources"]}
    assert numbers["emergency"] == "111"
    assert numbers["need_to_talk"].startswith("1737")
    assert numbers["samaritans"] == "0800 726 666"


def test_every_crisis_resource_has_an_explicit_hours_status():
    for item in crisis_resources.CRISIS_RESOURCES:
        assert item["hours"] in {"24/7", "unresolved"}
        if item["hours"] == "unresolved":
            assert item["hours_note"], f"{item['id']} has unresolved hours without a note"


def test_unauthenticated_escalation_open_is_refused(env):
    response = client.post("/v1/safety/escalations", json={"source": "crisis_panel", "severity": "urgent"})
    assert response.status_code == 401


def test_escalation_routes_enforce_roles(env, monkeypatch):
    app.dependency_overrides[auth.require_identity] = lambda: {"sub": PATIENT}
    try:
        opened = client.post("/v1/safety/escalations", json={"source": "crisis_panel", "severity": "urgent"})
        assert opened.status_code == 201
        eid = opened.json()["id"]
        assert client.get("/v1/safety/escalations/unresolved").status_code == 403
        assert client.post(f"/v1/safety/escalations/{eid}/acknowledge").status_code == 403
    finally:
        app.dependency_overrides.pop(auth.require_identity, None)
