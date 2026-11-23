"""Client access and correction requests (Privacy Act 2020 IPP 6 and IPP 7). Synthetic data only."""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import crypto, governance, privacy_requests, rekey
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# Signing off needs a reviewer; these tests use the open review pool (see conftest.py).
pytestmark = pytest.mark.usefixtures("open_review_pool")

OWNER, OTHER, REV, ADMIN, ADMIN2 = "clin-pr", "clin-pr-other", "rev-pr", "admin-pr", "admin-pr-2"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer"}}
MARKER = "SYNTHETIC-PRIVACY-MARKER-7f3a"
TODAY = datetime.now(timezone.utc).date()


def sha(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def new_client(act) -> str:
    act(OWNER, "clinician")
    return client.post("/v1/clients", json={"display_code": "SYN-PR", "note": MARKER}).json()["id"]


def signed_off(act, cid: str) -> str:
    act(OWNER, "clinician")
    aid = client.post("/v1/assessments", json={"client_id": cid, "form_id": "f", "form_version": "v1",
                                               "payload": PAYLOAD}).json()["id"]
    client.post(f"/v1/assessments/{aid}/submit", json={})
    act(REV, "reviewer")
    client.post(f"/v1/assessments/{aid}/start-review")
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)}).status_code == 200
    return aid


def log(act, cid: str, kind: str, received: str | None = None, admin: str = ADMIN):
    act(admin, "admin")
    return client.post("/v1/admin/privacy-requests",
                       json={"client_id": cid, "kind": kind, "received_on": received or TODAY.isoformat()})


# --------------------------------------------------------------------------- due dates


def test_due_dates_skip_weekends_holidays_and_optional_summer_period():
    friday = date(2026, 11, 20)
    assert privacy_requests.due_date(friday, 1, set(), False) == date(2026, 11, 23)
    assert privacy_requests.due_date(friday, 1, {date(2026, 11, 23)}, False) == date(2026, 11, 24)
    assert privacy_requests.due_date(friday, 20, set(), False) == date(2026, 12, 18)
    wednesday = date(2026, 12, 23)
    assert privacy_requests.due_date(wednesday, 3, set(), False) == date(2026, 12, 28)
    assert privacy_requests.due_date(wednesday, 3, set(), True) == date(2027, 1, 19)


def test_policy_is_unconfigured_by_default_and_reports_problems(monkeypatch):
    for env in (privacy_requests.WORKING_DAYS_ENV, privacy_requests.NON_WORKING_ENV, privacy_requests.SUMMER_ENV):
        monkeypatch.delenv(env, raising=False)
    policy = privacy_requests.policy()
    assert policy["configured"] is False and policy["response_working_days"] is None
    assert "privacy officer" in policy["basis_note"]
    monkeypatch.setenv(privacy_requests.WORKING_DAYS_ENV, "20")
    monkeypatch.setenv(privacy_requests.NON_WORKING_ENV, "2026-12-25,not-a-date")
    bad = privacy_requests.policy()
    assert bad["configured"] is False and any("invalid date" in p for p in bad["problems"])
    monkeypatch.setenv(privacy_requests.NON_WORKING_ENV, "2026-12-25")
    assert privacy_requests.policy()["configured"] is True
    monkeypatch.setenv(privacy_requests.WORKING_DAYS_ENV, "0")
    assert privacy_requests.policy()["configured"] is False


def test_request_is_logged_without_a_due_date_when_unconfigured(backend, act, monkeypatch):
    monkeypatch.delenv(privacy_requests.WORKING_DAYS_ENV, raising=False)
    cid = new_client(act)
    logged = log(act, cid, "access")
    assert logged.status_code == 201, logged.text
    body = logged.json()
    assert body["due_on"] is None and body["due_date_configured"] is False and body["state"] == "open"
    act(ADMIN, "admin")
    assert client.get("/v1/admin/privacy-requests/policy").json()["configured"] is False


def test_due_date_and_overdue_flag_when_configured(backend, act, monkeypatch):
    monkeypatch.setenv(privacy_requests.WORKING_DAYS_ENV, "20")
    cid = new_client(act)
    fresh = log(act, cid, "access").json()
    assert fresh["working_days"] == 20 and fresh["due_on"] > TODAY.isoformat() and fresh["overdue"] is False
    old = log(act, cid, "correction", (TODAY - timedelta(days=90)).isoformat()).json()
    assert old["overdue"] is True and old["days_until_due"] < 0
    act(ADMIN, "admin")
    listed = {r["id"]: r for r in client.get("/v1/admin/privacy-requests?state=open").json()}
    assert listed[old["id"]]["overdue"] is True and set(listed) == {fresh["id"], old["id"]}
    assert all("payload" not in r and "statement" not in r for r in listed.values())


def test_intake_validation(backend, act):
    cid = new_client(act)
    assert log(act, cid, "deletion").status_code == 422
    assert log(act, cid, "access", (TODAY + timedelta(days=1)).isoformat()).status_code == 422
    assert log(act, cid, "access", "24/11/2026").status_code == 422
    assert log(act, "00000000-0000-0000-0000-000000000000", "access").status_code == 404
    act(OWNER, "clinician")
    assert client.post("/v1/admin/privacy-requests", json={"client_id": cid, "kind": "access",
                                                           "received_on": TODAY.isoformat()}).status_code == 403
    act(ADMIN, "admin")
    assert client.get("/v1/admin/privacy-requests?state=done").status_code == 422


# --------------------------------------------------------------------------- access


def test_access_response_is_prepared_by_the_owner_and_logged_by_hash(backend, act, raw):
    cid = new_client(act)
    aid = signed_off(act, cid)
    act(OWNER, "clinician")
    draft = client.post("/v1/assessments", json={"client_id": cid, "form_id": "f", "form_version": "v1",
                                                 "payload": {"items": {"x": "draft"}}}).json()["id"]
    rid = log(act, cid, "access").json()["id"]

    act(OTHER, "clinician")
    assert client.post(f"/v1/privacy-requests/{rid}/access-response").status_code == 404
    act(ADMIN, "admin")
    assert client.post(f"/v1/privacy-requests/{rid}/access-response").status_code == 403, "admins get no payloads"

    act(OWNER, "clinician")
    response = client.post(f"/v1/privacy-requests/{rid}/access-response")
    assert response.status_code == 200, response.text
    document, digest = response.json()["export"], response.json()["export_hash"]
    assert document["format"] == privacy_requests.ACCESS_EXPORT_FORMAT and digest == sha(document)
    assert document["client_record"]["note"] == MARKER
    versions = {a["id"]: a for a in document["assessments"]}
    assert versions[aid]["payload"] == PAYLOAD
    assert versions[draft]["payload"] is None and "Not finalised" in versions[draft]["release_note"]
    assert client.post(f"/v1/privacy-requests/{rid}/access-response").status_code == 409, "responded once"

    exports = raw("SELECT assessment_id, reason_code, export_hash FROM exports")
    assert [tuple(e) for e in exports] == [(aid, "privacy_access_request", digest)]
    act(ADMIN, "admin")
    events = [e for e in client.get("/v1/audit?limit=500").json() if e["record_id"] == rid]
    assert [(e["action"], e["outcome"], e["content_hash"]) for e in events if e["outcome"] == "ok"] == [
        ("privacy_request.access_response", "ok", digest)]
    assert all(MARKER not in json.dumps(e) for e in client.get("/v1/audit?limit=500").json())
    row = next(r for r in client.get("/v1/admin/privacy-requests").json() if r["id"] == rid)
    assert row["state"] == "responded" and row["response_kind"] == "access_export" and row["response_hash"] == digest

    closed = client.post(f"/v1/admin/privacy-requests/{rid}/close", json={"outcome_code": "completed"})
    assert closed.status_code == 200 and closed.json()["state"] == "closed" and closed.json()["closed_by"] == ADMIN
    assert client.post(f"/v1/admin/privacy-requests/{rid}/close", json={"outcome_code": "completed"}).status_code == 409
    with pytest.raises(Exception, match="final"):
        raw("UPDATE privacy_requests SET outcome_code = 'refused' WHERE id = ?", (rid,))


def test_close_rules(backend, act):
    cid = new_client(act)
    rid = log(act, cid, "access").json()["id"]
    act(ADMIN, "admin")
    assert client.post(f"/v1/admin/privacy-requests/{rid}/close", json={"outcome_code": "completed"}).status_code == 409
    assert client.post(f"/v1/admin/privacy-requests/{rid}/close", json={"outcome_code": "lost"}).status_code == 422
    withdrawn = client.post(f"/v1/admin/privacy-requests/{rid}/close", json={"outcome_code": "withdrawn"})
    assert withdrawn.status_code == 200 and withdrawn.json()["outcome_code"] == "withdrawn"
    act(OWNER, "clinician")
    assert client.post(f"/v1/privacy-requests/{rid}/access-response").status_code == 409, "closed"


# --------------------------------------------------------------------------- correction


def test_declined_correction_attaches_an_encrypted_statement(backend, act, raw):
    cid = new_client(act)
    rid = log(act, cid, "correction").json()["id"]
    act(OWNER, "clinician")
    assert client.post(f"/v1/privacy-requests/{rid}/access-response").status_code == 409, "wrong kind"
    assert client.post(f"/v1/privacy-requests/{rid}/correction-response",
                       json={"action": "declined"}).status_code == 422, "statement required"
    statement = f"Synthetic statement of correction {MARKER}"
    declined = client.post(f"/v1/privacy-requests/{rid}/correction-response",
                           json={"action": "declined", "statement": statement})
    assert declined.status_code == 200 and declined.json()["response_kind"] == "declined_statement_attached"

    stored = raw("SELECT statement_ciphertext FROM correction_statements WHERE privacy_request_id = ?", (rid,))
    assert len(stored) == 1 and MARKER.encode() not in bytes(stored[0][0])
    listed = client.get(f"/v1/clients/{cid}/correction-statements").json()
    assert [s["statement"] for s in listed] == [statement] and listed[0]["attached_by"] == OWNER

    access_id = log(act, cid, "access").json()["id"]
    act(OWNER, "clinician")
    document = client.post(f"/v1/privacy-requests/{access_id}/access-response").json()["export"]
    assert [s["statement"] for s in document["correction_statements"]] == [statement]

    act(OTHER, "clinician")
    assert client.get(f"/v1/clients/{cid}/correction-statements").status_code == 404
    with pytest.raises(Exception, match="re-encryption or disposal"):
        raw("UPDATE correction_statements SET attached_by = 'someone' WHERE privacy_request_id = ?", (rid,))
    with pytest.raises(Exception, match="cannot be deleted"):
        raw("DELETE FROM correction_statements WHERE privacy_request_id = ?", (rid,))


def test_correction_by_amendment_links_the_new_version(backend, act):
    cid = new_client(act)
    aid = signed_off(act, cid)
    rid = log(act, cid, "correction").json()["id"]
    act(OWNER, "clinician")
    original = client.post(f"/v1/privacy-requests/{rid}/correction-response",
                           json={"action": "amended", "assessment_id": aid})
    assert original.status_code == 409, "link the new version, not the signed-off original"
    new_version = client.post(f"/v1/assessments/{aid}/amendments",
                              json={"payload": {"items": {"synthetic_item_1": "corrected"}},
                                    "reason": "Client correction request."}).json()["id"]
    linked = client.post(f"/v1/privacy-requests/{rid}/correction-response",
                         json={"action": "amended", "assessment_id": new_version})
    assert linked.status_code == 200
    assert linked.json()["amended_assessment_id"] == new_version
    assert linked.json()["response_kind"] == "amended_new_version"
    assert client.get(f"/v1/assessments/{aid}").json()["payload"] == PAYLOAD, "original unchanged"


def test_correction_validation_and_ownership(backend, act):
    cid = new_client(act)
    rid = log(act, cid, "correction").json()["id"]
    act(OWNER, "clinician")
    assert client.post(f"/v1/privacy-requests/{rid}/correction-response", json={"action": "erase"}).status_code == 422
    assert client.post(f"/v1/privacy-requests/{rid}/correction-response",
                       json={"action": "amended"}).status_code == 422
    assert client.post(f"/v1/privacy-requests/{rid}/correction-response",
                       json={"action": "amended", "assessment_id": "missing"}).status_code == 404
    act(OTHER, "clinician")
    assert client.post(f"/v1/privacy-requests/{rid}/correction-response",
                       json={"action": "client_record_corrected"}).status_code == 404
    act(OWNER, "clinician")
    done = client.post(f"/v1/privacy-requests/{rid}/correction-response", json={"action": "client_record_corrected"})
    assert done.status_code == 200 and done.json()["response_kind"] == "client_record_corrected"
    assert [r["id"] for r in client.get(f"/v1/clients/{cid}/privacy-requests").json()] == [rid]


def test_requests_are_organisation_scoped(backend, act):
    cid = new_client(act)
    rid = log(act, cid, "access").json()["id"]
    act(ADMIN, "admin", org="org-synthetic-2")
    assert client.get("/v1/admin/privacy-requests").json() == []
    assert client.post(f"/v1/admin/privacy-requests/{rid}/close", json={"outcome_code": "refused"}).status_code == 404
    assert client.post("/v1/admin/privacy-requests", json={"client_id": cid, "kind": "access",
                                                           "received_on": TODAY.isoformat()}).status_code == 404
    act(OWNER, "clinician", org="org-synthetic-2")
    assert client.post(f"/v1/privacy-requests/{rid}/access-response").status_code == 404


# --------------------------------------------------------------------------- disposal and key rotation


def test_disposal_removes_correction_statements(backend, act, raw, monkeypatch):
    cid = new_client(act)
    rid = log(act, cid, "correction").json()["id"]
    act(OWNER, "clinician")
    client.post(f"/v1/privacy-requests/{rid}/correction-response",
                json={"action": "declined", "statement": "Synthetic statement."})
    monkeypatch.setenv(governance.RETENTION_ENV, "365")
    monkeypatch.setattr(governance, "_now", lambda: datetime.now(timezone.utc) + timedelta(days=400))
    act(ADMIN, "admin")
    did = client.post("/v1/admin/disposals", json={"client_id": cid, "reason_code": "retention_elapsed"}).json()["id"]
    act(ADMIN2, "admin")
    assert client.post(f"/v1/admin/disposals/{did}/approve").status_code == 200
    rows = raw("SELECT statement_ciphertext, disposed_at FROM correction_statements WHERE client_id = ?", (cid,))
    assert len(rows) == 1 and bytes(rows[0][0]) == b"" and rows[0][1] is not None
    act(OWNER, "clinician")
    assert client.get(f"/v1/clients/{cid}/correction-statements").status_code == 410
    act(ADMIN, "admin")
    assert any(e["object_type"] == "correction_statement" and e["action"] == "record.dispose"
               for e in client.get("/v1/audit?limit=500").json())


def test_key_rotation_covers_correction_statements(backend, act, monkeypatch):
    old_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    new_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    monkeypatch.delenv(crypto.KEY_ENV, raising=False)
    monkeypatch.setenv(crypto.KEYS_ENV, f"k-old:{old_key}")
    monkeypatch.setenv(crypto.ACTIVE_ENV, "k-old")
    cid = new_client(act)
    rid = log(act, cid, "correction").json()["id"]
    act(OWNER, "clinician")
    client.post(f"/v1/privacy-requests/{rid}/correction-response",
                json={"action": "declined", "statement": "Synthetic rotated statement."})
    monkeypatch.setenv(crypto.KEYS_ENV, f"k-old:{old_key},k-new:{new_key}")
    monkeypatch.setenv(crypto.ACTIVE_ENV, "k-new")
    before = rekey.status(None)["ciphertexts_by_key_id"]
    assert before.get("k-old", 0) >= 2
    result = rekey.reencrypt("system:test", None)
    assert result["remaining"] == 0 and result["failed"] == 0
    assert set(rekey.status(None)["ciphertexts_by_key_id"]) == {"k-new"}
    monkeypatch.setenv(crypto.KEYS_ENV, f"k-new:{new_key}")
    assert rekey.verify_decrypt(None)["ok"] is True
    act(OWNER, "clinician")
    assert client.get(f"/v1/clients/{cid}/correction-statements").json()[0]["statement"] == "Synthetic rotated statement."
