"""Organisation (tenant) separation. Synthetic data only; runs on SQLite and PostgreSQL."""
from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# These tests exercise the review rules in the open-pool mode; see open_review_pool in conftest.py.
pytestmark = pytest.mark.usefixtures("open_review_pool")

ORG_A, ORG_B = "org-synthetic-a", "org-synthetic-b"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer"}}


def sha(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def make_client(act, sub: str, org: str) -> str:
    act(sub, "clinician", org=org)
    response = client.post("/v1/clients", json={"display_code": "SYN-ORG"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def make_submitted(act, sub: str, org: str) -> str:
    cid = make_client(act, sub, org)
    aid = client.post("/v1/assessments", json={"client_id": cid, "form_id": "whole_person_initial",
                                               "form_version": "v2.6", "payload": PAYLOAD}).json()["id"]
    assert client.post(f"/v1/assessments/{aid}/submit", json={}).status_code == 200
    return aid


def audit_rows(act, org: str) -> list[dict]:
    act("admin-x", "admin", org=org)
    response = client.get("/v1/audit", params={"limit": 500})
    assert response.status_code == 200, response.text
    return response.json()


def test_same_subject_in_another_org_cannot_see_client(backend, act):
    cid = make_client(act, "clin-shared-sub", ORG_A)
    act("clin-shared-sub", "clinician", org=ORG_B)
    assert client.get(f"/v1/clients/{cid}").status_code == 404
    assert client.put(f"/v1/clients/{cid}", json={"x": 1}).status_code == 404
    assert client.get(f"/v1/clients/{cid}/assessments").status_code == 404
    act("clin-shared-sub", "clinician", org=ORG_A)
    assert client.get(f"/v1/clients/{cid}").status_code == 200


def test_cross_org_denials_are_audited_in_the_callers_org(backend, act):
    cid = make_client(act, "clin-a", ORG_A)
    act("clin-a", "clinician", org=ORG_B)
    assert client.get(f"/v1/clients/{cid}").status_code == 404
    b_events = [e for e in audit_rows(act, ORG_B) if e["record_id"] == cid]
    assert [(e["action"], e["outcome"], e["org_id"]) for e in b_events] == [("read", "denied_or_missing", ORG_B)]
    a_events = [e for e in audit_rows(act, ORG_A) if e["record_id"] == cid]
    assert {e["org_id"] for e in a_events} == {ORG_A}


def test_assessments_are_invisible_across_orgs(backend, act):
    aid = make_submitted(act, "clin-a", ORG_A)
    act("rev-b", "reviewer", org=ORG_B)
    assert client.get("/v1/review-queue").json() == []
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 404
    assert client.get(f"/v1/assessments/{aid}").status_code == 404
    assert client.get(f"/v1/assessments/{aid}/safety-flags").status_code == 404
    act("rev-a", "reviewer", org=ORG_A)
    assert [q["id"] for q in client.get("/v1/review-queue").json()] == [aid]


def test_cross_org_assessment_cannot_be_created_against_foreign_client(backend, act):
    cid = make_client(act, "clin-a", ORG_A)
    act("clin-a", "clinician", org=ORG_B)
    response = client.post("/v1/assessments", json={"client_id": cid, "form_id": "f", "form_version": "v1",
                                                     "payload": PAYLOAD})
    assert response.status_code == 404


def test_admin_audit_listing_is_org_scoped_but_chain_is_whole(backend, act):
    make_client(act, "clin-a", ORG_A)
    make_client(act, "clin-b", ORG_B)
    a_rows = audit_rows(act, ORG_A)
    assert a_rows and {r["org_id"] for r in a_rows} == {ORG_A}
    act("admin-x", "admin", org=ORG_A)
    assert client.get("/v1/audit/verify").json()["ok"] is True


def test_missing_or_malformed_org_fails_closed(backend, act):
    act("clin-a", "clinician", org=None)
    response = client.post("/v1/clients", json={"x": 1})
    assert response.status_code == 403 and "organisation" in response.json()["detail"]
    act("clin-a", "clinician", org="bad org with spaces")
    assert client.post("/v1/clients", json={"x": 1}).status_code == 403
    act("admin-x", "admin", org=None)
    assert client.get("/v1/audit").status_code == 403
