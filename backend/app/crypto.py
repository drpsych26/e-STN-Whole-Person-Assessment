"""AES-256-GCM encryption for client record payloads. Fail closed without a key.

The key is supplied as urlsafe-base64 of 32 random bytes in STN_DATA_KEY. It must
come from a secrets manager in any deployed environment and must never be committed.
Each record's ciphertext is bound to its record id and owner through associated data,
so a ciphertext copied to another record fails verification.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_ENV = "STN_DATA_KEY"
NONCE_BYTES = 12


class DataKeyError(RuntimeError):
    """Raised when the client-data key is missing or malformed."""


class RecordIntegrityError(RuntimeError):
    """Raised when a stored ciphertext fails authentication."""


def _load_key() -> bytes:
    raw = os.getenv(KEY_ENV, "").strip()
    if not raw:
        raise DataKeyError("Client data key is not configured.")
    try:
        key = base64.urlsafe_b64decode(raw.encode("ascii"))
    except Exception as exc:  # noqa: BLE001 - any decode failure is a configuration error
        raise DataKeyError("Client data key is malformed.") from exc
    if len(key) != 32:
        raise DataKeyError("Client data key must decode to 32 bytes.")
    return key


def encrypt_payload(payload: dict[str, Any], associated_data: bytes) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return nonce + AESGCM(_load_key()).encrypt(nonce, plaintext, associated_data)


def decrypt_payload(blob: bytes, associated_data: bytes) -> dict[str, Any]:
    if len(blob) <= NONCE_BYTES:
        raise RecordIntegrityError("Stored record is truncated.")
    nonce, ciphertext = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
    try:
        plaintext = AESGCM(_load_key()).decrypt(nonce, ciphertext, associated_data)
    except InvalidTag as exc:
        raise RecordIntegrityError("Stored record failed authentication.") from exc
    return json.loads(plaintext.decode("utf-8"))
