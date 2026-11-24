"""Security headers are set on API, health, error and docs responses."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COMMON = {
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
}


def _assert_common(resp):
    for name, value in COMMON.items():
        assert resp.headers.get(name) == value, name


def test_health_has_strict_csp_and_no_store():
    resp = client.get("/health/live")
    _assert_common(resp)
    assert resp.headers["content-security-policy"].startswith("default-src 'none'")
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
    assert resp.headers["cache-control"] == "no-store"


def test_unauthenticated_api_refusal_still_has_headers():
    resp = client.get("/v1/clients")
    assert resp.status_code >= 400
    _assert_common(resp)
    assert "content-security-policy" in resp.headers


def test_docs_keep_working_without_api_csp():
    resp = client.get("/docs")
    _assert_common(resp)
    assert "content-security-policy" not in resp.headers
