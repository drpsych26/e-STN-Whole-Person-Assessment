"""Reviewer assignment and the reassignment queue (default: assignment required). Synthetic data only."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import review_assignment
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

AUTHOR, REV1, REV2, ADMIN, ADMIN2 = "clin-ra", "rev-ra-1", "rev-ra-2", "admin-ra", "admin-ra-2"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer"}}


def sha(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def submitted(act, flags: list[str] | None = None) -> str:
    act(AUTHOR, "clinician")
    cid = client.post("/v1/clients", json={"display_code": "SYN-RA"}).json()["id"]
    aid = client.post("/v1/assessments", json={"client_id": cid, "form_id": "whole_person_initial",
                                               "form_version": "v2.6", "payload": PAYLOAD}).json()["id"]
    assert client.post(f"/v1/assessments/{aid}/submit", json={"safety_flags": flags or []}).status_code == 200
    return aid


def assign(act, aid: str, reviewer: str, admin: str = ADMIN):
    act(admin, "admin")
    return client.post(f"/v1/admin/assessments/{aid}/reviewer", json={"reviewer_sub": reviewer})


def outcomes(act, aid: str) -> list[tuple[str, str]]:
    act(ADMIN, "admin")
    return [(e["action"], e["outcome"]) for e in client.get("/v1/audit?limit=500").json() if e["record_id"] == aid]


def test_assignment_is_required_by_default(backend, act, monkeypatch):
    monkeypatch.delenv("STN_REVIEW_ASSIGNMENT_REQUIRED", raising=False)
    aid = submitted(act)
    act(REV1, "reviewer")
    assert all(q["id"] != aid for q in client.get("/v1/review-queue").json()), "unassigned work is not offered"
    blocked = client.post(f"/v1/assessments/{aid}/start-review")
    assert blocked.status_code == 409 and "assigned" in blocked.json()["detail"]
    assert ("assessment.start_review", "rejected_unassigned") in outcomes(act, aid)


def test_only_the_assigned_reviewer_starts_review(backend, act):
    aid = submitted(act)
    assigned = assign(act, aid, REV1)
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["reviewer_sub"] == REV1 and body["assigned_by"] == ADMIN and body["replaced_reviewer_sub"] is None

    act(REV2, "reviewer")
    assert all(q["id"] != aid for q in client.get("/v1/review-queue").json())
    other = client.post(f"/v1/assessments/{aid}/start-review")
    assert other.status_code == 403 and "another reviewer" in other.json()["detail"]

    act(REV1, "reviewer")
    item = next(q for q in client.get("/v1/review-queue").json() if q["id"] == aid)
    assert item["assigned_reviewer"] == REV1 and "payload" not in item
    assert client.post(f"/v1/assessments/{aid}/start-review").json()["reviewer_sub"] == REV1
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)}).status_code == 200
    assert ("assessment.start_review", "rejected_not_assigned") in outcomes(act, aid)
    assert ("review.assign", "ok") in outcomes(act, aid)


def test_reassignment_replaces_the_reviewer_and_keeps_history(backend, act):
    aid = submitted(act)
    assert assign(act, aid, REV1).status_code == 200
    second = assign(act, aid, REV2, admin=ADMIN2)
    assert second.status_code == 200 and second.json()["replaced_reviewer_sub"] == REV1
    assert assign(act, aid, REV2).status_code == 409, "assigning the same reviewer again is a conflict"

    act(ADMIN, "admin")
    history = client.get(f"/v1/admin/assessments/{aid}/reviewer-history").json()
    assert [(h["reviewer_sub"], h["end_reason"]) for h in history] == [(REV1, "reassigned"), (REV2, None)]
    assert history[0]["ended_by"] == ADMIN2

    act(REV1, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 403
    act(REV2, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 200
    assert ("review.reassign", "ok") in outcomes(act, aid)


def test_self_assignment_and_author_assignment_are_refused(backend, act):
    aid = submitted(act)
    act(ADMIN, "admin", "reviewer")
    own = client.post(f"/v1/admin/assessments/{aid}/reviewer", json={"reviewer_sub": ADMIN})
    assert own.status_code == 403 and "yourself" in own.json()["detail"]
    author = assign(act, aid, AUTHOR)
    assert author.status_code == 403
    assert assign(act, aid, "has spaces").status_code == 422
    found = outcomes(act, aid)
    assert ("review.assign", "rejected_self_assignment") in found and ("review.assign", "rejected_self_review") in found


def test_only_admins_assign(backend, act):
    aid = submitted(act)
    for roles in (("reviewer",), ("clinician",)):
        act(REV1, *roles)
        assert client.post(f"/v1/admin/assessments/{aid}/reviewer", json={"reviewer_sub": REV2}).status_code == 403


def test_assignment_only_while_submitted(backend, act):
    act(AUTHOR, "clinician")
    cid = client.post("/v1/clients", json={"display_code": "SYN-RA"}).json()["id"]
    draft = client.post("/v1/assessments", json={"client_id": cid, "form_id": "f", "form_version": "v1",
                                                 "payload": PAYLOAD}).json()["id"]
    assert assign(act, draft, REV1).status_code == 409
    aid = submitted(act)
    assert assign(act, aid, REV1).status_code == 200
    act(REV1, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 200
    assert assign(act, aid, REV2).status_code == 409, "no reassignment once review has started"
    assert assign(act, "00000000-0000-0000-0000-000000000000", REV1).status_code == 404


def test_inactive_or_unregistered_reviewers_cannot_be_assigned(backend, act, monkeypatch):
    aid = submitted(act)
    act(ADMIN, "admin")
    assert client.post("/v1/admin/accounts", json={"subject": REV1}).status_code == 201
    invited = assign(act, aid, REV1)
    assert invited.status_code == 409 and "not active" in invited.json()["detail"]
    act(ADMIN, "admin")
    assert client.post(f"/v1/admin/accounts/{REV1}/activate", json={}).status_code == 200
    assert client.post(f"/v1/admin/accounts/{REV1}/suspend", json={"reason_code": "leave"}).status_code == 200
    assert assign(act, aid, REV1).status_code == 409
    monkeypatch.setenv("STN_ACCOUNT_REGISTRY_REQUIRED", "true")
    act(ADMIN, "admin")
    assert client.post("/v1/admin/accounts", json={"subject": ADMIN}).status_code == 403, "admin is unregistered"
    monkeypatch.setenv("STN_ACCOUNT_REGISTRY_REQUIRED", "false")
    assert assign(act, aid, REV2).status_code == 200, "unregistered is allowed when registration is optional"
    assert ("review.assign", "rejected_reviewer_not_active") in outcomes(act, aid)


def test_resubmission_ends_the_assignment(backend, act):
    aid = submitted(act)
    assert assign(act, aid, REV1).status_code == 200
    act(REV1, "reviewer")
    client.post(f"/v1/assessments/{aid}/start-review")
    assert client.post(f"/v1/assessments/{aid}/return", json={"reason": "Synthetic return note."}).status_code == 200
    act(AUTHOR, "clinician")
    client.post(f"/v1/assessments/{aid}/reopen")
    assert client.post(f"/v1/assessments/{aid}/submit", json={}).status_code == 200
    act(REV1, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 409, "new submission is unassigned"
    act(ADMIN, "admin")
    history = client.get(f"/v1/admin/assessments/{aid}/reviewer-history").json()
    assert [(h["submission"], h["end_reason"]) for h in history] == [(1, "resubmitted")]


def test_deactivating_a_reviewer_returns_work_to_the_queue(backend, act):
    aid = submitted(act)
    act(ADMIN, "admin")
    client.post("/v1/admin/accounts", json={"subject": REV1})
    client.post(f"/v1/admin/accounts/{REV1}/activate", json={})
    assert assign(act, aid, REV1).status_code == 200
    act(ADMIN, "admin")
    assert all(q["id"] != aid for q in client.get("/v1/admin/review-assignments").json()), "freshly assigned"
    assert client.post(f"/v1/admin/accounts/{REV1}/deactivate", json={"reason_code": "left_org"}).status_code == 200
    queue = client.get("/v1/admin/review-assignments").json()
    entry = next(q for q in queue if q["id"] == aid)
    assert entry["reason"] == "unassigned" and "payload" not in entry
    assert client.get(f"/v1/admin/assessments/{aid}/reviewer-history").json()[0]["end_reason"] == "reviewer_deactivated"
    assert ("review.unassign", "reviewer_deactivated") in outcomes(act, aid)


def test_stale_assignments_appear_in_the_reassignment_queue(backend, act, monkeypatch):
    aid = submitted(act, flags=["synthetic_flag"])
    assert assign(act, aid, REV1).status_code == 200
    act(ADMIN, "admin")
    assert all(q["id"] != aid for q in client.get("/v1/admin/review-assignments?older_than_hours=1").json())

    class Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz or timezone.utc) + timedelta(hours=3)

    monkeypatch.setattr(review_assignment, "datetime", Later)
    entry = next(q for q in client.get("/v1/admin/review-assignments?older_than_hours=1").json() if q["id"] == aid)
    assert entry["reason"] == "stale" and entry["assigned_reviewer"] == REV1
    assert entry["unacknowledged_safety_flags"] == 1
    assert all(q["id"] != aid for q in client.get("/v1/admin/review-assignments?older_than_hours=4").json())


def test_assignment_is_organisation_scoped(backend, act):
    aid = submitted(act)
    act(ADMIN, "admin", org="org-synthetic-2")
    assert client.post(f"/v1/admin/assessments/{aid}/reviewer", json={"reviewer_sub": REV1}).status_code == 404
    assert client.get(f"/v1/admin/assessments/{aid}/reviewer-history").status_code == 404
    assert client.get("/v1/admin/review-assignments").json() == []


def test_assigned_reviewer_is_enforced_in_the_open_pool_too(backend, act, open_review_pool):
    aid = submitted(act)
    act(REV2, "reviewer")
    assert any(q["id"] == aid for q in client.get("/v1/review-queue").json()), "open pool offers unassigned work"
    assert assign(act, aid, REV1).status_code == 200
    act(REV2, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 403


def test_assignment_rows_cannot_be_deleted_or_rewritten(backend, act, raw):
    aid = submitted(act)
    assign(act, aid, REV1)
    with pytest.raises(Exception, match="cannot be deleted"):
        raw("DELETE FROM review_assignments WHERE assessment_id = ?", (aid,))
    with pytest.raises(Exception, match="single end"):
        raw("UPDATE review_assignments SET reviewer_sub = ? WHERE assessment_id = ?", (REV2, aid))
