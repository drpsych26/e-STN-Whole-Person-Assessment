"""Clinician registration, attestation reference validation (D-08) and clinical-access enforcement.

Synthetic data only. These tests cover what the platform records and enforces; they do not and
cannot verify anyone's registration with a real authority.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

CLIN, REV, ADMIN, CLIN_ADMIN = "clin-reg-1", "rev-reg-1", "admin-reg-1", "clin-admin-reg-1"
NEXT_YEAR = (date.today() + timedelta(days=365)).isoformat()
TODAY = date.today().isoformat()
REG = {"authority": "nz_psychologists_board", "registration_number": "SYN-00001", "scope_code": "clinical_psychologist",
       "expires_on": NEXT_YEAR}
ATTEST = {"source_url": "https://register.synthetic.test/entry/SYN-00001", "checked_on": TODAY}


@pytest.fixture
def enforced(monkeypatch):
    monkeypatch.setenv("STN_REQUIRE_VERIFIED_REGISTRATION", "true")
    monkeypatch.setenv("STN_REGISTER_HOSTS", "register.synthetic.test")  # explicit synthetic host


def submit(act, who=CLIN, role="clinician", body=REG):
    act(who, role)
    return client.post("/v1/me/clinician-registration", json=body)


def attest(act, reg_id, who=ADMIN, body=ATTEST, *roles):
    act(who, *(roles or ("admin",)))
    return client.post(f"/v1/admin/clinician-registrations/{reg_id}/attest", json=body)


def test_unverified_clinicians_have_no_clinical_access_when_enforced(backend, act, enforced):
    act(CLIN, "clinician")
    assert client.post("/v1/clients", json={"display_code": "SYN-R"}).status_code == 403
    r = submit(act)
    assert r.status_code == 201 and r.json()["verified"] is False and r.json()["reason"] == "awaiting_attestation"
    act(CLIN, "clinician")
    assert client.post("/v1/clients", json={"display_code": "SYN-R"}).status_code == 403  # a declaration grants nothing
    ok = attest(act, r.json()["registration"]["id"])
    assert ok.status_code == 201 and ok.json()["verified"] is True
    act(CLIN, "clinician")
    assert client.post("/v1/clients", json={"display_code": "SYN-R"}).status_code == 201
    act(ADMIN, "admin")  # admin-only routes never needed a registration
    assert client.get("/v1/admin/clinician-registrations").status_code == 200


def test_reviewers_are_enforced_too_and_admin_role_is_not_clinical_authority(backend, act, enforced):
    act(REV, "reviewer")
    assert client.get("/v1/review-queue").status_code == 403
    reg_id = submit(act, REV, "reviewer").json()["registration"]["id"]
    attest(act, reg_id)
    act(REV, "reviewer")
    assert client.get("/v1/review-queue").status_code == 200
    act(CLIN_ADMIN, "clinician", "admin")
    assert client.post("/v1/clients", json={"display_code": "SYN-R"}).status_code == 403  # clinician route, unverified
    assert client.get("/v1/admin/clinician-registrations").status_code == 200  # admin route still works


def test_attestation_reference_validation(backend, act, enforced, monkeypatch):
    reg_id = submit(act).json()["registration"]["id"]
    assert attest(act, "no-such-registration").status_code == 404
    act("admin-other-org", "admin", org="org-synthetic-2")
    assert client.post(f"/v1/admin/clinician-registrations/{reg_id}/attest", json=ATTEST).status_code == 404
    assert attest(act, reg_id, body={**ATTEST, "source_url": "http://register.synthetic.test/x"}).status_code == 422
    assert attest(act, reg_id, body={**ATTEST, "source_url": "javascript:alert(1)"}).status_code == 422
    future = (date.today() + timedelta(days=1)).isoformat()
    stale = (date.today() - timedelta(days=31)).isoformat()
    assert attest(act, reg_id, body={**ATTEST, "checked_on": future}).status_code == 422
    assert attest(act, reg_id, body={**ATTEST, "checked_on": stale}).status_code == 422
    monkeypatch.setenv("STN_REGISTER_HOSTS", "register.approved.test")
    assert attest(act, reg_id).status_code == 422
    monkeypatch.setenv("STN_REGISTER_HOSTS", "register.synthetic.test")
    assert attest(act, reg_id, body={**ATTEST, "source_url": "https://evil.register.synthetic.test/x"}).status_code == 422
    assert attest(act, reg_id, body={**ATTEST, "source_url": "https://register.synthetic.test.evil.test/x"}).status_code == 422
    newer = submit(act, body={**REG, "registration_number": "SYN-00002"}).json()["registration"]["id"]
    assert attest(act, reg_id).status_code == 409  # superseded by a newer submission
    assert attest(act, newer).status_code == 201
    assert attest(act, newer).status_code == 409  # already attested


def test_self_attestation_is_refused(backend, act, enforced, raw):
    reg_id = submit(act, CLIN_ADMIN, "clinician").json()["registration"]["id"]
    r = attest(act, reg_id, CLIN_ADMIN, ATTEST, "clinician", "admin")
    assert r.status_code == 403
    with pytest.raises(Exception):  # and the schema refuses it even if the code did not
        raw("INSERT INTO attestations (id, org_id, kind, reference_type, reference_id, subject, source_url, checked_on, "
            "attested_by, attested_at) VALUES ('x', 'org-synthetic-1', 'registration_verified', 'clinician_registration', "
            "?, ?, 'https://r.test', ?, ?, ?)", (reg_id, CLIN_ADMIN, TODAY, CLIN_ADMIN, TODAY))


def test_revocation_and_expiry_remove_clinical_access(backend, act, enforced, raw):
    reg_id = submit(act).json()["registration"]["id"]
    att = attest(act, reg_id).json()["attestation"]["id"]
    act(CLIN, "clinician")
    assert client.post("/v1/clients", json={"display_code": "SYN-R"}).status_code == 201
    act(ADMIN, "admin")
    assert client.post(f"/v1/admin/attestations/{att}/revoke").json()["verified"] is False
    assert client.post(f"/v1/admin/attestations/{att}/revoke").status_code == 409
    act(CLIN, "clinician")
    assert client.post("/v1/clients", json={"display_code": "SYN-R"}).status_code == 403
    with pytest.raises(Exception):
        raw("UPDATE attestations SET revoked_at = NULL WHERE id = ?", (att,))
    with pytest.raises(Exception):
        raw("UPDATE clinician_registrations SET expires_on = '2099-01-01' WHERE id = ?", (reg_id,))


def test_submission_validation(backend, act):
    assert submit(act, body={**REG, "expires_on": "2020-01-01"}).status_code == 422
    assert submit(act, body={**REG, "authority": "Psychologists Board!"}).status_code == 422
    assert submit(act, body={**REG, "registration_number": "x" * 40}).status_code == 422
    act(ADMIN, "admin")
    assert client.post("/v1/me/clinician-registration", json=REG).status_code == 403
    act("client-subj-x", "client")
    assert client.post("/v1/me/clinician-registration", json=REG).status_code == 403


def test_enforcement_defaults_follow_the_environment(backend, act, monkeypatch):
    act(CLIN, "clinician")
    assert client.post("/v1/clients", json={"display_code": "SYN-R"}).status_code == 201  # local default: off
    from app import clinician_registry, db
    monkeypatch.setenv(db.ENVIRONMENT_ENV, "production")
    assert clinician_registry.enforcement_required() is True
    monkeypatch.setenv("STN_REQUIRE_VERIFIED_REGISTRATION", "false")
    assert clinician_registry.enforcement_required() is False


@pytest.mark.parametrize("env", [{"STN_REQUIRE_VERIFIED_REGISTRATION": "true"}, {"STN_ENVIRONMENT": "production"},
                                 {"STN_ENVIRONMENT": "staging"}])
def test_missing_host_list_fails_closed_when_enforced_or_hosted(backend, act, monkeypatch, env):
    monkeypatch.delenv("STN_REGISTER_HOSTS", raising=False)
    reg_id = submit(act).json()["registration"]["id"]
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    if "STN_ENVIRONMENT" in env:  # hosted environments refuse SQLite; exercise the registry rule directly
        from app import clinician_registry
        with pytest.raises(clinician_registry.RegistryNotConfigured):
            clinician_registry.attest(ADMIN, "org-synthetic-1", reg_id, ATTEST)
        return
    r = attest(act, reg_id)
    assert r.status_code == 503 and "STN_REGISTER_HOSTS" in r.json()["detail"]
    monkeypatch.setenv("STN_REGISTER_HOSTS", " , ")  # blank entries count as empty
    assert attest(act, reg_id).status_code == 503
    monkeypatch.setenv("STN_REGISTER_HOSTS", "register.synthetic.test")
    assert attest(act, reg_id).status_code == 201  # exact approved host accepted
