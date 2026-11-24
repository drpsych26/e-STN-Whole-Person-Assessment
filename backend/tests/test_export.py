"""Logged export of signed-off assessments. Synthetic data only."""
from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# These tests exercise the review rules in the open-pool mode; see open_review_pool in conftest.py.
pytestmark = pytest.mark.usefixtures("open_review_pool")

AUTHOR, OTHER, REV, REV2, ADMIN = "clin-exp", "clin-other", "rev-exp", "rev-other", "admin-exp"
MARKER = "SYNTHETIC-EXPORT-MARKER-5D1E"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer", "note": MARKER}}


def sha(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def draft(act) -> str:
    act(AUTHOR, "clinician")
    cid = client.post("/v1/clients", json={"display_code": "SYN-EXP"}).json()["id"]
    return client.post("/v1/assessments", json={"client_id": cid, "form_id": "whole_person_initial",
                                                "form_version": "v2.6", "payload": PAYLOAD}).json()["id"]


def signed_off(act) -> str:
    aid = draft(act)
    client.post(f"/v1/assessments/{aid}/submit", json={})
    act(REV, "reviewer")
    client.post(f"/v1/assessments/{aid}/start-review")
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)}).status_code == 200
    return aid


def export(aid: str, reason: str | None = "client_request"):
    body = {} if reason is None else {"reason_code": reason}
    return client.post(f"/v1/assessments/{aid}/export", json=body)


def test_author_exports_signed_off_record_and_hash_is_logged(backend, act, raw):
    aid = signed_off(act)
    act(AUTHOR, "clinician")
    response = export(aid)
    assert response.status_code == 200, response.text
    body = response.json()
    document = body["export"]
    assert document["format"] == "stn-assessment-export/1"
    assert document["payload"] == PAYLOAD and document["reason_code"] == "client_request"
    assert document["assessment"]["state"] == "signed_off"
    assert body["export_hash"] == sha(document)

    logged = raw("SELECT exported_by, reason_code, export_hash FROM exports WHERE assessment_id = ?", (aid,))
    assert logged == [(AUTHOR, "client_request", body["export_hash"])]

    act(ADMIN, "admin")
    events = [e for e in client.get("/v1/audit", params={"limit": 500}).json() if e["action"] == "assessment.export"]
    assert [(e["record_id"], e["outcome"], e["content_hash"]) for e in events] == [(aid, "ok", body["export_hash"])]
    assert MARKER not in json.dumps(client.get("/v1/audit", params={"limit": 500}).json())
    assert client.get("/v1/audit/verify").json()["ok"] is True


def test_signing_reviewer_may_export_but_others_may_not(backend, act):
    aid = signed_off(act)
    act(REV, "reviewer")
    assert export(aid).status_code == 200
    act(REV2, "reviewer")
    assert export(aid).status_code == 404
    act(OTHER, "clinician")
    assert export(aid).status_code == 404
    act(ADMIN, "admin")
    assert export(aid).status_code == 403
    act(AUTHOR, "clinician", org="org-synthetic-other")
    assert export(aid).status_code == 404


def test_export_needs_reason_and_signed_off_state(backend, act):
    aid = draft(act)
    act(AUTHOR, "clinician")
    assert export(aid).status_code == 409
    signed = signed_off(act)
    act(AUTHOR, "clinician")
    assert export(signed, reason=None).status_code == 422
    assert export(signed, reason="free text is not a code").status_code == 422


def test_export_log_is_append_only(backend, act, raw):
    aid = signed_off(act)
    act(AUTHOR, "clinician")
    export(aid)
    with pytest.raises(Exception, match="append-only"):
        raw("UPDATE exports SET reason_code = 'tampered' WHERE assessment_id = ?", (aid,))
    with pytest.raises(Exception, match="append-only"):
        raw("DELETE FROM exports WHERE assessment_id = ?", (aid,))
