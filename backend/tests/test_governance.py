"""Consent, retention, legal holds and two-person disposal. Synthetic data only."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import governance
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

OWNER, OTHER, REV, ADMIN1, ADMIN2 = "clin-own", "clin-other", "rev-1", "admin-1", "admin-2"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer"}}


def sha(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@pytest.fixture
def retention(monkeypatch):
    """Configure a 365-day period and move the governance clock 400 days ahead."""
    monkeypatch.setenv(governance.RETENTION_ENV, "365")

    def later(days: int = 400) -> None:
        monkeypatch.setattr(governance, "_now", lambda: datetime.now(timezone.utc) + timedelta(days=days))

    return later


def new_client(act) -> str:
    act(OWNER, "clinician")
    response = client.post("/v1/clients", json={"display_code": "SYN-GOV"})
    assert response.status_code == 201
    return response.json()["id"]


def signed_off_assessment(act, cid: str, flags: list[str] | None = None) -> str:
    act(OWNER, "clinician")
    aid = client.post("/v1/assessments", json={"client_id": cid, "form_id": "whole_person_initial",
                                               "form_version": "v2.6", "payload": PAYLOAD}).json()["id"]
    assert client.post(f"/v1/assessments/{aid}/submit", json={"safety_flags": flags or []}).status_code == 200
    for flag in client.get(f"/v1/assessments/{aid}/safety-flags").json():
        assert client.post(f"/v1/assessments/{aid}/safety-flags/{flag['id']}/acknowledge").status_code == 200
    act(REV, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 200
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)}).status_code == 200
    return aid


def request_disposal(act, cid: str, admin: str = ADMIN1):
    act(admin, "admin")
    return client.post("/v1/admin/disposals", json={"client_id": cid, "reason_code": "retention_elapsed"})


# --------------------------------------------------------------------------- consent


def test_consent_record_list_and_single_withdrawal(backend, act):
    cid = new_client(act)
    created = client.post(f"/v1/clients/{cid}/consents",
                          json={"scope": "assessment", "consent_text_ref": "STN-CONSENT-DRAFT-0.1"})
    assert created.status_code == 201, created.text
    consent = created.json()
    assert consent["captured_by"] == OWNER and consent["withdrawn_at"] is None
    listed = client.get(f"/v1/clients/{cid}/consents").json()
    assert [c["id"] for c in listed] == [consent["id"]]
    withdrawn = client.post(f"/v1/clients/{cid}/consents/{consent['id']}/withdraw")
    assert withdrawn.status_code == 200 and withdrawn.json()["withdrawn_by"] == OWNER
    assert client.post(f"/v1/clients/{cid}/consents/{consent['id']}/withdraw").status_code == 409


def test_consent_is_owner_and_org_scoped_and_validated(backend, act):
    cid = new_client(act)
    assert client.post(f"/v1/clients/{cid}/consents", json={"scope": "has spaces", "consent_text_ref": "x"}).status_code == 422
    act(OTHER, "clinician")
    assert client.post(f"/v1/clients/{cid}/consents", json={"scope": "a", "consent_text_ref": "b"}).status_code == 404
    assert client.get(f"/v1/clients/{cid}/consents").status_code == 404
    act(OWNER, "clinician", org="org-synthetic-other")
    assert client.get(f"/v1/clients/{cid}/consents").status_code == 404


def test_consent_rows_cannot_be_rewritten_or_deleted(backend, act, raw):
    cid = new_client(act)
    consent = client.post(f"/v1/clients/{cid}/consents", json={"scope": "a", "consent_text_ref": "b"}).json()
    with pytest.raises(Exception, match="consent records"):
        raw("UPDATE consents SET scope = 'tampered' WHERE id = ?", (consent["id"],))
    with pytest.raises(Exception, match="consent records"):
        raw("DELETE FROM consents WHERE id = ?", (consent["id"],))


# --------------------------------------------------------------------------- retention policy


def test_disposal_fails_closed_without_retention_policy(backend, act, monkeypatch):
    monkeypatch.delenv(governance.RETENTION_ENV, raising=False)
    cid = new_client(act)
    act(ADMIN1, "admin")
    policy = client.get("/v1/admin/retention/policy").json()
    assert policy["configured"] is False and "Retention of Health Information" in policy["basis_note"]
    assert request_disposal(act, cid).status_code == 503
    assert client.get("/v1/admin/retention/due").status_code == 503
    monkeypatch.setenv(governance.RETENTION_ENV, "not-a-number")
    assert request_disposal(act, cid).status_code == 503
    monkeypatch.setenv(governance.RETENTION_ENV, "0")
    assert request_disposal(act, cid).status_code == 503


def test_disposal_refused_before_period_elapses(backend, act, retention):
    cid = new_client(act)
    response = request_disposal(act, cid)
    assert response.status_code == 409 and "not yet elapsed" in response.json()["detail"]
    assert client.get("/v1/admin/retention/due").json() == []


# --------------------------------------------------------------------------- disposal


def test_two_person_disposal_removes_payloads_and_leaves_tombstone(backend, act, raw, retention):
    cid = new_client(act)
    aid = signed_off_assessment(act, cid, flags=["synthetic_flag"])
    retention()
    act(ADMIN1, "admin")
    assert [d["client_id"] for d in client.get("/v1/admin/retention/due").json()] == [cid]

    requested = request_disposal(act, cid)
    assert requested.status_code == 201, requested.text
    disposal = requested.json()
    assert disposal["state"] == "requested" and disposal["retention_period_days"] == 365

    same_person = client.post(f"/v1/admin/disposals/{disposal['id']}/approve")
    assert same_person.status_code == 403 and "different person" in same_person.json()["detail"]
    act(OWNER, "clinician")
    assert client.post(f"/v1/admin/disposals/{disposal['id']}/approve").status_code == 403

    act(ADMIN2, "admin")
    approved = client.post(f"/v1/admin/disposals/{disposal['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"] == "executed" and approved.json()["assessments_disposed"] == 1

    act(OWNER, "clinician")
    assert client.get(f"/v1/clients/{cid}").status_code == 410
    assert client.get(f"/v1/assessments/{aid}").status_code == 410
    assert client.put(f"/v1/clients/{cid}", json={"x": 1}).status_code == 410
    tombstones = client.get(f"/v1/clients/{cid}/assessments").json()
    assert tombstones[0]["id"] == aid and tombstones[0]["disposed_at"] and tombstones[0]["content_hash"] == sha(PAYLOAD)

    assert raw("SELECT length(ciphertext) FROM client_records WHERE id = ?", (cid,))[0][0] == 0
    assert raw("SELECT length(ciphertext), note_ciphertext FROM assessments WHERE id = ?", (aid,))[0] == (0, None)
    codes = [r[0] for r in raw("SELECT code FROM safety_flags WHERE assessment_id = ?", (aid,))]
    assert codes and all(c.startswith("disposed:") for c in codes)

    with pytest.raises(Exception, match="final"):
        raw("UPDATE client_records SET ciphertext = ? WHERE id = ?", (b"x", cid))
    with pytest.raises(Exception, match="final|immutable"):
        raw("UPDATE assessments SET ciphertext = ? WHERE id = ?", (b"x", aid))
    with pytest.raises(Exception, match="cannot be deleted"):
        raw("DELETE FROM client_records WHERE id = ?", (cid,))

    act(ADMIN1, "admin")
    actions = {(e["action"], e["record_id"]) for e in client.get("/v1/audit", params={"limit": 500}).json()}
    assert {("disposal.request", cid), ("disposal.approve", disposal["id"]),
            ("record.dispose", cid), ("record.dispose", aid)} <= actions
    assert client.get("/v1/audit/verify").json()["ok"] is True
    assert client.post(f"/v1/admin/disposals/{disposal['id']}/approve").status_code == 409
    assert request_disposal(act, cid).status_code == 409


def test_reviewer_can_be_the_second_person(backend, act, retention):
    cid = new_client(act)
    retention()
    disposal = request_disposal(act, cid).json()
    act(REV, "reviewer")
    assert client.post(f"/v1/admin/disposals/{disposal['id']}/approve").status_code == 200


def test_legal_hold_blocks_request_and_approval(backend, act, retention):
    cid = new_client(act)
    retention()
    act(ADMIN1, "admin")
    hold = client.post("/v1/admin/legal-holds", json={"client_id": cid, "reason_code": "litigation"})
    assert hold.status_code == 201
    assert client.get("/v1/admin/retention/due").json() == []
    blocked = request_disposal(act, cid)
    assert blocked.status_code == 409 and "legal hold" in blocked.json()["detail"]

    assert client.post(f"/v1/admin/legal-holds/{hold.json()['id']}/release").status_code == 200
    assert client.post(f"/v1/admin/legal-holds/{hold.json()['id']}/release").status_code == 409
    disposal = request_disposal(act, cid).json()
    second_hold = client.post("/v1/admin/legal-holds", json={"client_id": cid, "reason_code": "complaint"})
    assert second_hold.status_code == 201
    act(ADMIN2, "admin")
    response = client.post(f"/v1/admin/disposals/{disposal['id']}/approve")
    assert response.status_code == 409 and "legal hold" in response.json()["detail"]
    act(OWNER, "clinician")
    assert client.get(f"/v1/clients/{cid}").status_code == 200


def test_active_review_blocks_disposal(backend, act, retention):
    cid = new_client(act)
    act(OWNER, "clinician")
    aid = client.post("/v1/assessments", json={"client_id": cid, "form_id": "f", "form_version": "v1",
                                               "payload": PAYLOAD}).json()["id"]
    client.post(f"/v1/assessments/{aid}/submit", json={})
    retention()
    response = request_disposal(act, cid)
    assert response.status_code == 409 and "in review" in response.json()["detail"]


def test_cancelled_disposal_is_final(backend, act, retention, raw):
    cid = new_client(act)
    retention()
    disposal = request_disposal(act, cid).json()
    assert request_disposal(act, cid).status_code == 409  # one pending request per client
    act(ADMIN2, "admin")
    assert client.post(f"/v1/admin/disposals/{disposal['id']}/cancel").status_code == 200
    assert client.post(f"/v1/admin/disposals/{disposal['id']}/approve").status_code == 409
    with pytest.raises(Exception, match="final"):
        raw("UPDATE disposals SET state = 'requested' WHERE id = ?", (disposal["id"],))
    assert [d["state"] for d in client.get("/v1/admin/disposals").json()] == ["cancelled"]


def test_admin_governance_routes_need_admin_and_same_org(backend, act, retention):
    cid = new_client(act)
    retention()
    act(OWNER, "clinician")
    assert client.get("/v1/admin/retention/due").status_code == 403
    assert client.post("/v1/admin/legal-holds", json={"client_id": cid, "reason_code": "x"}).status_code == 403
    act(ADMIN1, "admin", org="org-synthetic-other")
    assert client.post("/v1/admin/legal-holds", json={"client_id": cid, "reason_code": "x"}).status_code == 404
    assert client.post("/v1/admin/disposals", json={"client_id": cid, "reason_code": "x"}).status_code == 404
    assert client.get("/v1/admin/retention/due").json() == []
