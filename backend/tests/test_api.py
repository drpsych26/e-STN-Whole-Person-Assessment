from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_is_available_without_clinical_data():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_identity_route_rejects_missing_bearer_token():
    response = client.get("/v1/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

def test_identity_route_stays_disabled_when_provider_is_unconfigured(monkeypatch):
    monkeypatch.delenv("STN_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("STN_OIDC_AUDIENCE", raising=False)
    monkeypatch.delenv("STN_OIDC_JWKS_URL", raising=False)
    response = client.get(
        "/v1/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]
