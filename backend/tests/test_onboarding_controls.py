"""Onboarding controls: signed verification events, versioned acknowledgements, separation of
duties, provisional restrictions and fail-closed authentication. Synthetic keys and identities."""
from __future__ import annotations

import base64
import secrets
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import audit, auth, onboarding, rbac, store, verification
from app.main import app
from app.rbac import ProvisionalRestriction, Role

ISSUER = "https://idp.example.test/"
AUDIENCE = "stn-api-test"
JWKS = "https://idp.example.test/.well-known/jwks.json"
ADMIN, INTAKE, SUPERVISOR, CLINICIAN, CUSTOMER = "admin-1", "intake-1", "supervisor-1", "clinician-1", "customer-1"

PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeJwks:
    def get_signing_key_from_jwt(self, token):
        class K:  # noqa: D401
            key = PRIVATE.public_key()
        return K()


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv(store.DB_ENV, str(tmp_path / "onb.sqlite3"))
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    monkeypatch.setenv("STN_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("STN_OIDC_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("STN_OIDC_JWKS_URL", JWKS)
    monkeypatch.setenv("STN_TERMS_VERSION", "terms-2026-11")
    monkeypatch.setenv("STN_PRIVACY_NOTICE_VERSION", "privacy-2026-11")
    monkeypatch.setenv("STN_CONSENT_VERSION", "consent-2026-11")
    monkeypatch.setattr(verification, "_jwks_client", lambda url: _FakeJwks())
    rbac.grant_system_role(ADMIN, Role.PLATFORM_ADMINISTRATOR)
    rbac.grant_system_role(INTAKE, Role.INTAKE_COORDINATOR)
    rbac.grant_system_role(SUPERVISOR, Role.CLINICAL_SUPERVISOR)
    rbac.grant_system_role(CLINICIAN, Role.AUTHORISED_CLINICIAN)
    return tmp_path


def event(kind: str, subject: str = CUSTOMER, jti: str | None = None, key=PRIVATE, **over) -> str:
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": subject, "jti": jti or secrets.token_hex(8),
              "iat": now, "exp": now + 600, "event": kind, "verified": True}
    claims.update(over)
    return jwt.encode(claims, key, algorithm="RS256")


def verify_all(subject: str = CUSTOMER) -> None:
    for kind in ("email_verified", "phone_verified", "mfa_enrolled"):
        verification.ingest_event(event(kind, subject))


def _full_customer_path(case_id: str) -> None:
    onboarding.advance(INTAKE, case_id, "contact_verified")
    onboarding.advance(INTAKE, case_id, "account_active")
    onboarding.advance(INTAKE, case_id, "privacy_acknowledged")
    onboarding.advance(INTAKE, case_id, "consented")


# ---------- signed verification events ----------

def test_valid_signed_event_records_verification(env):
    result = verification.ingest_event(event("email_verified"))
    assert result == {"subject": CUSTOMER, "kind": "email"}


def test_replayed_event_is_refused(env):
    token = event("email_verified", jti="evt-1")
    verification.ingest_event(token)
    with pytest.raises(verification.VerificationRejected, match="already been recorded"):
        verification.ingest_event(token)


def test_event_signed_by_other_key_is_refused(env):
    with pytest.raises(verification.VerificationRejected):
        verification.ingest_event(event("email_verified", key=OTHER_KEY))


def test_expired_or_wrong_audience_event_is_refused(env):
    with pytest.raises(verification.VerificationRejected):
        verification.ingest_event(event("email_verified", exp=int(time.time()) - 10))
    with pytest.raises(verification.VerificationRejected):
        verification.ingest_event(event("email_verified", aud="someone-else"))


def test_unknown_event_type_and_unverified_claim_are_refused(env):
    with pytest.raises(verification.VerificationRejected):
        verification.ingest_event(event("account_deleted"))
    with pytest.raises(verification.VerificationRejected):
        verification.ingest_event(event("email_verified", verified=False))


def test_event_without_configuration_fails_closed(env, monkeypatch):
    monkeypatch.delenv("STN_OIDC_JWKS_URL", raising=False)
    with pytest.raises(verification.VerificationNotConfigured):
        verification.ingest_event(event("email_verified"))


def test_event_webhook_route_rejects_unsigned_body(env):
    client = TestClient(app)
    assert client.post("/v1/verification/events", json={"event": "not-a-jwt"}).status_code == 401
    assert client.post("/v1/verification/events", json={}).status_code == 422


# ---------- caller-supplied flags are no longer accepted ----------

def test_intake_cannot_mark_verification_by_assertion(env):
    case = onboarding.create_case(CUSTOMER)
    with pytest.raises(onboarding.RequirementNotMet, match="email, phone"):
        onboarding.advance(INTAKE, case["id"], "contact_verified")


def test_advance_route_ignores_caller_evidence_and_requires_events(env):
    client = TestClient(app)
    case = onboarding.create_case(CUSTOMER)
    app.dependency_overrides[auth.require_identity] = lambda: {"sub": INTAKE}
    try:
        response = client.post(f"/v1/onboarding/{case['id']}/advance",
                               json={"to_stage": "contact_verified", "evidence": {"email_verified": True, "phone_verified": True}})
        assert response.status_code == 422
        assert "Identity provider" in response.json()["detail"]
        assert onboarding.get_case_for_subject(CUSTOMER)["stage"] == "registered"
    finally:
        app.dependency_overrides.pop(auth.require_identity, None)


# ---------- acknowledgements ----------

def test_acknowledgement_must_match_current_version(env):
    with pytest.raises(onboarding.RequirementNotMet, match="current published version"):
        onboarding.record_acknowledgement(CUSTOMER, "terms", "terms-old")


def test_missing_version_configuration_fails_closed(env, monkeypatch):
    monkeypatch.delenv("STN_CONSENT_VERSION", raising=False)
    case = onboarding.create_case(CUSTOMER)
    verify_all()
    onboarding.record_acknowledgement(CUSTOMER, "terms", "terms-2026-11")
    onboarding.advance(INTAKE, case["id"], "contact_verified")
    onboarding.advance(INTAKE, case["id"], "account_active")
    onboarding.record_acknowledgement(CUSTOMER, "privacy_notice", "privacy-2026-11")
    onboarding.advance(INTAKE, case["id"], "privacy_acknowledged")
    with pytest.raises(onboarding.ConfigurationMissing):
        onboarding.advance(INTAKE, case["id"], "consented")


def test_account_active_needs_mfa_event_and_terms(env):
    case = onboarding.create_case(CUSTOMER)
    verify_all()
    onboarding.advance(INTAKE, case["id"], "contact_verified")
    with pytest.raises(onboarding.RequirementNotMet, match="terms"):
        onboarding.advance(INTAKE, case["id"], "account_active")


# ---------- attestations and separation of duties ----------

def test_eligibility_needs_clinician_attestation_not_intake(env):
    case = onboarding.create_case(CUSTOMER)
    _prepare_to_intake(case["id"])
    with pytest.raises(onboarding.RequirementNotMet, match="No eligibility attestation"):
        onboarding.advance(INTAKE, case["id"], "intake_eligible")
    with pytest.raises(PermissionError):
        onboarding.record_attestation(INTAKE, case["id"], "eligibility", "not-a-record")
    _att(SUPERVISOR, case["id"], "eligibility")
    onboarding.advance(INTAKE, case["id"], "intake_eligible")


def test_attester_cannot_advance_same_stage(env):
    case = onboarding.create_case(CUSTOMER)
    _prepare_to_intake(case["id"])
    _att(SUPERVISOR, case["id"], "eligibility")
    with pytest.raises(onboarding.RequirementNotMet, match="separation of duties"):
        onboarding.advance(SUPERVISOR, case["id"], "intake_eligible")


def test_customer_cannot_attest_own_stage(env):
    case = onboarding.create_case(CUSTOMER)
    with pytest.raises(PermissionError):
        onboarding.record_attestation(CUSTOMER, case["id"], "eligibility", "not-a-record")


def test_team_assignment_requires_authorised_clinician(env):
    case = onboarding.create_case(CUSTOMER)
    _prepare_to_intake(case["id"])
    _att(SUPERVISOR, case["id"], "eligibility")
    onboarding.advance(INTAKE, case["id"], "intake_eligible")
    _att(SUPERVISOR, case["id"], "screening")
    onboarding.advance(INTAKE, case["id"], "screened")
    _att(INTAKE, case["id"], "allocation")
    onboarding.advance(SUPERVISOR, case["id"], "allocated")
    _att(INTAKE, case["id"], "team_assignment", SUPERVISOR)
    with pytest.raises(onboarding.RequirementNotMet, match="authorised clinician"):
        onboarding.advance(SUPERVISOR, case["id"], "team_assigned")


def _att(actor: str, case_id: str, kind: str, assignee: str | None = None) -> dict:
    """Create the platform record for a stage, then attest it as its responsible staff member."""
    record_type = onboarding.RECORD_TYPE_FOR_KIND[kind]
    record = onboarding.create_platform_record(actor, case_id, record_type, assignee)
    return onboarding.record_attestation(actor, case_id, kind, record["record_id"])


def _prepare_to_intake(case_id: str) -> None:
    verify_all()
    onboarding.record_acknowledgement(CUSTOMER, "terms", "terms-2026-11")
    onboarding.record_acknowledgement(CUSTOMER, "privacy_notice", "privacy-2026-11")
    onboarding.record_acknowledgement(CUSTOMER, "consent", "consent-2026-11")
    _full_customer_path(case_id)


# ---------- provisional restriction ----------

def test_provisional_account_cannot_be_granted_clinical_role(env):
    onboarding.create_case(CUSTOMER)
    with pytest.raises(ProvisionalRestriction):
        rbac.grant_role(ADMIN, CUSTOMER, Role.AUTHORISED_CLINICIAN)


def test_provisional_account_is_denied_clinical_routes_even_if_role_held(env):
    case = onboarding.create_case(CUSTOMER)
    # Simulate a role row written outside the grant path (e.g. by error or direct database access).
    with store._connect() as conn:
        conn.execute("INSERT INTO role_assignments (subject, role, granted_by, granted_at) "
                     "VALUES (?, 'authorised_clinician', 'test', '2026-11-21')", (CUSTOMER,))
    client = TestClient(app)
    app.dependency_overrides[auth.require_identity] = lambda: {"sub": CUSTOMER}
    try:
        assert client.post("/v1/clients", json={"x": 1}).status_code == 403
        with store._connect() as conn:
            rows = conn.execute("SELECT action FROM audit_chain WHERE action = 'access.denied_provisional'").fetchall()
        assert rows
    finally:
        app.dependency_overrides.pop(auth.require_identity, None)
    assert case["stage"] == "registered"


def test_completed_account_is_no_longer_provisional(env):
    case = onboarding.create_case(CUSTOMER)
    _prepare_to_intake(case["id"])
    _att(SUPERVISOR, case["id"], "eligibility")
    onboarding.advance(INTAKE, case["id"], "intake_eligible")
    _att(SUPERVISOR, case["id"], "screening")
    onboarding.advance(INTAKE, case["id"], "screened")
    _att(INTAKE, case["id"], "allocation")
    onboarding.advance(SUPERVISOR, case["id"], "allocated")
    _att(INTAKE, case["id"], "team_assignment", CLINICIAN)
    onboarding.advance(SUPERVISOR, case["id"], "team_assigned")
    onboarding.advance(INTAKE, case["id"], "complete")
    with store._connect() as conn:
        assert not rbac.is_provisional(conn, CUSTOMER)
    rbac.grant_role(ADMIN, CUSTOMER, Role.AUTHORISED_CLINICIAN)


def test_stage_order_still_enforced(env):
    case = onboarding.create_case(CUSTOMER)
    with pytest.raises(onboarding.InvalidTransition):
        onboarding.advance(INTAKE, case["id"], "consented")


# ---------- fail-closed authentication across protected routes ----------

PROTECTED = [
    ("post", "/v1/clients", {"json": {"x": 1}}),
    ("get", "/v1/clients/abc", {}),
    ("put", "/v1/clients/abc", {"json": {"x": 1}}),
    ("get", "/v1/onboarding/me", {}),
    ("post", "/v1/onboarding", {}),
    ("post", "/v1/onboarding/abc/advance", {"json": {"to_stage": "contact_verified"}}),
    ("post", "/v1/onboarding/abc/suspend", {}),
    ("post", "/v1/onboarding/me/acknowledgements", {"json": {"kind": "terms", "version": "x"}}),
    ("post", "/v1/onboarding/abc/attestations", {"json": {"kind": "eligibility", "record_id": "r"}}),
    ("post", "/v1/admin/roles", {"json": {"subject": "x", "role": "auditor"}}),
]


@pytest.mark.parametrize("method,path,kwargs", PROTECTED)
def test_no_token_is_rejected(env, method, path, kwargs):
    client = TestClient(app)
    assert getattr(client, method)(path, **kwargs).status_code == 401


@pytest.mark.parametrize("method,path,kwargs", PROTECTED)
def test_garbage_token_is_rejected(env, method, path, kwargs):
    client = TestClient(app)
    response = getattr(client, method)(path, headers={"Authorization": "Bearer not-a-token"}, **kwargs)
    assert response.status_code in (401, 503)
    assert response.status_code != 200


@pytest.mark.parametrize("method,path,kwargs", PROTECTED)
def test_unconfigured_idp_fails_closed(env, monkeypatch, method, path, kwargs):
    monkeypatch.delenv("STN_OIDC_JWKS_URL", raising=False)
    client = TestClient(app)
    response = getattr(client, method)(path, headers={"Authorization": "Bearer x"}, **kwargs)
    assert response.status_code == 503


def test_admin_grant_denied_for_customer_identity(env):
    rbac.grant_system_role("cust-x", Role.CUSTOMER)
    client = TestClient(app)
    app.dependency_overrides[auth.require_identity] = lambda: {"sub": "cust-x"}
    try:
        assert client.post("/v1/admin/roles", json={"subject": "x", "role": "auditor"}).status_code == 403
    finally:
        app.dependency_overrides.pop(auth.require_identity, None)


# ---------- attestations must cite real platform records (migration 0004) ----------

def _case_at_intake(env_case_subject: str = CUSTOMER) -> str:
    case = onboarding.create_case(env_case_subject)
    _prepare_to_intake(case["id"])
    return case["id"]


def test_attestation_citing_nonexistent_record_is_refused(env):
    case_id = _case_at_intake()
    with pytest.raises(onboarding.RequirementNotMet, match="does not exist"):
        onboarding.record_attestation(SUPERVISOR, case_id, "eligibility", "11111111-1111-1111-1111-111111111111")


def test_free_text_reference_does_not_satisfy_a_stage(env):
    case_id = _case_at_intake()
    # Legacy-style row written directly: a free-text reference is not a platform record.
    with store._connect() as conn:
        conn.execute("INSERT INTO attestations (case_id, kind, reference, attested_by, recorded_at) "
                     "VALUES (?, 'eligibility', 'checked', ?, '2026-11-21')", (case_id, SUPERVISOR))
    with pytest.raises(onboarding.RequirementNotMet, match="valid active platform record"):
        onboarding.advance(INTAKE, case_id, "intake_eligible")


def test_record_citing_another_staff_members_record_is_refused(env):
    case_id = _case_at_intake()
    record = onboarding.create_platform_record(SUPERVISOR, case_id, "eligibility_review")
    with pytest.raises(onboarding.RequirementNotMet, match="responsible staff member"):
        onboarding.record_attestation(CLINICIAN, case_id, "eligibility", record["record_id"])


def test_record_of_wrong_type_is_refused(env):
    case_id = _case_at_intake()
    record = onboarding.create_platform_record(SUPERVISOR, case_id, "screening_review")
    with pytest.raises(onboarding.RequirementNotMet, match="does not exist for this case and stage"):
        onboarding.record_attestation(SUPERVISOR, case_id, "eligibility", record["record_id"])


def test_withdrawn_record_cannot_be_attested_or_advance_a_stage(env):
    case_id = _case_at_intake()
    record = onboarding.create_platform_record(SUPERVISOR, case_id, "eligibility_review")
    onboarding.record_attestation(SUPERVISOR, case_id, "eligibility", record["record_id"])
    with store._connect() as conn:
        conn.execute("UPDATE platform_records SET status = 'withdrawn' WHERE id = ?", (record["record_id"],))
    with pytest.raises(onboarding.RequirementNotMet, match="valid active platform record"):
        onboarding.advance(INTAKE, case_id, "intake_eligible")


def test_platform_record_fields_cannot_be_changed_or_deleted(env):
    case_id = _case_at_intake()
    record = onboarding.create_platform_record(SUPERVISOR, case_id, "eligibility_review")
    with store._connect() as conn:
        with pytest.raises(Exception, match="fields are fixed"):
            conn.execute("UPDATE platform_records SET responsible_sub = ? WHERE id = ?", (CLINICIAN, record["record_id"]))
        with pytest.raises(Exception, match="append-only"):
            conn.execute("DELETE FROM platform_records WHERE id = ?", (record["record_id"],))


def test_only_the_authorised_role_can_create_a_record_type(env):
    case_id = _case_at_intake()
    with pytest.raises(PermissionError):
        onboarding.create_platform_record(INTAKE, case_id, "screening_review")
    with pytest.raises(PermissionError):
        onboarding.create_platform_record(CUSTOMER, case_id, "eligibility_review")


def test_team_assignment_record_must_name_an_assignee(env):
    case_id = _case_at_intake()
    with pytest.raises(onboarding.RequirementNotMet, match="must name the assignee"):
        onboarding.create_platform_record(INTAKE, case_id, "team_assignment")


def test_record_creation_and_attestation_are_audited(env):
    case_id = _case_at_intake()
    record = onboarding.create_platform_record(SUPERVISOR, case_id, "eligibility_review")
    onboarding.record_attestation(SUPERVISOR, case_id, "eligibility", record["record_id"])
    with store._connect() as conn:
        actions = [r["action"] for r in conn.execute("SELECT action FROM audit_chain ORDER BY seq")]
    assert "platform_record.created" in actions
    assert "attestation.recorded" in actions
    assert audit.verify() == (True, None)
