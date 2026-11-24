"""Data-key rotation: status and re-encryption of stored ciphertext.

Rotation procedure (see backend/README.md):
1. Add the new key to the keyring (STN_DATA_KEYS or Key Vault) alongside the old one.
2. Make it active (STN_DATA_ACTIVE_KEY_ID). New writes now use it; old records still decrypt.
3. Run the re-encrypt job until "remaining" is 0: POST /v1/admin/keys/re-encrypt for one
   organisation, or `python -m app.rekey` as the platform operator for all of them.
4. Only then remove the old key.

Each record is decrypted with its own associated data and re-encrypted under the
active key; the plaintext never leaves the process. Submitted and signed-off
assessments are checked against their recorded content hash before they are
rewritten, so a record that fails verification is skipped and audited, never
"healed". Only ciphertext columns change: updated_at, workflow state and sign-off
metadata are untouched (the database trigger on signed-off rows enforces this).
Disposed records hold no ciphertext and are skipped. Statements of correction
(app.privacy_requests) are covered as well.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

from . import audit, db
from .assessments import _aad as assessment_aad
from .assessments import _note_aad, _payload
from .crypto import decrypt_payload, encrypt_payload, key_id_of, key_provider, keyring
from .privacy_requests import statement_aad
from .store import client_aad

SYSTEM_ACTOR = "system:rekey"


def _rows(conn: db.Conn, table: str, org: str | None) -> list[dict[str, Any]]:
    sql = f"SELECT * FROM {table} WHERE disposed_at IS NULL"
    params: tuple = ()
    if org is not None:
        sql += " AND org_id = ?"
        params = (org,)
    return conn.execute(sql + " ORDER BY id", params).fetchall()


def status(org: str | None) -> dict[str, Any]:
    ring = keyring()
    counts: Counter[str] = Counter()
    with db.transaction() as conn:
        for row in _rows(conn, "client_records", org):
            counts[key_id_of(row["ciphertext"])] += 1
        for row in _rows(conn, "assessments", org):
            counts[key_id_of(row["ciphertext"])] += 1
            if row["note_ciphertext"] is not None:
                counts[key_id_of(row["note_ciphertext"])] += 1
        for row in _rows(conn, "correction_statements", org):
            counts[key_id_of(row["statement_ciphertext"])] += 1
    pending = sum(n for key_id, n in counts.items() if key_id != ring.active_id)
    return {
        "provider": key_provider().name,
        "active_key_id": ring.active_id,
        "available_key_ids": sorted(ring.keys),
        "ciphertexts_by_key_id": dict(sorted(counts.items())),
        "pending_reencryption": pending,
    }


def reencrypt(actor: str, org: str | None, limit: int = 500) -> dict[str, Any]:
    """Move up to `limit` records (one transaction) onto the active key."""
    active = keyring().active_id
    done = failed = 0
    with db.transaction() as conn:
        for row in _rows(conn, "client_records", org):
            if done + failed >= limit:
                break
            if key_id_of(row["ciphertext"]) == active:
                continue
            aad = client_aad(row["id"], row["owner_sub"])
            try:
                blob = encrypt_payload(decrypt_payload(row["ciphertext"], aad), aad)
            except Exception:  # noqa: BLE001 - integrity or key failure: skip and audit
                failed += 1
                audit.append(conn, actor, "key.reencrypt", "client", row["id"], "integrity_failure", org=row["org_id"])
                continue
            conn.execute(
                "UPDATE client_records SET ciphertext = ? WHERE id = ? AND ciphertext = ?",
                (blob, row["id"], row["ciphertext"]),
            )
            done += 1
            audit.append(conn, actor, "key.reencrypt", "client", row["id"], "ok", org=row["org_id"])
        for row in _rows(conn, "assessments", org):
            if done + failed >= limit:
                break
            note = row["note_ciphertext"]
            if key_id_of(row["ciphertext"]) == active and (note is None or key_id_of(note) == active):
                continue
            try:
                payload = _payload(row)
                blob = encrypt_payload(payload, assessment_aad(row["id"], row["author_sub"]))
                new_note = None
                if note is not None:
                    new_note = encrypt_payload(decrypt_payload(note, _note_aad(row["id"])), _note_aad(row["id"]))
            except Exception:  # noqa: BLE001 - integrity or key failure: skip and audit
                failed += 1
                audit.append(conn, actor, "key.reencrypt", "assessment", row["id"], "integrity_failure",
                             org=row["org_id"])
                continue
            conn.execute(
                "UPDATE assessments SET ciphertext = ?, note_ciphertext = ? WHERE id = ? AND ciphertext = ?",
                (blob, new_note, row["id"], row["ciphertext"]),
            )
            done += 1
            audit.append(conn, actor, "key.reencrypt", "assessment", row["id"], "ok", org=row["org_id"])
        for row in _rows(conn, "correction_statements", org):
            if done + failed >= limit:
                break
            if key_id_of(row["statement_ciphertext"]) == active:
                continue
            aad = statement_aad(row["id"], row["client_id"])
            try:
                blob = encrypt_payload(decrypt_payload(row["statement_ciphertext"], aad), aad)
            except Exception:  # noqa: BLE001 - integrity or key failure: skip and audit
                failed += 1
                audit.append(conn, actor, "key.reencrypt", "correction_statement", row["id"], "integrity_failure",
                             org=row["org_id"])
                continue
            conn.execute(
                "UPDATE correction_statements SET statement_ciphertext = ? WHERE id = ? AND statement_ciphertext = ?",
                (blob, row["id"], row["statement_ciphertext"]),
            )
            done += 1
            audit.append(conn, actor, "key.reencrypt", "correction_statement", row["id"], "ok", org=row["org_id"])
    remaining = status(org)["pending_reencryption"]
    return {"active_key_id": active, "reencrypted": done, "failed": failed, "remaining": remaining}


def verify_decrypt(org: str | None) -> dict[str, Any]:
    """Decrypt every stored payload (read-only) and report failures. Used after a restore."""
    checked = failed = 0
    with db.transaction() as conn:
        for row in _rows(conn, "client_records", org):
            checked += 1
            try:
                decrypt_payload(row["ciphertext"], client_aad(row["id"], row["owner_sub"]))
            except Exception:  # noqa: BLE001
                failed += 1
        for row in _rows(conn, "assessments", org):
            checked += 1
            try:
                _payload(row)
                if row["note_ciphertext"] is not None:
                    decrypt_payload(row["note_ciphertext"], _note_aad(row["id"]))
            except Exception:  # noqa: BLE001
                failed += 1
        for row in _rows(conn, "correction_statements", org):
            checked += 1
            try:
                decrypt_payload(row["statement_ciphertext"], statement_aad(row["id"], row["client_id"]))
            except Exception:  # noqa: BLE001
                failed += 1
    return {"records_checked": checked, "failed": failed, "ok": failed == 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-encrypt STN records under the active data key.")
    parser.add_argument("--org", help="Limit to one organisation (default: all).")
    parser.add_argument("--limit", type=int, default=500, help="Records per batch.")
    parser.add_argument("--status-only", action="store_true", help="Report key ids in use; change nothing.")
    parser.add_argument("--verify-decrypt", action="store_true", help="Decrypt every record; change nothing.")
    args = parser.parse_args(argv)
    if args.status_only:
        print(json.dumps(status(args.org), indent=2))
        return 0
    if args.verify_decrypt:
        result = verify_decrypt(args.org)
        print(json.dumps(result))
        return 0 if result["ok"] else 1
    while True:
        result = reencrypt(SYSTEM_ACTOR, args.org, args.limit)
        print(json.dumps(result))
        if result["remaining"] == 0 or result["reencrypted"] == 0:
            return 0 if result["remaining"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
