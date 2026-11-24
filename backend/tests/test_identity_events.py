"""Identity-provider verification events: signature, claims, freshness and replay. Synthetic keys only.

These prove the validation logic, not a live Entra tenant integration.
"""
from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.idp_fixtures import API_AUDIENCE, EVENT_AUDIENCE, OTHER, PRIVATE, event, idp  # noqa: F401

client = TestClient(app, raise_server_exceptions=False)


def post(token):
    return client.post("/v1/identity/events", json={"event": token})


@pytest.fixture(autouse=True)
def _migrated(request):
    """Rejected events never touch the database; migrate it so the 'nothing stored' checks can read it."""
    if "backend" in request.fixturenames:
        request.getfixturevalue("backend")
        from app import db
        with db.transaction():
            pass


def stored(raw, subject):
    return raw("SELECT kind FROM identity_verification_events WHERE subject = ? ORDER BY kind", (subject,))


def test_valid_events_are_recorded_and_replay_is_refused(backend, idp, raw):
    token = idp("subj-ev-1", "email_verified")
    r = post(token)
    assert r.status_code == 202 and r.json() == {"subject": "subj-ev-1", "kind": "email", "recorded": True}
    assert post(idp("subj-ev-1", "mfa_enrolled")).status_code == 202
    replay = post(token)
    assert replay.status_code == 401 and "already been recorded" in replay.json()["detail"]
    assert [r[0] for r in stored(raw, "subj-ev-1")] == ["email", "mfa"]


@pytest.mark.parametrize("overrides, reason", [
    ({"aud": API_AUDIENCE}, "API access-token audience"),
    ({"aud": "someone-else"}, "wrong audience"),
    ({"iss": "https://evil.test/"}, "wrong issuer"),
    ({"exp": int(time.time()) - 3600}, "expired"),
    ({"iat": int(time.time()) - 3600}, "too old"),
    ({"iat": int(time.time()) + 3600}, "issued in the future"),
    ({"iat": None}, "no issue time"),
    ({"jti": None}, "no event id"),
    ({"jti": "short"}, "malformed event id"),
    ({"sub": "bad subject with spaces"}, "malformed subject"),
    ({"event": "password_changed"}, "unknown event kind"),
    ({"verified": False}, "not a confirmed verification"),
    ({"verified": "true"}, "verified must be boolean true"),
    ({"nbf": int(time.time()) + 3600}, "not yet valid"),
])
def test_invalid_events_are_rejected_and_not_stored(backend, idp, raw, overrides, reason):
    r = post(idp("subj-ev-bad", **overrides))
    assert r.status_code == 401, reason
    assert stored(raw, "subj-ev-bad") == []


def test_wrong_key_and_unsigned_tokens_are_rejected(backend, idp, raw):
    assert post(idp("subj-ev-key", key=OTHER)).status_code == 401
    claims = jwt.decode(idp("subj-ev-key"), options={"verify_signature": False})
    assert post(jwt.encode(claims, "shared-secret-attack-0123456789abcdef", algorithm="HS256")).status_code == 401
    unsigned = jwt.encode(claims, None, algorithm="none")
    assert post(unsigned).status_code == 401
    assert post("not-a-jwt").status_code == 401
    assert client.post("/v1/identity/events", json={}).status_code == 401
    assert stored(raw, "subj-ev-key") == []


def test_fails_closed_when_not_configured(backend, idp, monkeypatch):
    monkeypatch.delenv("STN_IDP_EVENT_AUDIENCE")
    assert post(idp("subj-ev-cfg")).status_code == 503
    monkeypatch.setenv("STN_IDP_EVENT_AUDIENCE", API_AUDIENCE)  # must differ from the API audience
    assert post(idp("subj-ev-cfg", aud=API_AUDIENCE)).status_code == 503


def test_events_cannot_be_rewritten(backend, idp, raw):
    assert post(idp("subj-ev-rw")).status_code == 202
    with pytest.raises(Exception):
        raw("UPDATE identity_verification_events SET kind = 'mfa' WHERE subject = ?", ("subj-ev-rw",))
    with pytest.raises(Exception):
        raw("DELETE FROM identity_verification_events WHERE subject = ?", ("subj-ev-rw",))


def test_event_cannot_be_used_as_an_api_bearer_token(backend, idp, monkeypatch):
    """Same key and issuer, but the event audience is not the API audience, so /v1/me refuses it."""
    from app import auth
    from tests import idp_fixtures

    monkeypatch.setattr(auth, "_jwks_client", lambda url: idp_fixtures._Jwks())
    token = idp("subj-ev-bearer", roles=["admin"], stn_org="org-synthetic-1", amr=["mfa"])
    r = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    good = jwt.encode({"iss": idp_fixtures.ISSUER, "aud": API_AUDIENCE, "sub": "subj-ev-bearer",
                       "iat": int(time.time()), "exp": int(time.time()) + 300}, PRIVATE, algorithm="RS256")
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {good}"}).status_code == 200
    assert EVENT_AUDIENCE != API_AUDIENCE
