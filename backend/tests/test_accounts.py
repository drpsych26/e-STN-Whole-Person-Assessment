"""Clinician account registry, request-time enforcement, two-person reactivation and
access review. Synthetic subjects only."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import accounts
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

ORG = "org-synthetic-1"  # the default organisation of the act fixture (conftest.py)
ADMIN1, ADMIN2, CLIN = "admin-acc-1", "admin-acc-2", "clin-acc"


def as_admin(act, sub: str = ADMIN1) -> None:
    act(sub, "admin")


def invite(act, subject: str = CLIN):
    as_admin(act)
    return client.post("/v1/admin/accounts", json={"subject": subject, "reason_code": "new_starter"})


def status_of(act, subject: str = CLIN) -> str:
    as_admin(act)
    return next(a["status"] for a in client.get("/v1/admin/accounts").json() if a["subject"] == subject)


def clinician_can_act(act, subject: str = CLIN) -> int:
    act(subject, "clinician")
    return client.post("/v1/clients", json={"display_code": "SYN-ACC"}).status_code


def test_full_lifecycle_with_request_time_enforcement(backend, act):
    assert clinician_can_act(act) == 201, "unregistered subjects act while registration is optional"
    created = invite(act)
    assert created.status_code == 201 and created.json()["status"] == "invited"
    assert created.json()["invited_by"] == ADMIN1

    act(CLIN, "clinician")
    refused = client.post("/v1/clients", json={"display_code": "SYN-ACC"})
    assert refused.status_code == 403 and "invited" in refused.json()["detail"]

    as_admin(act)
    assert client.post(f"/v1/admin/accounts/{CLIN}/activate", json={}).status_code == 200
    assert clinician_can_act(act) == 201

    as_admin(act)
    assert client.post(f"/v1/admin/accounts/{CLIN}/suspend", json={}).status_code == 422, "reason required"
    assert client.post(f"/v1/admin/accounts/{CLIN}/suspend", json={"reason_code": "leave"}).status_code == 200
    act(CLIN, "clinician")
    suspended = client.get("/v1/review-queue")
    assert suspended.status_code == 403
    assert client.post("/v1/clients", json={"display_code": "SYN-ACC"}).json()["detail"].endswith(
        "suspended in this organisation.")

    as_admin(act)
    assert client.post(f"/v1/admin/accounts/{CLIN}/activate", json={}).status_code == 200, "reinstate"
    assert client.post(f"/v1/admin/accounts/{CLIN}/deactivate", json={"reason_code": "left_org"}).status_code == 200
    assert clinician_can_act(act) == 403
    as_admin(act)
    assert client.post(f"/v1/admin/accounts/{CLIN}/activate", json={}).status_code == 409, "needs two people"

    history = client.get(f"/v1/admin/accounts/{CLIN}/history").json()
    assert [(h["from_status"], h["to_status"]) for h in history] == [
        (None, "invited"), ("invited", "active"), ("active", "suspended"), ("suspended", "active"),
        ("active", "deactivated")]


def test_reactivation_needs_a_second_admin(backend, act):
    invite(act)
    as_admin(act)
    client.post(f"/v1/admin/accounts/{CLIN}/activate", json={})
    client.post(f"/v1/admin/accounts/{CLIN}/deactivate", json={"reason_code": "left_org"})
    assert client.post(f"/v1/admin/accounts/{CLIN}/reactivation-requests", json={}).status_code == 422
    request = client.post(f"/v1/admin/accounts/{CLIN}/reactivation-requests", json={"reason_code": "rehired"})
    assert request.status_code == 201 and request.json()["state"] == "requested"
    rid = request.json()["id"]
    assert client.post(f"/v1/admin/accounts/{CLIN}/reactivation-requests",
                       json={"reason_code": "rehired"}).status_code == 409, "one pending request at a time"
    same = client.post(f"/v1/admin/account-reactivations/{rid}/approve")
    assert same.status_code == 403 and "different admin" in same.json()["detail"]
    assert clinician_can_act(act) == 403

    as_admin(act, ADMIN2)
    approved = client.post(f"/v1/admin/account-reactivations/{rid}/approve")
    assert approved.status_code == 200 and approved.json()["decided_by"] == ADMIN2
    assert status_of(act) == "active" and clinician_can_act(act) == 201
    as_admin(act, ADMIN2)
    assert client.post(f"/v1/admin/account-reactivations/{rid}/approve").status_code == 409, "decided is final"


def test_reactivation_can_be_cancelled(backend, act):
    invite(act)
    as_admin(act)
    client.post(f"/v1/admin/accounts/{CLIN}/deactivate", json={"reason_code": "never_started"})
    rid = client.post(f"/v1/admin/accounts/{CLIN}/reactivation-requests", json={"reason_code": "error"}).json()["id"]
    cancelled = client.post(f"/v1/admin/account-reactivations/{rid}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled"
    as_admin(act, ADMIN2)
    assert client.post(f"/v1/admin/account-reactivations/{rid}/approve").status_code == 409
    assert status_of(act) == "deactivated"


def test_admins_cannot_change_their_own_account(backend, act):
    invite(act, ADMIN1)
    as_admin(act, ADMIN2)
    client.post(f"/v1/admin/accounts/{ADMIN1}/activate", json={})
    as_admin(act, ADMIN1)
    own = client.post(f"/v1/admin/accounts/{ADMIN1}/suspend", json={"reason_code": "test"})
    assert own.status_code == 403 and "your own account" in own.json()["detail"]
    as_admin(act, ADMIN2)
    client.post(f"/v1/admin/accounts/{ADMIN1}/deactivate", json={"reason_code": "left_org"})
    as_admin(act, ADMIN2)
    rid = client.post(f"/v1/admin/accounts/{ADMIN1}/reactivation-requests", json={"reason_code": "back"}).json()["id"]
    as_admin(act, ADMIN1)
    assert client.post(f"/v1/admin/account-reactivations/{rid}/approve").status_code == 403, "deactivated admin is refused"


def test_validation_conflicts_and_missing_subjects(backend, act):
    as_admin(act)
    assert client.post("/v1/admin/accounts", json={"subject": "has spaces"}).status_code == 422
    assert client.post("/v1/admin/accounts", json={"subject": CLIN, "reason_code": "bad code"}).status_code == 422
    assert invite(act).status_code == 201
    assert invite(act).status_code == 409
    as_admin(act)
    assert client.post("/v1/admin/accounts/nobody-here/activate", json={}).status_code == 404
    assert client.get("/v1/admin/accounts/nobody-here/history").status_code == 404
    assert client.post(f"/v1/admin/accounts/{CLIN}/suspend", json={"reason_code": "x"}).status_code == 409, "invited"
    assert client.get("/v1/admin/accounts?status=unknown").status_code == 422
    assert [a["subject"] for a in client.get("/v1/admin/accounts?status=invited").json()] == [CLIN]


def test_only_admins_manage_accounts(backend, act):
    for roles in (("clinician",), ("reviewer",)):
        act("someone", *roles)
        assert client.post("/v1/admin/accounts", json={"subject": CLIN}).status_code == 403
        assert client.get("/v1/admin/access-review").status_code == 403


def test_status_is_per_organisation(backend, act):
    invite(act)
    as_admin(act)
    client.post(f"/v1/admin/accounts/{CLIN}/deactivate", json={"reason_code": "left_org"})
    act(CLIN, "clinician", org="org-synthetic-2")
    assert client.post("/v1/clients", json={"display_code": "SYN-ACC"}).status_code == 201
    act(ADMIN1, "admin", org="org-synthetic-2")
    assert client.get("/v1/admin/accounts").json() == []
    assert client.post(f"/v1/admin/accounts/{CLIN}/activate", json={}).status_code == 404


def test_registration_can_be_required(backend, act, monkeypatch):
    monkeypatch.setenv(accounts.REQUIRED_ENV, "true")
    unregistered = clinician_can_act(act)
    assert unregistered == 403
    accounts.main(["register", "--org", ORG, "--subject", ADMIN1, "--activate"])
    as_admin(act)
    assert client.post("/v1/admin/accounts", json={"subject": CLIN}).status_code == 201
    assert client.post(f"/v1/admin/accounts/{CLIN}/activate", json={}).status_code == 200
    assert clinician_can_act(act) == 201
    as_admin(act)
    assert client.get("/v1/admin/access-review").json()["registry_required"] is True


def test_registration_required_without_a_store_fails_closed(act, monkeypatch):
    monkeypatch.setenv(accounts.REQUIRED_ENV, "true")
    monkeypatch.delenv("STN_DATA_DB", raising=False)
    monkeypatch.delenv("STN_DATABASE_URL", raising=False)
    act(CLIN, "clinician")
    assert client.get("/v1/review-queue").status_code == 403, "role check comes first"
    act(CLIN, "reviewer")
    assert client.get("/v1/review-queue").status_code == 503


def test_denials_and_transitions_are_audited(backend, act):
    invite(act)
    clinician_can_act(act)
    as_admin(act)
    events = [(e["action"], e["outcome"]) for e in client.get("/v1/audit?limit=500").json()
              if e["record_id"] == CLIN]
    assert ("account.invite", "ok") in events and ("account.access", "denied_invited") in events


def test_access_review_report(backend, act):
    for subject in (CLIN, "rev-acc", "idle-acc"):
        invite(act, subject)
        as_admin(act)
        client.post(f"/v1/admin/accounts/{subject}/activate", json={})
    as_admin(act)
    client.post("/v1/admin/accounts/idle-acc/deactivate", json={"reason_code": "left_org"})
    client.post("/v1/admin/accounts/idle-acc/reactivation-requests", json={"reason_code": "rehired"})
    clinician_can_act(act)
    act("rev-acc", "reviewer", "clinician")
    assert client.get("/v1/review-queue").status_code == 200

    as_admin(act)
    report = client.get("/v1/admin/access-review").json()
    by = {a["subject"]: a for a in report["accounts"]}
    assert by[CLIN]["roles_last_presented"] == ["clinician"] and by[CLIN]["last_seen_at"]
    assert by["rev-acc"]["roles_last_presented"] == ["clinician", "reviewer"]
    assert by[CLIN]["inactive"] is False
    assert by["idle-acc"]["status"] == "deactivated" and by["idle-acc"]["reactivation_pending"] is True
    assert report["counts"] == {"invited": 0, "active": 2, "suspended": 0, "deactivated": 1}
    assert report["registry_required"] is False and "identity provider" in report["note"]

    invite(act, "never-seen")
    as_admin(act)
    client.post("/v1/admin/accounts/never-seen/activate", json={})
    report = client.get("/v1/admin/access-review?inactive_after_days=30").json()
    never = next(a for a in report["accounts"] if a["subject"] == "never-seen")
    assert never["inactive"] is True and report["inactive_active_accounts"] == 1
    assert any(e["action"] == "access_review.read" for e in client.get("/v1/audit?limit=500").json())


def test_registry_tables_are_append_only(backend, act, raw):
    invite(act)
    with pytest.raises(Exception, match="append-only"):
        raw("UPDATE account_events SET to_status = 'active' WHERE subject = ?", (CLIN,))
    with pytest.raises(Exception, match="cannot be deleted"):
        raw("DELETE FROM clinician_accounts WHERE subject = ?", (CLIN,))
