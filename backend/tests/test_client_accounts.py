"""Client accounts: invitation, claim, verification, acknowledgement, activation, status and isolation.

Synthetic data and synthetic identity-provider events only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.idp_fixtures import idp  # noqa: F401

client = TestClient(app, raise_server_exceptions=False)

OWNER, OTHER_CLIN, ADMIN, ADMIN2 = "clin-ca-owner", "clin-ca-other", "admin-ca", "admin-ca-2"
ALICE, BOB = "client-subj-alice", "client-subj-bob"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer"}}


@pytest.fixture
def versions(monkeypatch):
    monkeypatch.setenv("STN_TERMS_VERSION", "terms-2026-11")
    monkeypatch.setenv("STN_PRIVACY_NOTICE_VERSION", "privacy-2026-11")
    monkeypatch.setenv("STN_CONSENT_VERSION", "consent-2026-11")


def new_client(act, owner=OWNER, code="SYN-CA") -> str:
    act(owner, "clinician")
    cid = client.post("/v1/clients", json={"display_code": code}).json()["id"]
    client.post("/v1/assessments", json={"client_id": cid, "form_id": "whole_person_initial",
                                         "form_version": "v2.6", "payload": PAYLOAD})
    return cid


def invite(act, cid, owner=OWNER):
    act(owner, "clinician")
    return client.post(f"/v1/clients/{cid}/client-account/invitation")


def claim(act, subject, code, org=None):
    if org:
        act(subject, "client", org=org)
    else:
        act(subject, "client")
    return client.post("/v1/me/client-invitation/claim", json={"code": code})


def complete_requirements(act, idp, subject):
    for kind in ("email_verified", "mfa_enrolled"):
        assert client.post("/v1/identity/events", json={"event": idp(subject, kind)}).status_code == 202
    act(subject, "client")
    for kind, version in (("terms", "terms-2026-11"), ("privacy_notice", "privacy-2026-11"), ("consent", "consent-2026-11")):
        assert client.post("/v1/me/client-acknowledgements", json={"kind": kind, "version": version}).status_code == 201


def onboard(act, idp, subject=ALICE, owner=OWNER, code="SYN-CA") -> str:
    cid = new_client(act, owner, code)
    inv = invite(act, cid, owner).json()
    assert claim(act, subject, inv["invitation_code"]).status_code == 200
    complete_requirements(act, idp, subject)
    act(owner, "clinician")
    assert client.post(f"/v1/clients/{cid}/client-account/activate").status_code == 200
    return cid


def test_full_onboarding_journey(backend, act, idp, versions):
    cid = new_client(act)
    inv = invite(act, cid)
    assert inv.status_code == 201 and len(inv.json()["invitation_code"]) >= 40

    r = claim(act, ALICE, inv.json()["invitation_code"])
    assert r.status_code == 200 and r.json()["status"] == "provisional"
    assert "identity:email" in r.json()["outstanding_requirements"]

    # Provisional: own status only, no clinical information.
    assert client.get("/v1/me/client-account").status_code == 200
    assert client.get("/v1/me/client-assessments").status_code == 403

    act(OWNER, "clinician")
    early = client.post(f"/v1/clients/{cid}/client-account/activate")
    assert early.status_code == 422 and "identity:mfa" in early.json()["detail"]["missing"]

    complete_requirements(act, idp, ALICE)
    act(OWNER, "clinician")
    done = client.post(f"/v1/clients/{cid}/client-account/activate")
    assert done.status_code == 200 and done.json()["status"] == "active" and done.json()["outstanding_requirements"] == []

    act(ALICE, "client")
    own = client.get("/v1/me/client-assessments")
    assert own.status_code == 200 and len(own.json()) == 1
    assert set(own.json()[0]) == {"id", "form_id", "form_version", "state", "created_at", "updated_at"}  # no payload


def test_clients_only_see_their_own_records(backend, act, idp, versions):
    alice_cid = onboard(act, idp, ALICE, code="SYN-A")
    bob_cid = onboard(act, idp, BOB, code="SYN-B")
    act(BOB, "client")
    bob = client.get("/v1/me/client-assessments").json()
    act(ALICE, "client")
    alice = client.get("/v1/me/client-assessments").json()
    assert {a["id"] for a in alice}.isdisjoint({b["id"] for b in bob})
    # Identifier manipulation: staff routes that take ids are closed to the client role.
    for path in (f"/v1/clients/{bob_cid}", f"/v1/clients/{alice_cid}", f"/v1/assessments/{bob[0]['id']}",
                 f"/v1/clients/{bob_cid}/client-account", "/v1/audit", f"/v1/safety-escalations/by-client/{bob_cid}"):
        assert client.get(path).status_code == 403, path
    assert client.get("/v1/me/client-assessments", params={"client_id": bob_cid}).json() == alice


def test_client_and_staff_roles_cannot_be_combined(backend, act, idp, versions):
    onboard(act, idp)
    act(ALICE, "client", "clinician")
    assert client.get("/v1/me/client-account").status_code == 403
    assert client.post("/v1/clients", json={"display_code": "X"}).status_code == 403


def test_invitation_codes_are_single_use_expiring_and_org_bound(backend, act, idp, versions, raw):
    cid = new_client(act)
    first = invite(act, cid).json()["invitation_code"]
    second = invite(act, cid).json()["invitation_code"]  # reissue: the first stops working
    assert claim(act, ALICE, first).status_code == 404
    assert claim(act, ALICE, second, org="org-synthetic-2").status_code == 404  # other organisation
    assert claim(act, ALICE, "x" * 43).status_code == 404
    assert claim(act, ALICE, "short").status_code == 404
    assert claim(act, ALICE, second).status_code == 200
    assert claim(act, BOB, second).status_code == 404  # used
    other = new_client(act, code="SYN-OTHER")
    third = invite(act, other).json()["invitation_code"]
    assert claim(act, ALICE, third).status_code == 409  # one client account per sign-in per organisation
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    raw("UPDATE client_accounts SET invite_expires_at = ? WHERE client_id = ?", (past, other))
    assert claim(act, BOB, third).status_code == 404  # expired
    act(OWNER, "clinician")
    assert client.post(f"/v1/clients/{cid}/client-account/invitation").status_code == 409  # already claimed


def test_only_the_owning_clinician_invites_and_activates(backend, act, idp, versions):
    cid = new_client(act)
    assert invite(act, cid, OTHER_CLIN).status_code == 404
    code = invite(act, cid).json()["invitation_code"]
    claim(act, ALICE, code)
    complete_requirements(act, idp, ALICE)
    act(OTHER_CLIN, "clinician")
    assert client.post(f"/v1/clients/{cid}/client-account/activate").status_code == 404
    act(ADMIN, "admin")
    assert client.post(f"/v1/clients/{cid}/client-account/activate").status_code == 403  # admin is not clinical authority
    view = client.get(f"/v1/clients/{cid}/client-account")
    assert view.status_code == 200 and view.json()["claimed"] is True and "subject" not in view.json()
    act("admin-other-org", "admin", org="org-synthetic-2")
    assert client.get(f"/v1/clients/{cid}/client-account").status_code == 404


def test_acknowledgements_need_current_versions_and_configuration(backend, act, idp, versions, monkeypatch):
    cid = new_client(act)
    claim(act, ALICE, invite(act, cid).json()["invitation_code"])
    act(ALICE, "client")
    assert client.post("/v1/me/client-acknowledgements", json={"kind": "terms", "version": "terms-2020"}).status_code == 422
    assert client.post("/v1/me/client-acknowledgements", json={"kind": "medical", "version": "x"}).status_code == 422
    assert client.post("/v1/me/client-acknowledgements",
                       json={"kind": "terms", "version": "terms-2026-11"}).status_code == 201
    assert client.post("/v1/me/client-acknowledgements",
                       json={"kind": "terms", "version": "terms-2026-11"}).status_code == 201  # idempotent
    complete_requirements(act, idp, ALICE)
    monkeypatch.setenv("STN_TERMS_VERSION", "terms-2027-01")  # new terms: must acknowledge again
    act(OWNER, "clinician")
    r = client.post(f"/v1/clients/{cid}/client-account/activate")
    assert r.status_code == 422 and r.json()["detail"]["missing"] == ["acknowledgement:terms"]
    monkeypatch.delenv("STN_CONSENT_VERSION")
    assert client.post(f"/v1/clients/{cid}/client-account/activate").status_code == 503


def test_suspend_reactivate_deactivate(backend, act, idp, versions, raw):
    cid = onboard(act, idp)
    act(ADMIN, "admin")
    assert client.post(f"/v1/admin/client-accounts/{cid}/suspend", json={}).status_code == 422  # reason required
    assert client.post(f"/v1/admin/client-accounts/{cid}/suspend", json={"reason_code": "client_request"}).json()["status"] == "suspended"
    act(ALICE, "client")
    assert client.get("/v1/me/client-account").status_code == 403
    assert client.get("/v1/me/client-assessments").status_code == 403
    act(ADMIN, "admin")
    assert client.post(f"/v1/admin/client-accounts/{cid}/reactivate", json={}).json()["status"] == "active"
    assert client.post(f"/v1/admin/client-accounts/{cid}/deactivate", json={"reason_code": "service_ended"}).json()["status"] == "deactivated"
    assert client.post(f"/v1/admin/client-accounts/{cid}/reactivate", json={}).status_code == 409
    act(ALICE, "client")
    assert client.get("/v1/me/client-account").status_code == 403
    with pytest.raises(Exception):
        raw("UPDATE client_accounts SET status = 'active' WHERE client_id = ?", (cid,))
    with pytest.raises(Exception):
        raw("DELETE FROM client_accounts WHERE client_id = ?", (cid,))


def test_unlinked_client_sign_in_gets_nothing(backend, act, versions):
    act("client-never-invited", "client")
    assert client.get("/v1/me/client-account").status_code == 403
    assert client.get("/v1/me/client-assessments").status_code == 403


def test_onboarding_is_audited_without_codes(backend, act, idp, versions, raw):
    cid = onboard(act, idp)
    rows = raw("SELECT action, outcome FROM audit_events WHERE record_id = ? ORDER BY id", (cid,))
    actions = [r[0] for r in rows]
    for expected in ("client_account.invite", "client_account.claim", "client_account.activate"):
        assert expected in actions
    blob = " ".join(str(c) for r in raw("SELECT * FROM audit_events") for c in r)
    stored_hash = raw("SELECT invite_code_sha256 FROM client_accounts WHERE client_id = ?", (cid,))[0][0]
    assert stored_hash is None  # cleared on claim
    assert "invitation_code" not in blob
