"""Client-record store tests. Synthetic data and a throwaway key only."""
from __future__ import annotations

import base64
import os
import secrets
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import auth, store
from app.main import app

MARKER = "SYNTHETIC-MARKER-7F3A"
OWNER = "clinician-owner"
OTHER = "clinician-other"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "records.sqlite3"
    monkeypatch.setenv(store.DB_ENV, str(path))
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    return path


@pytest.fixture
def as_user(monkeypatch):
    current = {"sub": OWNER}
    monkeypatch.setitem(app.dependency_overrides, auth.require_identity, lambda: {"sub": current["sub"]})

    def switch(sub: str) -> None:
        current["sub"] = sub

    yield switch
    app.dependency_overrides.pop(auth.require_identity, None)


client = TestClient(app)


def test_create_read_update_roundtrip(db_path, as_user):
    created = client.post("/v1/clients", json={"note": MARKER, "age_band": "adult"})
    assert created.status_code == 201
    record_id = created.json()["id"]

    read = client.get(f"/v1/clients/{record_id}")
    assert read.status_code == 200
    assert read.json()["payload"] == {"note": MARKER, "age_band": "adult"}

    updated = client.put(f"/v1/clients/{record_id}", json={"note": "changed"})
    assert updated.status_code == 200
    assert client.get(f"/v1/clients/{record_id}").json()["payload"] == {"note": "changed"}


def test_plaintext_never_reaches_disk(db_path, as_user):
    client.post("/v1/clients", json={"note": MARKER})
    raw = db_path.read_bytes()
    assert MARKER.encode() not in raw


def test_other_clinician_gets_not_found_not_forbidden(db_path, as_user):
    record_id = client.post("/v1/clients", json={"note": MARKER}).json()["id"]
    as_user(OTHER)
    assert client.get(f"/v1/clients/{record_id}").status_code == 404
    assert client.put(f"/v1/clients/{record_id}", json={"x": 1}).status_code == 404


def test_missing_record_matches_not_owned_response(db_path, as_user):
    missing = client.get("/v1/clients/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Record not found."


def test_audit_log_records_access_without_payload(db_path, as_user):
    record_id = client.post("/v1/clients", json={"note": MARKER}).json()["id"]
    client.get(f"/v1/clients/{record_id}")
    as_user(OTHER)
    client.get(f"/v1/clients/{record_id}")

    entries = store.audit_entries(record_id)
    assert [e["outcome"] for e in entries] == ["ok", "ok", "denied_or_missing"]
    assert [e["actor_sub"] for e in entries] == [OWNER, OWNER, OTHER]
    for entry in entries:
        assert MARKER not in " ".join(str(v) for v in entry.values())


def test_missing_key_fails_closed_without_storing(db_path, as_user, monkeypatch):
    monkeypatch.delenv("STN_DATA_KEY", raising=False)
    response = client.post("/v1/clients", json={"note": MARKER})
    assert response.status_code == 503
    assert not db_path.exists(), "no database file may be created when the key is missing"


def test_malformed_key_is_rejected(db_path, as_user, monkeypatch):
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(b"short").decode())
    assert client.post("/v1/clients", json={"note": MARKER}).status_code == 503


def test_unconfigured_database_fails_closed(as_user, monkeypatch):
    monkeypatch.delenv(store.DB_ENV, raising=False)
    monkeypatch.setenv("STN_DATA_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    assert client.post("/v1/clients", json={"x": 1}).status_code == 503


def test_tampered_ciphertext_is_detected(db_path, as_user):
    record_id = client.post("/v1/clients", json={"note": MARKER}).json()["id"]
    with sqlite3.connect(db_path) as conn:
        blob = bytearray(conn.execute(
            "SELECT ciphertext FROM client_records WHERE id = ?", (record_id,)
        ).fetchone()[0])
        blob[-1] ^= 0x01
        conn.execute("UPDATE client_records SET ciphertext = ? WHERE id = ?", (bytes(blob), record_id))
        conn.commit()
    response = client.get(f"/v1/clients/{record_id}")
    assert response.status_code == 500
    assert response.json()["detail"] == "Record could not be verified."


def test_swapped_ciphertext_between_records_is_detected(db_path, as_user):
    first = client.post("/v1/clients", json={"note": "first"}).json()["id"]
    second = client.post("/v1/clients", json={"note": "second"}).json()["id"]
    with sqlite3.connect(db_path) as conn:
        blob = conn.execute("SELECT ciphertext FROM client_records WHERE id = ?", (first,)).fetchone()[0]
        conn.execute("UPDATE client_records SET ciphertext = ? WHERE id = ?", (blob, second))
        conn.commit()
    assert client.get(f"/v1/clients/{second}").status_code == 500


def test_oversized_payload_rejected(db_path, as_user):
    big = {"blob": "x" * (64 * 1024 + 1)}
    assert client.post("/v1/clients", json=big).status_code == 413


def test_non_object_body_rejected(db_path, as_user):
    assert client.post("/v1/clients", json=["not", "an", "object"]).status_code == 422


def test_client_routes_require_identity(db_path):
    assert client.post("/v1/clients", json={"x": 1}).status_code == 401
    assert client.get("/v1/clients/anything").status_code == 401
