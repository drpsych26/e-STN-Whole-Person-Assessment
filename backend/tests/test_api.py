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
