"""RBAC, audit chain and onboarding state machine tests. Synthetic identifiers only."""
from __future__ import annotations

import base64
import secrets
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import audit, auth, onboarding, rbac, store
from app.main import app
from app.rbac import PermissionDenied, Role

ADMIN = "platform-admin-1"
CLINICIAN = "clinician-1"
INTAKE = "intake-1"
AUDITOR = "auditor-1"
CUSTOMER = "customer-1"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv(store.DB_ENV, str(tmp_path / "platform.sqlite3"))
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    rbac.grant_system_role(ADMIN, Role.PLATFORM_ADMINISTRATOR)
    rbac.grant_system_role(INTAKE, Role.INTAKE_COORDINATOR)
    rbac.grant_system_role(AUDITOR, Role.AUDITOR)
    return tmp_path


@pytest.fixture
def as_user(monkeypatch):
    current = {"sub": ADMIN}
    app.dependency_overrides[auth.require_identity] = lambda: {"sub": current["sub"]}

    def switch(sub: str) -> None:
        current["sub"] = sub

    yield switch
    app.dependency_overrides.pop(auth.require_identity, None)


client = TestClient(app)


# ---------- RBAC ----------

def test_permissions_union_from_roles():
    perms = rbac.permissions_for([Role.CUSTOMER, Role.AUDITOR])
    assert {"customer:read_own", "audit:read"} <= perms
    assert "clinical:read_assigned" not in perms


def test_roles_read_from_database_only(env):
    with store._connect() as conn:
        assert rbac.roles_for(conn, "nobody") == frozenset()


def test_clinical_director_cannot_read_client_records_directly(env):
    rbac.grant_system_role("director-1", Role.CLINICAL_DIRECTOR)
    with store._connect() as conn:
        perms = rbac.permissions_for(rbac.roles_for(conn, "director-1"))
    assert "clinical:read_assigned" not in perms and "clinical:governance" in perms


def test_only_platform_admin_can_grant_roles(env):
    with pytest.raises(PermissionDenied):
        rbac.grant_role(INTAKE, "someone", Role.CLINICAL_SUPERVISOR)
    assert rbac.grant_role(ADMIN, "someone", Role.CLINICAL_SUPERVISOR) is True


def test_denied_grant_is_audited(env):
    with pytest.raises(PermissionDenied):
        rbac.grant_role(INTAKE, "someone", Role.CLINICAL_SUPERVISOR)
    actions = [e["action"] for e in _audit_rows()]
    assert "rbac.denied" in actions


def test_revoke_removes_access(env):
    rbac.grant_role(ADMIN, "temp-1", Role.AUTHORISED_CLINICIAN)
    assert rbac.revoke_role(ADMIN, "temp-1", Role.AUTHORISED_CLINICIAN) is True
    with store._connect() as conn:
        assert rbac.roles_for(conn, "temp-1") == frozenset()


def test_admin_route_requires_grant_permission(env, as_user):
    as_user(INTAKE)
    assert client.post("/v1/admin/roles", json={"subject": "x", "role": "auditor"}).status_code == 403
    as_user(ADMIN)
    assert client.post("/v1/admin/roles", json={"subject": "x", "role": "auditor"}).status_code == 201
    assert client.post("/v1/admin/roles", json={"subject": "x", "role": "root"}).status_code == 422


def test_access_denial_is_audited_on_routes(env, as_user):
    as_user(CUSTOMER)
    assert client.post("/v1/onboarding/any/advance", json={"to_stage": "contact_verified"}).status_code == 403
    assert "access.denied" in [e["action"] for e in _audit_rows()]


def test_permission_checks_fail_closed_without_database(monkeypatch, as_user):
    monkeypatch.delenv(store.DB_ENV, raising=False)
    as_user(ADMIN)
    assert client.post("/v1/admin/roles", json={"subject": "x", "role": "auditor"}).status_code == 503


def test_unknown_permission_name_is_rejected_at_definition():
    with pytest.raises(ValueError, match="Unknown permission"):
        rbac.require_permission("clinical:delete_everything")


# ---------- Audit chain ----------

def _audit_rows():
    with store._connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM audit_chain ORDER BY seq")]


def test_audit_chain_verifies_when_intact(env):
    audit.append("a", "test.one", "case:1", {"stage": "x"})
    audit.append("a", "test.two", "case:1", {"stage": "y"})
    assert audit.verify() == (True, None)


def test_audit_rows_cannot_be_updated_or_deleted(env):
    audit.append("a", "test.one", "case:1", {})
    with store._connect() as conn:
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute("UPDATE audit_chain SET actor = 'mallory'")
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute("DELETE FROM audit_chain")


def test_tampering_is_detected_by_chain_verification(env):
    audit.append("a", "test.one", "case:1", {})
    audit.append("a", "test.two", "case:1", {})
    with store._connect() as conn:
        conn.execute("DROP TRIGGER audit_chain_no_update")
        conn.execute("UPDATE audit_chain SET actor = 'mallory' WHERE seq = 1")
    assert audit.verify() == (False, 1)


def test_audit_detail_is_stored_as_given(env):
    audit.append("a", "test.detail", "case:1", {"from": "registered", "to": "contact_verified"})
    row = _audit_rows()[-1]
    assert '"from":"registered"' in row["detail"]


# ---------- Onboarding ----------

def _full_path(case_id: str, actor: str = INTAKE):
    evidence = {
        "contact_verified": {"email_verified": True, "phone_verified": True},
        "account_active": {"mfa_enrolled": True, "terms_accepted": True},
        "privacy_acknowledged": {"privacy_notice_version": "2026-11"},
        "consented": {"consent_record_id": "consent-1"},
        "intake_eligible": {"eligibility_checked": True},
        "screened": {"screening_record_id": "screen-1"},
        "allocated": {"allocation_ref": "alloc-1"},
        "team_assigned": {"clinician_subject": CLINICIAN},
        "complete": {},
    }
    for stage in onboarding.STAGES[1:]:
        onboarding.advance(actor, case_id, stage, evidence[stage])


def test_registration_creates_customer_role_and_no_clinical_approval(env):
    case = onboarding.create_case(CUSTOMER)
    assert case["stage"] == "registered"
    with store._connect() as conn:
        assert Role.CUSTOMER in rbac.roles_for(conn, CUSTOMER)
        columns = [r["name"] for r in conn.execute("PRAGMA table_info(onboarding_cases)")]
    assert not any("approv" in c for c in columns)


def test_stages_cannot_be_skipped(env):
    case = onboarding.create_case(CUSTOMER)
    with pytest.raises(onboarding.InvalidTransition):
        onboarding.advance(INTAKE, case["id"], "consented", {"consent_record_id": "c"})


def test_missing_evidence_blocks_advance(env):
    case = onboarding.create_case(CUSTOMER)
    with pytest.raises(onboarding.MissingEvidence, match="email_verified"):
        onboarding.advance(INTAKE, case["id"], "contact_verified", {"phone_verified": True})


def test_full_onboarding_path_completes_in_order(env):
    case = onboarding.create_case(CUSTOMER)
    _full_path(case["id"])
    assert onboarding.get_case_for_subject(CUSTOMER)["stage"] == "complete"


def test_only_one_open_case_per_account(env):
    onboarding.create_case(CUSTOMER)
    with pytest.raises(onboarding.CaseAlreadyOpen):
        onboarding.create_case(CUSTOMER)


def test_suspended_case_cannot_advance(env):
    case = onboarding.create_case(CUSTOMER)
    onboarding.suspend(INTAKE, case["id"])
    with pytest.raises(onboarding.CaseSuspended):
        onboarding.advance(INTAKE, case["id"], "contact_verified",
                           {"email_verified": True, "phone_verified": True})


def test_unknown_case_is_not_found(env):
    with pytest.raises(onboarding.CaseNotFound):
        onboarding.advance(INTAKE, "missing", "contact_verified", {})


def test_every_transition_is_audited(env):
    case = onboarding.create_case(CUSTOMER)
    onboarding.advance(INTAKE, case["id"], "contact_verified",
                       {"email_verified": True, "phone_verified": True})
    actions = [e["action"] for e in _audit_rows()]
    assert actions.count("onboarding.advance") == 1
    assert audit.verify() == (True, None)


def test_customer_can_open_case_and_read_own_stage(env, as_user):
    as_user(CUSTOMER)
    created = client.post("/v1/onboarding")
    assert created.status_code == 201
    assert client.get("/v1/onboarding/me").json()["stage"] == "registered"


def test_intake_route_advances_and_enforces_permission(env, as_user):
    as_user(CUSTOMER)
    case_id = client.post("/v1/onboarding").json()["id"]
    assert client.post(f"/v1/onboarding/{case_id}/advance",
                       json={"to_stage": "contact_verified"}).status_code == 403
    as_user(INTAKE)
    response = client.post(f"/v1/onboarding/{case_id}/advance", json={
        "to_stage": "contact_verified",
        "evidence": {"email_verified": True, "phone_verified": True},
    })
    assert response.status_code == 200
    assert response.json()["stage"] == "contact_verified"
    assert client.post(f"/v1/onboarding/{case_id}/advance",
                       json={"to_stage": "consented"}).status_code == 409


def test_onboarding_open_requires_identity(env):
    assert client.post("/v1/onboarding").status_code == 401
