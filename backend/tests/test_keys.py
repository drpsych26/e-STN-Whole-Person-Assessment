"""Versioned keyring, rotation and the Key Vault provider stub. Throwaway keys only."""
from __future__ import annotations

import base64
import hashlib
import json
import secrets

import pytest
from fastapi.testclient import TestClient

from app import crypto, rekey
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

AUTHOR, REV, ADMIN = "clin-key", "rev-key", "admin-key"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer"}}


def new_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def sha(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def use_keys(monkeypatch, active: str, **keys: str) -> None:
    monkeypatch.delenv(crypto.KEY_ENV, raising=False)
    monkeypatch.setenv(crypto.KEYS_ENV, ",".join(f"{k}:{v}" for k, v in keys.items()))
    monkeypatch.setenv(crypto.ACTIVE_ENV, active)


def records(act) -> tuple[str, str]:
    """A client record and a signed-off assessment with a reviewer note on an earlier return."""
    act(AUTHOR, "clinician")
    cid = client.post("/v1/clients", json={"display_code": "SYN-KEY"}).json()["id"]
    aid = client.post("/v1/assessments", json={"client_id": cid, "form_id": "f", "form_version": "v1",
                                               "payload": PAYLOAD}).json()["id"]
    client.post(f"/v1/assessments/{aid}/submit", json={})
    act(REV, "reviewer")
    client.post(f"/v1/assessments/{aid}/start-review")
    client.post(f"/v1/assessments/{aid}/return", json={"reason": "Synthetic return note."})
    act(AUTHOR, "clinician")
    client.post(f"/v1/assessments/{aid}/reopen")
    client.post(f"/v1/assessments/{aid}/submit", json={})
    act(REV, "reviewer")
    client.post(f"/v1/assessments/{aid}/start-review")
    assert client.post(f"/v1/assessments/{aid}/sign-off", json={"content_hash": sha(PAYLOAD)}).status_code == 200
    return cid, aid


def readable(act, cid: str, aid: str) -> None:
    act(AUTHOR, "clinician")
    assert client.get(f"/v1/clients/{cid}").status_code == 200
    response = client.get(f"/v1/assessments/{aid}")
    assert response.status_code == 200, response.text
    assert response.json()["payload"] == PAYLOAD and response.json()["note"] == "Synthetic return note."


def test_rotation_round_trip(backend, act, raw, monkeypatch):
    k1, k2 = new_key(), new_key()
    use_keys(monkeypatch, "k2025", k2025=k1)
    cid, aid = records(act)
    blob = bytes(raw("SELECT ciphertext FROM assessments WHERE id = ?", (aid,))[0][0])
    assert crypto.key_id_of(blob) == "k2025"

    use_keys(monkeypatch, "k2026", k2025=k1, k2026=k2)
    readable(act, cid, aid)  # old key still readable
    act(ADMIN, "admin")
    status = client.get("/v1/admin/keys/status").json()
    assert status["active_key_id"] == "k2026" and status["pending_reencryption"] == 3
    assert "k2025" in status["ciphertexts_by_key_id"] and key_material_absent(status, k1, k2)

    result = client.post("/v1/admin/keys/re-encrypt", params={"limit": 1}).json()
    assert result["reencrypted"] == 1 and result["remaining"] > 0
    result = client.post("/v1/admin/keys/re-encrypt").json()
    assert result["remaining"] == 0 and result["failed"] == 0
    assert client.get("/v1/admin/keys/status").json()["ciphertexts_by_key_id"] == {"k2026": 3}

    use_keys(monkeypatch, "k2026", k2026=k2)  # old key retired
    readable(act, cid, aid)
    with pytest.raises(Exception, match="immutable"):
        raw("UPDATE assessments SET form_version = 'tampered' WHERE id = ?", (aid,))
    act(ADMIN, "admin")
    assert client.get("/v1/audit/verify").json()["ok"] is True
    assert any(e["action"] == "key.reencrypt" for e in client.get("/v1/audit", params={"limit": 500}).json())


def key_material_absent(status: dict, *keys: str) -> bool:
    text = json.dumps(status)
    return all(k not in text for k in keys)


def test_legacy_single_key_records_move_to_keyring(backend, act, raw, monkeypatch):
    legacy = new_key()
    monkeypatch.delenv(crypto.KEYS_ENV, raising=False)
    monkeypatch.delenv(crypto.ACTIVE_ENV, raising=False)
    monkeypatch.setenv(crypto.KEY_ENV, legacy)
    cid, aid = records(act)
    k2 = new_key()
    monkeypatch.setenv(crypto.KEYS_ENV, f"k2026:{k2}")
    monkeypatch.setenv(crypto.ACTIVE_ENV, "k2026")
    readable(act, cid, aid)
    assert rekey.main(["--limit", "10"]) == 0
    monkeypatch.delenv(crypto.KEY_ENV)
    readable(act, cid, aid)


def test_headerless_original_format_still_decrypts(monkeypatch):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = new_key()
    monkeypatch.setenv(crypto.KEY_ENV, key)
    nonce = secrets.token_bytes(12)
    blob = nonce + AESGCM(base64.urlsafe_b64decode(key)).encrypt(nonce, b'{"a":1}', b"aad")
    assert crypto.key_id_of(blob) == crypto.LEGACY_KEY_ID
    assert crypto.decrypt_payload(blob, b"aad") == {"a": 1}


def test_missing_key_or_forged_key_id_fails_verification(backend, act, raw, monkeypatch):
    use_keys(monkeypatch, "k1", k1=new_key())
    cid, _ = records(act)
    use_keys(monkeypatch, "k2", k2=new_key())
    act(AUTHOR, "clinician")
    assert client.get(f"/v1/clients/{cid}").status_code == 500

    use_keys(monkeypatch, "k1", k1=new_key(), kx=new_key())
    blob = crypto.encrypt_payload({"a": 1}, b"aad")
    forged = blob.replace(b"k1", b"kx", 1)
    with pytest.raises(crypto.RecordIntegrityError):
        crypto.decrypt_payload(forged, b"aad")


@pytest.mark.parametrize("keys,active", [
    ("k1:" + "A" * 10, "k1"),          # malformed key
    ("k1", "k1"),                       # missing separator
    ("k1:{k},k2:{k}", ""),              # ambiguous: no active id
    ("k1:{k}", "k9"),                   # active id not in ring
    ("legacy:{k}", "legacy"),           # reserved id
    ("bad id:{k}", "bad id"),           # invalid id
])
def test_keyring_misconfiguration_fails_closed(backend, act, monkeypatch, keys, active):
    monkeypatch.delenv(crypto.KEY_ENV, raising=False)
    monkeypatch.setenv(crypto.KEYS_ENV, keys.format(k=new_key()))
    monkeypatch.setenv(crypto.ACTIVE_ENV, active)
    act(AUTHOR, "clinician")
    assert client.post("/v1/clients", json={"x": 1}).status_code == 503


def test_replayed_older_ciphertext_is_detected_by_content_hash(backend, act, raw):
    act(AUTHOR, "clinician")
    cid = client.post("/v1/clients", json={"display_code": "SYN-KEY"}).json()["id"]
    created = client.post("/v1/assessments", json={"client_id": cid, "form_id": "f", "form_version": "v1",
                                                   "payload": {"v": 1}}).json()
    aid = created["id"]
    old_blob = bytes(raw("SELECT ciphertext FROM assessments WHERE id = ?", (aid,))[0][0])
    client.put(f"/v1/assessments/{aid}", json={"payload": {"v": 2}, "revision": 1})
    client.post(f"/v1/assessments/{aid}/submit", json={})
    raw("UPDATE assessments SET ciphertext = ? WHERE id = ?", (old_blob, aid))
    response = client.get(f"/v1/assessments/{aid}")
    assert response.status_code == 500 and response.json()["detail"] == "Record could not be verified."


class _Secret:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeVault:
    def __init__(self, secrets_by_name: dict[str, str]) -> None:
        self.secrets = secrets_by_name
        self.reads = 0

    def get_secret(self, name: str) -> _Secret:
        self.reads += 1
        if name not in self.secrets:
            raise KeyError(name)
        return _Secret(self.secrets[name])


def test_key_vault_provider_fails_closed_unless_configured(backend, act, monkeypatch):
    monkeypatch.setenv(crypto.PROVIDER_ENV, "azure-keyvault")
    act(AUTHOR, "clinician")
    assert client.post("/v1/clients", json={"x": 1}).status_code == 503  # nothing configured
    monkeypatch.setenv(crypto.KEYVAULT_URL_ENV, "https://stn-synthetic.vault.azure.net/")
    monkeypatch.setenv(crypto.KEYVAULT_IDS_ENV, "stn-data-2026a")
    monkeypatch.setenv(crypto.ACTIVE_ENV, "stn-data-2026a")
    assert client.post("/v1/clients", json={"x": 1}).status_code == 503  # SDK not installed in tests
    monkeypatch.setenv(crypto.PROVIDER_ENV, "something-else")
    assert client.post("/v1/clients", json={"x": 1}).status_code == 503


def test_key_vault_provider_with_fake_vault(backend, act, monkeypatch):
    vault = _FakeVault({"stn-data-2026a": new_key()})
    crypto.set_key_provider(crypto.AzureKeyVaultKeyProvider(client_factory=lambda url: vault))
    monkeypatch.setenv(crypto.KEYVAULT_URL_ENV, "https://stn-synthetic.vault.azure.net/")
    monkeypatch.setenv(crypto.KEYVAULT_IDS_ENV, "stn-data-2026a")
    monkeypatch.setenv(crypto.ACTIVE_ENV, "stn-data-2026a")
    act(AUTHOR, "clinician")
    cid = client.post("/v1/clients", json={"x": 1}).json()["id"]
    assert client.get(f"/v1/clients/{cid}").json()["payload"] == {"x": 1}
    assert vault.reads == 1  # cached
    act(ADMIN, "admin")
    assert client.get("/v1/admin/keys/status").json()["provider"] == "azure-keyvault"
    crypto.set_key_provider(crypto.AzureKeyVaultKeyProvider(client_factory=lambda url: _FakeVault({})))
    act(AUTHOR, "clinician")
    assert client.get(f"/v1/clients/{cid}").status_code == 503  # secret unreadable
