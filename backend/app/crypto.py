"""AES-256-GCM encryption for record payloads with a versioned keyring. Fail closed.

Keys come from a KeyProvider (STN_KEY_PROVIDER):
- "env" (default): STN_DATA_KEYS="<key-id>:<urlsafe-b64 32 bytes>,..." plus
  STN_DATA_ACTIVE_KEY_ID. The single-key setting STN_DATA_KEY is still accepted and
  is available as key id "legacy"; with only STN_DATA_KEY set, "legacy" is active.
- "azure-keyvault": keys are Key Vault secrets (see AzureKeyVaultKeyProvider). It
  fails closed unless fully configured and the Azure SDK is installed. It is not
  exercised against a live vault in CI.

Envelope written for every new ciphertext:
    b"STNk" | version (1 byte = 2) | key-id length (1 byte) | key id | nonce (12) | ciphertext+tag
The header is authenticated as part of the associated data, so changing the key id
breaks verification. Blobs without the header are the original format and decrypt
with the "legacy" key. Each record's associated data also binds the ciphertext to
its record id and owner, so a ciphertext copied to another record fails verification.

Keys must come from a secrets manager in any deployed environment and must never be
committed. Rotation: add a new key, make it active, then run the admin re-encrypt
job (app.rekey) so stored records move to the active key; old keys stay readable
until every record has moved.
"""
from __future__ import annotations

import base64
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_ENV = "STN_DATA_KEY"
KEYS_ENV = "STN_DATA_KEYS"
ACTIVE_ENV = "STN_DATA_ACTIVE_KEY_ID"
PROVIDER_ENV = "STN_KEY_PROVIDER"
KEYVAULT_URL_ENV = "STN_KEYVAULT_URL"
KEYVAULT_IDS_ENV = "STN_KEYVAULT_KEY_IDS"
LEGACY_KEY_ID = "legacy"
MAGIC = b"STNk"
ENVELOPE_VERSION = 2
NONCE_BYTES = 12
_KEY_ID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class DataKeyError(RuntimeError):
    """Raised when the data keys are missing, malformed or unavailable."""


class RecordIntegrityError(RuntimeError):
    """Raised when a stored ciphertext fails authentication."""


@dataclass(frozen=True)
class Keyring:
    keys: dict[str, bytes]
    active_id: str

    def active_key(self) -> bytes:
        return self.keys[self.active_id]


class KeyProvider(Protocol):
    name: str

    def keyring(self) -> Keyring: ...


def _decode_key(raw: str, label: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(raw.strip().encode("ascii"))
    except Exception as exc:  # noqa: BLE001 - any decode failure is a configuration error
        raise DataKeyError(f"Data key '{label}' is malformed.") from exc
    if len(key) != 32:
        raise DataKeyError(f"Data key '{label}' must decode to 32 bytes.")
    return key


def _check_key_id(key_id: str) -> str:
    if not _KEY_ID.match(key_id):
        raise DataKeyError("Data key ids must be 1-64 letters, digits, '_', '.' or '-'.")
    return key_id


def _build(keys: dict[str, bytes], active: str) -> Keyring:
    if not keys:
        raise DataKeyError("Client data key is not configured.")
    if not active:
        if set(keys) == {LEGACY_KEY_ID}:
            active = LEGACY_KEY_ID
        else:
            raise DataKeyError(f"{ACTIVE_ENV} must name the active data key.")
    if active not in keys:
        raise DataKeyError("The active data key id is not in the keyring.")
    return Keyring(keys=keys, active_id=active)


class EnvKeyProvider:
    """Keys from environment variables (local, CI and synthetic runs)."""

    name = "env"

    def keyring(self) -> Keyring:
        keys: dict[str, bytes] = {}
        legacy = os.getenv(KEY_ENV, "").strip()
        if legacy:
            keys[LEGACY_KEY_ID] = _decode_key(legacy, LEGACY_KEY_ID)
        for item in os.getenv(KEYS_ENV, "").split(","):
            if not item.strip():
                continue
            if ":" not in item:
                raise DataKeyError(f"{KEYS_ENV} entries must be '<key-id>:<base64 key>'.")
            key_id, raw = (p.strip() for p in item.split(":", 1))
            _check_key_id(key_id)
            if key_id == LEGACY_KEY_ID or key_id in keys:
                raise DataKeyError(f"Data key id '{key_id}' is reserved or duplicated.")
            keys[key_id] = _decode_key(raw, key_id)
        return _build(keys, os.getenv(ACTIVE_ENV, "").strip())


def _azure_secret_client(vault_url: str) -> Any:
    try:
        from azure.identity import DefaultAzureCredential  # type: ignore[import-not-found]
        from azure.keyvault.secrets import SecretClient  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DataKeyError("Azure Key Vault SDK is not installed; the key provider is unavailable.") from exc
    return SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())


class AzureKeyVaultKeyProvider:
    """Keys held as Azure Key Vault secrets (urlsafe-base64 of 32 bytes per secret).

    Configuration (all required, otherwise fail closed):
      STN_KEYVAULT_URL       https://<vault-name>.vault.azure.net/
      STN_KEYVAULT_KEY_IDS   comma-separated secret names; each name is also the key id
      STN_DATA_ACTIVE_KEY_ID one of those ids
    The managed identity of the API needs only "get" on those secrets. Keys are cached
    in memory for ttl_seconds. This class is unit-tested with a fake secret client;
    it has not been run against a live vault from this repository.
    """

    name = "azure-keyvault"

    def __init__(self, client_factory: Callable[[str], Any] | None = None, ttl_seconds: int = 300) -> None:
        self._factory = client_factory
        self._ttl = ttl_seconds
        self._cached: tuple[float, Keyring] | None = None
        self._lock = threading.Lock()

    def keyring(self) -> Keyring:
        url = os.getenv(KEYVAULT_URL_ENV, "").strip()
        ids = [i.strip() for i in os.getenv(KEYVAULT_IDS_ENV, "").split(",") if i.strip()]
        active = os.getenv(ACTIVE_ENV, "").strip()
        if not url.startswith("https://") or not ids or not active:
            raise DataKeyError("Azure Key Vault key provider is not configured.")
        with self._lock:
            if self._cached and self._cached[0] > time.monotonic():
                return self._cached[1]
            client = (self._factory or _azure_secret_client)(url)
            keys: dict[str, bytes] = {}
            for key_id in ids:
                _check_key_id(key_id)
                try:
                    secret = client.get_secret(key_id)
                except Exception as exc:  # noqa: BLE001 - never expose vault details
                    raise DataKeyError("A data key could not be read from Key Vault.") from exc
                keys[key_id] = _decode_key(getattr(secret, "value", "") or "", key_id)
            ring = _build(keys, active)
            self._cached = (time.monotonic() + self._ttl, ring)
            return ring


_override: KeyProvider | None = None
_azure_provider = AzureKeyVaultKeyProvider()


def set_key_provider(provider: KeyProvider | None) -> None:
    """Test and composition hook. None restores selection by STN_KEY_PROVIDER."""
    global _override
    _override = provider


def key_provider() -> KeyProvider:
    if _override is not None:
        return _override
    choice = os.getenv(PROVIDER_ENV, "env").strip().lower() or "env"
    if choice == "env":
        return EnvKeyProvider()
    if choice == "azure-keyvault":
        return _azure_provider
    raise DataKeyError(f"Unknown key provider '{choice}'.")


def keyring() -> Keyring:
    return key_provider().keyring()


def _header(key_id: str) -> bytes:
    encoded = key_id.encode("ascii")
    return MAGIC + bytes([ENVELOPE_VERSION, len(encoded)]) + encoded


def _split(blob: bytes) -> tuple[str, bytes, bytes]:
    """Return (key id, header, nonce+ciphertext). Headerless blobs are the legacy format."""
    if blob[:4] == MAGIC and len(blob) > 6 and blob[4] == ENVELOPE_VERSION:
        length = blob[5]
        key_id_bytes = blob[6:6 + length]
        try:
            key_id = key_id_bytes.decode("ascii")
        except UnicodeDecodeError:
            key_id = ""
        if key_id and _KEY_ID.match(key_id):
            header_end = 6 + length
            return key_id, blob[:header_end], blob[header_end:]
    return LEGACY_KEY_ID, b"", blob


def key_id_of(blob: bytes) -> str:
    return _split(blob)[0]


def encrypt_payload(payload: dict[str, Any], associated_data: bytes) -> bytes:
    ring = keyring()
    header = _header(ring.active_id)
    nonce = os.urandom(NONCE_BYTES)
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return header + nonce + AESGCM(ring.active_key()).encrypt(nonce, plaintext, header + associated_data)


def decrypt_payload(blob: bytes, associated_data: bytes) -> dict[str, Any]:
    ring = keyring()
    key_id, header, body = _split(blob)
    if len(body) <= NONCE_BYTES:
        raise RecordIntegrityError("Stored record is truncated.")
    key = ring.keys.get(key_id)
    if key is None:
        raise RecordIntegrityError("Stored record uses a data key that is not available.")
    nonce, ciphertext = body[:NONCE_BYTES], body[NONCE_BYTES:]
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, header + associated_data)
    except InvalidTag as exc:
        raise RecordIntegrityError("Stored record failed authentication.") from exc
    return json.loads(plaintext.decode("utf-8"))
