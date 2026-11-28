"""Safety escalation lifecycle, role separation, organisation separation and monitoring. Synthetic data only."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CLIN, CLIN2, REV, ADMIN = "clin-se", "clin-se-2", "rev-se", "admin-se"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer"}}


@pytest.fixture
def setup(backend, act):
    act(CLIN, "clinician")
    cid = client.post("/v1/clients", json={"display_code": "SYN-SE"}).json()["id"]
    aid = client.post("/v1/assessments", json={"client_id": cid, "form_id": "whole_person_initial",
                                               "form_version": "v2.6", "payload": PAYLOAD}).json()["id"]
    return cid, aid


def open_one(cid: str, severity: str = "urgent_assessment", **extra):
    return client.post("/v1/safety-escalations",
                       json={"client_id": cid, "source": "clinician_report", "severity": severity, **extra})


def audit_rows(act, record_id: str) -> list[tuple[str, str]]:
    act(ADMIN, "admin")
    return [(e["action"], e["outcome"]) for e in client.get("/v1/audit?limit=500").json() if e["record_id"] == record_id]


def test_full_lifecycle_is_audited(setup, act):
    cid, aid = setup
    r = open_one(cid)
    assert r.status_code == 201, r.text
    esc = r.json()
    assert esc["status"] == "open" and esc["owner_sub"] is None and esc["overdue"] is False
    eid = esc["id"]

    act(REV, "reviewer")
    r = client.post(f"/v1/safety-escalations/{eid}/acknowledge")
    assert r.status_code == 200 and r.json()["owner_sub"] == REV and r.json()["status"] == "acknowledged"

    act(CLIN2, "clinician")
    r = client.post(f"/v1/safety-escalations/{eid}/acknowledge")
    assert r.status_code == 200 and r.json()["owner_sub"] == CLIN2  # handover

    r = client.post(f"/v1/safety-escalations/{eid}/resolve",
                    json={"resolution_code": "safety_plan_agreed", "documentation_ref": aid})
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["status"] == "resolved" and done["resolved_by"] == CLIN2 and done["documentation_ref"] == aid

    assert client.post(f"/v1/safety-escalations/{eid}/acknowledge").status_code == 409
    assert client.post(f"/v1/safety-escalations/{eid}/resolve",
                       json={"resolution_code": "safety_plan_agreed", "documentation_ref": aid}).status_code == 409

    assert audit_rows(act, eid)[:4] == [
        ("safety_escalation.open.urgent_assessment", "ok"),
        ("safety_escalation.acknowledge", "ok"),
        ("safety_escalation.handover", "ok"),
        ("safety_escalation.resolve.safety_plan_agreed", "ok"),
    ]


def test_admin_sees_queue_but_cannot_act(setup, act):
    cid, _ = setup
    eid = open_one(cid).json()["id"]
    act(ADMIN, "admin")
    assert client.post("/v1/safety-escalations", json={"client_id": cid, "source": "manual"}).status_code == 403
    assert client.post(f"/v1/safety-escalations/{eid}/acknowledge").status_code == 403
    assert client.get(f"/v1/safety-escalations/{eid}").status_code == 403
    queue = client.get("/v1/safety-escalations")
    assert queue.status_code == 200 and [e["id"] for e in queue.json()] == [eid]


def test_resolution_requires_acknowledgement_and_documentation(setup, act):
    cid, aid = setup
    eid = open_one(cid).json()["id"]
    body = {"resolution_code": "safety_plan_agreed", "documentation_ref": aid}
    assert client.post(f"/v1/safety-escalations/{eid}/resolve", json=body).status_code == 409
    client.post(f"/v1/safety-escalations/{eid}/acknowledge")
    assert client.post(f"/v1/safety-escalations/{eid}/resolve",
                       json={"resolution_code": "fine", "documentation_ref": aid}).status_code == 422
    assert client.post(f"/v1/safety-escalations/{eid}/resolve",
                       json={"resolution_code": "safety_plan_agreed"}).status_code == 422
    other = client.post("/v1/clients", json={"display_code": "SYN-SE-OTHER"}).json()["id"]
    other_aid = client.post("/v1/assessments", json={"client_id": other, "form_id": "whole_person_initial",
                                                     "form_version": "v2.6", "payload": PAYLOAD}).json()["id"]
    r = client.post(f"/v1/safety-escalations/{eid}/resolve",
                    json={"resolution_code": "safety_plan_agreed", "documentation_ref": other_aid})
    assert r.status_code == 422  # documentation must be about the same client
    assert ("safety_escalation.resolve.safety_plan_agreed", "rejected_documentation") in audit_rows(act, eid)


def test_input_validation(setup):
    cid, aid = setup
    assert open_one(cid, severity="severe").status_code == 422
    assert client.post("/v1/safety-escalations",
                       json={"client_id": cid, "source": "gossip", "severity": "routine_monitoring"}).status_code == 422
    assert client.post("/v1/safety-escalations",
                       json={"client_id": cid, "source": "assessment_item", "severity": "routine_monitoring"}
                       ).status_code == 422  # assessment sources need assessment_id
    r = client.post("/v1/safety-escalations", json={"client_id": cid, "source": "assessment_item",
                                                     "severity": "increased_concern", "assessment_id": aid})
    assert r.status_code == 201 and r.json()["assessment_id"] == aid
    assert open_one("no-such-client").status_code == 404


def test_other_organisation_cannot_see_or_act(setup, act):
    cid, _ = setup
    eid = open_one(cid).json()["id"]
    act("clin-other-org", "clinician", org="org-synthetic-2")
    assert client.get(f"/v1/safety-escalations/{eid}").status_code == 404
    assert client.post(f"/v1/safety-escalations/{eid}/acknowledge").status_code == 404
    assert open_one(cid).status_code == 404
    assert client.get("/v1/safety-escalations").json() == []


def test_overdue_ordering_and_configurable_windows(setup, act, monkeypatch):
    from app import safety_escalations

    cid, _ = setup
    routine = open_one(cid, severity="routine_monitoring").json()["id"]
    urgent = open_one(cid, severity="urgent_assessment").json()["id"]
    emergency = open_one(cid, severity="immediate_emergency").json()["id"]
    real = datetime

    class Later(datetime):  # the clock moves 30 minutes on; opening times cannot be rewritten
        @classmethod
        def now(cls, tz=None):
            return real.now(tz) + timedelta(minutes=30)

    monkeypatch.setattr(safety_escalations, "datetime", Later)
    monkeypatch.setenv("STN_SAFETY_ACK_MINUTES", "routine_monitoring=10,immediate_emergency=60")
    queue = client.get("/v1/safety-escalations").json()
    assert [e["id"] for e in queue] == [routine, emergency, urgent]
    assert queue[0]["overdue"] is True and queue[1]["overdue"] is False
    client.post(f"/v1/safety-escalations/{routine}/acknowledge")
    assert client.get(f"/v1/safety-escalations/{routine}").json()["overdue"] is False


def test_rows_cannot_be_deleted_or_rewritten(setup, act, raw):
    cid, aid = setup
    eid = open_one(cid).json()["id"]
    with pytest.raises(Exception):
        raw("DELETE FROM safety_escalations WHERE id = ?", (eid,))
    with pytest.raises(Exception):
        raw("UPDATE safety_escalations SET severity = 'routine_monitoring' WHERE id = ?", (eid,))
    client.post(f"/v1/safety-escalations/{eid}/acknowledge")
    client.post(f"/v1/safety-escalations/{eid}/resolve",
                json={"resolution_code": "monitoring_plan_documented", "documentation_ref": aid})
    with pytest.raises(Exception):
        raw("UPDATE safety_escalations SET status = 'open' WHERE id = ?", (eid,))


def test_client_history(setup, act):
    cid, _ = setup
    first = open_one(cid, severity="increased_concern").json()["id"]
    second = open_one(cid, severity="urgent_assessment").json()["id"]  # concern rose: new escalation
    history = client.get(f"/v1/safety-escalations/by-client/{cid}").json()
    assert [e["id"] for e in history] == [first, second]
