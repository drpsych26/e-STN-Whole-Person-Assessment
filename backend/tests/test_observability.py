"""Request IDs and structured access logs. No record content may reach the logs."""
from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_request_id_issued_reused_and_sanitised():
    r = client.get("/healthz")
    assert len(r.headers["x-request-id"]) == 36
    assert client.get("/healthz", headers={"X-Request-ID": "gw-abc_123"}).headers["x-request-id"] == "gw-abc_123"
    bad = client.get("/healthz", headers={"X-Request-ID": "x\" injected <script>"}).headers["x-request-id"]
    assert bad != "x\" injected <script>" and len(bad) == 36
    assert len(client.get("/healthz", headers={"X-Request-ID": "a" * 65}).headers["x-request-id"]) == 36


def test_access_log_uses_route_template_and_no_identifiers(backend, act, caplog):
    act("clin-obs", "clinician")
    cid = client.post("/v1/clients", json={"display_code": "SYN-OBS-SECRET"}).json()["id"]
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="stn.access"):
        r = client.get(f"/v1/clients/{cid}?display=SYN-OBS-SECRET", headers={"X-Request-ID": "trace-1"})
    lines = [json.loads(rec.message) for rec in caplog.records if rec.name == "stn.access"]
    assert lines and lines[-1]["route"] == "/v1/clients/{record_id}"
    assert lines[-1]["request_id"] == "trace-1" and lines[-1]["status"] == r.status_code
    blob = caplog.text
    assert cid not in blob and "SYN-OBS-SECRET" not in blob and "clin-obs" not in blob


def test_rate_limit_refusals_and_errors_carry_request_id(backend, act, monkeypatch, caplog):
    from app import clients
    act("clin-obs", "clinician")

    def boom(*a, **k):
        raise RuntimeError("payload with SYN-SECRET-CONTENT")

    monkeypatch.setattr(clients.store, "create_record", boom)
    with caplog.at_level(logging.ERROR, logger="stn.error"):
        r = client.post("/v1/clients", json={"display_code": "x"}, headers={"X-Request-ID": "err-1"})
    assert r.status_code == 500 and r.headers["x-request-id"] == "err-1"
    assert r.json() == {"detail": "Internal server error.", "request_id": "err-1"}
    assert "SYN-SECRET-CONTENT" not in caplog.text and "RuntimeError" in caplog.text
