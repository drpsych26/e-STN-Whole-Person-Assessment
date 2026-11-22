"""Assessment records and clinician review workflow. Synthetic data only."""
from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

MARKER = "SYNTHETIC-ASSESSMENT-MARKER-91C2"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer", "note": MARKER}}
AUTHOR, OTHER_CLIN, REV1, REV2, DUAL, ADMIN = "clin-a", "clin-b", "rev-1", "rev-2", "dual-1", "admin-1"
STATES = ("draft", "submitted", "in_review", "returned", "signed_off")


def sha(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def new_client(act, owner: str = AUTHOR) -> str:
    act(owner, "clinician")
    response = client.post("/v1/clients", json={"display_code": "SYN-0001"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def new_assessment(act, owner: str = AUTHOR, payload: dict = PAYLOAD) -> dict:
    client_id = new_client(act, owner)
    act(owner, "clinician", "reviewer") if owner == DUAL else act(owner, "clinician")
    response = client.post(
        "/v1/assessments",
        json={"client_id": client_id, "form_id": "whole_person_initial", "form_version": "v2.6", "payload": payload},
    )
    assert response.status_code == 201, response.text
    return response.json()


def bring_to(act, state: str, flags: list[str] | None = None) -> str:
    aid = new_assessment(act)["id"]
    if state == "draft":
        return aid
    act(AUTHOR, "clinician")
    assert client.post(f"/v1/assessments/{aid}/submit", json={"safety_flags": flags or []}).status_code == 200
    if state == "submitted":
        return aid
    act(REV1, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 200
    if state == "in_review":
        return aid
    if state == "returned":
        assert client.post(f"/v1/assessments/{aid}/return", json={"reason": "Synthetic return reason."}).status_code == 200
        return aid
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)}).status_code == 200
    return aid


def state_of(act, aid: str) -> str:
    act(AUTHOR, "clinician")
    return client.get(f"/v1/assessments/{aid}").json()["state"]


# --------------------------------------------------------------------------- happy paths


def test_create_submit_review_sign_off(backend, act):
    created = new_assessment(act)
    aid = created["id"]
    assert created["state"] == "draft" and created["version"] == 1 and created["revision"] == 1

    act(AUTHOR, "clinician")
    submitted = client.post(f"/v1/assessments/{aid}/submit", json={}).json()
    assert submitted["state"] == "submitted"
    assert submitted["content_hash"] == sha(PAYLOAD)

    act(REV1, "reviewer")
    queue = client.get("/v1/review-queue").json()
    item = next(q for q in queue if q["id"] == aid)
    assert "payload" not in item and item["unacknowledged_safety_flags"] == 0
    assert client.get(f"/v1/assessments/{aid}").status_code == 404, "unclaimed work is not readable"

    assert client.post(f"/v1/assessments/{aid}/start-review").json()["reviewer_sub"] == REV1
    assert client.get(f"/v1/assessments/{aid}").json()["payload"] == PAYLOAD

    signed = client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)}).json()
    assert signed["state"] == "signed_off"
    assert signed["signed_off_by"] == REV1 and signed["signed_off_at"]
    assert signed["content_hash"] == sha(PAYLOAD)


def test_return_reopen_edit_and_resubmit(backend, act):
    aid = bring_to(act, "returned")
    act(AUTHOR, "clinician")
    record = client.get(f"/v1/assessments/{aid}").json()
    assert record["state"] == "returned" and record["note"] == "Synthetic return reason."

    assert client.post(f"/v1/assessments/{aid}/reopen").json()["state"] == "draft"
    revised = {"items": {"synthetic_item_1": "revised"}}
    edited = client.put(f"/v1/assessments/{aid}", json={"payload": revised, "revision": record["revision"]})
    assert edited.status_code == 200 and edited.json()["revision"] == record["revision"] + 1

    resubmitted = client.post(f"/v1/assessments/{aid}/submit", json={}).json()
    assert resubmitted["submission"] == 2 and resubmitted["content_hash"] == sha(revised)
    assert resubmitted["reviewer_sub"] is None

    act(REV2, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 200
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(revised)}).status_code == 200


# --------------------------------------------------------------------------- transition matrix

ALLOWED = {("draft", "submit"), ("submitted", "start_review"), ("in_review", "return"),
           ("in_review", "sign_off"), ("returned", "reopen"), ("draft", "edit")}


def attempt(act, aid: str, action: str):
    if action in ("submit", "reopen", "edit"):
        act(AUTHOR, "clinician")
        if action == "edit":
            revision = client.get(f"/v1/assessments/{aid}").json()["revision"]
            return client.put(f"/v1/assessments/{aid}", json={"payload": {"x": 1}, "revision": revision})
        return client.post(f"/v1/assessments/{aid}/{action}", json={})
    act(REV1, "reviewer")
    if action == "start_review":
        return client.post(f"/v1/assessments/{aid}/start-review")
    if action == "return":
        return client.post(f"/v1/assessments/{aid}/return", json={"reason": "Synthetic."})
    return client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)})


FORBIDDEN = [(s, a) for s in STATES for a in ("submit", "start_review", "return", "sign_off", "reopen", "edit")
             if (s, a) not in ALLOWED]


@pytest.mark.parametrize(("state", "action"), FORBIDDEN)
def test_forbidden_transitions_are_rejected_and_change_nothing(backend, act, state, action):
    aid = bring_to(act, state)
    response = attempt(act, aid, action)
    # Reviewer actions on work the reviewer does not hold are invisible (404); everything else is 409.
    not_held = action in ("return", "sign_off") and state in ("draft", "submitted")
    assert response.status_code == (404 if not_held else 409), (state, action, response.text)
    assert state_of(act, aid) == state


def test_allowed_transition_table_matches_service():
    from app import assessments

    assert set(assessments.TRANSITIONS) == {
        ("draft", "submitted"), ("submitted", "in_review"), ("in_review", "returned"),
        ("in_review", "signed_off"), ("returned", "draft"),
    }


# --------------------------------------------------------------------------- separation of duties


def test_author_cannot_start_review_of_own_work(backend, act):
    aid = new_assessment(act, owner=DUAL)["id"]
    act(DUAL, "clinician", "reviewer")
    assert client.post(f"/v1/assessments/{aid}/submit", json={}).status_code == 200
    assert all(q["id"] != aid for q in client.get("/v1/review-queue").json())
    response = client.post(f"/v1/assessments/{aid}/start-review")
    assert response.status_code == 403
    assert state_of_dual(act, aid) == "submitted"


def state_of_dual(act, aid: str) -> str:
    act(DUAL, "clinician", "reviewer")
    return client.get(f"/v1/assessments/{aid}").json()["state"]


def test_self_sign_off_refused_even_if_reviewer_slot_is_forced(backend, act, raw):
    aid = new_assessment(act, owner=DUAL)["id"]
    act(DUAL, "clinician", "reviewer")
    client.post(f"/v1/assessments/{aid}/submit", json={})
    raw("UPDATE assessments SET state = 'in_review', reviewer_sub = ? WHERE id = ?", (DUAL, aid))
    response = client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)})
    assert response.status_code == 403
    assert state_of_dual(act, aid) == "in_review"


def test_only_the_assigned_reviewer_can_read_return_or_sign_off(backend, act):
    aid = bring_to(act, "in_review")
    act(REV2, "reviewer")
    assert client.get(f"/v1/assessments/{aid}").status_code == 404
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)}).status_code == 404
    assert client.post(f"/v1/assessments/{aid}/return", json={"reason": "x"}).status_code == 404
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 409
    assert state_of(act, aid) == "in_review"


def test_sign_off_requires_the_reviewed_hash(backend, act):
    aid = bring_to(act, "in_review")
    act(REV1, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": "0" * 64}).status_code == 409
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": "not-a-hash"}).status_code == 422
    assert client.post(f"/v1/assessments/{aid}/return", json={"reason": "   "}).status_code == 422
    assert state_of(act, aid) == "in_review"


# --------------------------------------------------------------------------- immutability and versions


def test_signed_off_record_is_immutable_in_api_and_database(backend, act, raw):
    aid = bring_to(act, "signed_off")
    act(AUTHOR, "clinician")
    assert client.put(f"/v1/assessments/{aid}", json={"payload": {"x": 1}, "revision": 1}).status_code == 409
    with pytest.raises(Exception, match="immutable"):
        raw("UPDATE assessments SET form_version = 'tampered' WHERE id = ?", (aid,))
    with pytest.raises(Exception, match="cannot be deleted"):
        raw("DELETE FROM assessments WHERE id = ?", (aid,))
    record = client.get(f"/v1/assessments/{aid}").json()
    assert record["state"] == "signed_off" and record["payload"] == PAYLOAD and record["form_version"] == "v2.6"


def test_amendment_creates_a_new_version_and_leaves_original_unchanged(backend, act):
    aid = bring_to(act, "signed_off")
    act(AUTHOR, "clinician")
    amended_payload = {"items": {"synthetic_item_1": "amended"}}
    response = client.post(f"/v1/assessments/{aid}/amendments",
                           json={"payload": amended_payload, "reason": "Synthetic correction."})
    assert response.status_code == 201
    new = response.json()
    assert new["version"] == 2 and new["parent_id"] == aid and new["state"] == "draft"
    assert client.get(f"/v1/assessments/{new['id']}").json()["note"] == "Synthetic correction."

    original = client.get(f"/v1/assessments/{aid}").json()
    assert original["state"] == "signed_off" and original["payload"] == PAYLOAD
    assert original["content_hash"] == sha(PAYLOAD)

    again = client.post(f"/v1/assessments/{aid}/amendments", json={"payload": {}, "reason": "Second."})
    assert again.status_code == 409, "only the latest version can be amended"
    draft = client.post(f"/v1/assessments/{new['id']}/amendments", json={"payload": {}, "reason": "x"})
    assert draft.status_code == 409, "drafts are edited, not amended"

    listed = client.get(f"/v1/clients/{original['client_id']}/assessments").json()
    assert [a["version"] for a in listed] == [1, 2]


def test_stale_revision_is_rejected(backend, act):
    aid = new_assessment(act)["id"]
    act(AUTHOR, "clinician")
    assert client.put(f"/v1/assessments/{aid}", json={"payload": {"a": 1}, "revision": 1}).status_code == 200
    stale = client.put(f"/v1/assessments/{aid}", json={"payload": {"a": 2}, "revision": 1})
    assert stale.status_code == 409
    assert client.get(f"/v1/assessments/{aid}").json()["payload"] == {"a": 1}


# --------------------------------------------------------------------------- safety flags


def test_unacknowledged_safety_flags_block_review(backend, act):
    aid = bring_to(act, "submitted", flags=["synthetic_flag_b", "synthetic_flag_a"])
    act(REV1, "reviewer")
    assert next(q for q in client.get("/v1/review-queue").json() if q["id"] == aid)["unacknowledged_safety_flags"] == 2
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 409

    flags = client.get(f"/v1/assessments/{aid}/safety-flags").json()
    assert [f["code"] for f in flags] == ["synthetic_flag_a", "synthetic_flag_b"]
    assert all(f["acknowledged_by"] is None for f in flags)

    first = client.post(f"/v1/assessments/{aid}/safety-flags/{flags[0]['id']}/acknowledge")
    assert first.status_code == 200 and first.json()["acknowledged_by"] == REV1 and first.json()["acknowledged_at"]
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 409, "one flag still open"
    assert client.post(f"/v1/assessments/{aid}/safety-flags/{flags[0]['id']}/acknowledge").status_code == 409

    act(AUTHOR, "clinician")
    second = client.post(f"/v1/assessments/{aid}/safety-flags/{flags[1]['id']}/acknowledge")
    assert second.status_code == 200 and second.json()["acknowledged_by"] == AUTHOR

    act(REV1, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 200


def test_flags_apply_per_submission(backend, act):
    aid = bring_to(act, "returned")
    act(AUTHOR, "clinician")
    client.post(f"/v1/assessments/{aid}/reopen")
    client.post(f"/v1/assessments/{aid}/submit", json={"safety_flags": ["synthetic_flag_new"]})
    act(REV2, "reviewer")
    assert client.post(f"/v1/assessments/{aid}/start-review").status_code == 409
    flags = client.get(f"/v1/assessments/{aid}/safety-flags").json()
    assert [f["code"] for f in flags] == ["synthetic_flag_new"]


def test_flag_validation_and_unknown_ids(backend, act):
    aid = new_assessment(act)["id"]
    act(AUTHOR, "clinician")
    assert client.post(f"/v1/assessments/{aid}/submit", json={"safety_flags": ["bad code!"]}).status_code == 422
    assert client.post(f"/v1/assessments/{aid}/submit", json={"safety_flags": "x"}).status_code == 422
    assert state_of(act, aid) == "draft"
    client.post(f"/v1/assessments/{aid}/submit", json={"safety_flags": ["synthetic_flag"]})
    assert client.post(f"/v1/assessments/{aid}/safety-flags/not-a-flag/acknowledge").status_code == 404


# --------------------------------------------------------------------------- visibility and roles


def test_other_clinicians_and_admins_cannot_see_records(backend, act):
    aid = new_assessment(act)["id"]
    act(OTHER_CLIN, "clinician")
    assert client.get(f"/v1/assessments/{aid}").status_code == 404
    assert client.get("/v1/assessments/00000000-0000-0000-0000-000000000000").status_code == 404
    act(ADMIN, "admin")
    assert client.get(f"/v1/assessments/{aid}").status_code == 403
    assert client.post("/v1/clients", json={"x": 1}).status_code == 403
    act(REV1, "reviewer")
    assert client.post("/v1/clients", json={"x": 1}).status_code == 403


def test_assessment_needs_a_client_the_author_owns(backend, act):
    client_id = new_client(act, AUTHOR)
    act(OTHER_CLIN, "clinician")
    response = client.post("/v1/assessments", json={
        "client_id": client_id, "form_id": "f", "form_version": "1", "payload": {}})
    assert response.status_code == 404
    assert client.get(f"/v1/clients/{client_id}/assessments").status_code == 404


def test_input_validation(backend, act):
    client_id = new_client(act)
    for body in (
        {"client_id": client_id, "form_id": "bad id", "form_version": "1", "payload": {}},
        {"client_id": client_id, "form_id": "f", "form_version": "1", "payload": []},
        {"form_id": "f", "form_version": "1", "payload": {}},
    ):
        assert client.post("/v1/assessments", json=body).status_code == 422, body


# --------------------------------------------------------------------------- encryption and audit


def test_payload_is_encrypted_at_rest(backend, act, raw):
    aid = new_assessment(act)["id"]
    blob = bytes(raw("SELECT ciphertext FROM assessments WHERE id = ?", (aid,))[0][0])
    assert MARKER.encode() not in blob


def test_swapped_ciphertext_between_assessments_is_detected(backend, act, raw):
    first = new_assessment(act)["id"]
    second = new_assessment(act, payload={"items": {"other": "synthetic"}})["id"]
    blob = bytes(raw("SELECT ciphertext FROM assessments WHERE id = ?", (first,))[0][0])
    raw("UPDATE assessments SET ciphertext = ? WHERE id = ?", (blob, second))
    act(AUTHOR, "clinician")
    assert client.get(f"/v1/assessments/{second}").status_code == 500


def test_admin_reads_audit_metadata_without_payloads(backend, act):
    aid = bring_to(act, "signed_off", flags=None)
    act(OTHER_CLIN, "clinician")
    client.get(f"/v1/assessments/{aid}")

    act(ADMIN, "admin")
    events = client.get("/v1/audit", params={"limit": 500}).json()
    actions = [(e["action"], e["outcome"]) for e in events if e["record_id"] == aid]
    for expected in [("assessment.create", "ok"), ("assessment.submit", "ok"), ("assessment.start_review", "ok"),
                     ("assessment.sign_off", "ok"), ("assessment.read", "denied_or_missing")]:
        assert expected in actions, expected
    flat = json.dumps(events)
    assert MARKER not in flat and "Synthetic return reason" not in flat
    assert client.get("/v1/audit/verify").json()["ok"] is True

    act(AUTHOR, "clinician")
    assert client.get("/v1/audit").status_code == 403


def test_audit_is_append_only_and_tampering_is_detected(backend, act, raw):
    bring_to(act, "submitted")
    with pytest.raises(Exception, match="append-only"):
        raw("UPDATE audit_events SET outcome = 'ok' WHERE id = 1")
    with pytest.raises(Exception, match="append-only"):
        raw("DELETE FROM audit_events WHERE id = 1")

    # Simulate a privileged attacker who bypasses the triggers, then edits history.
    if backend == "sqlite":
        raw("DROP TRIGGER audit_events_no_update")
    else:
        raw("ALTER TABLE audit_events DISABLE TRIGGER audit_events_append_only")
    raw("UPDATE audit_events SET actor_sub = 'someone-else' WHERE id = 2")

    act(ADMIN, "admin")
    result = client.get("/v1/audit/verify").json()
    assert result["ok"] is False and result["first_broken_event_id"] == 2


def test_denials_are_audited(backend, act):
    aid = new_assessment(act)["id"]
    act(OTHER_CLIN, "clinician")
    client.get(f"/v1/assessments/{aid}")
    client.post(f"/v1/assessments/{aid}/submit", json={})
    act(ADMIN, "admin")
    events = [e for e in client.get("/v1/audit", params={"limit": 500}).json() if e["record_id"] == aid]
    denied = [(e["actor_sub"], e["action"]) for e in events if e["outcome"] == "denied_or_missing"]
    assert (OTHER_CLIN, "assessment.read") in denied and (OTHER_CLIN, "assessment.submit") in denied


# --------------------------------------------------------------------------- fail closed


def test_missing_database_fails_closed(act, monkeypatch, tmp_path):
    monkeypatch.delenv("STN_DATA_DB", raising=False)
    monkeypatch.delenv("STN_DATABASE_URL", raising=False)
    act(AUTHOR, "clinician")
    response = client.post("/v1/assessments", json={"client_id": "x", "form_id": "f", "form_version": "1", "payload": {}})
    assert response.status_code == 503


def test_missing_key_fails_closed(backend, act, monkeypatch):
    client_id = new_client(act)
    monkeypatch.delenv("STN_DATA_KEY")
    act(AUTHOR, "clinician")
    response = client.post("/v1/assessments", json={"client_id": client_id, "form_id": "f", "form_version": "1", "payload": {}})
    assert response.status_code == 503


def test_postgres_url_without_driver_fails_closed(act, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_psycopg(name, *args, **kwargs):
        if name.startswith("psycopg"):
            raise ImportError("psycopg hidden for this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setenv("STN_DATABASE_URL", "postgresql://synthetic@127.0.0.1:1/none")
    monkeypatch.setattr(builtins, "__import__", no_psycopg)
    act(AUTHOR, "clinician")
    assert client.get("/v1/clients/00000000-0000-0000-0000-000000000000").status_code == 503
