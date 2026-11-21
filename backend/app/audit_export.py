"""Export audit-chain segments for write-once (immutable) external retention.

A segment is newline-delimited JSON covering a contiguous range of audit rows, plus a manifest
recording the segment's first and last hashes and its SHA-256. Upload the segment and manifest
to write-once storage (for example Azure Blob Storage with an immutability policy). The
manifest lets an auditor verify that the exported chain is consistent with the live chain.
Upload itself is not implemented here; it needs the storage account from Stage 3 infrastructure.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import audit, store


def export_segment(directory: Path, first_seq: int | None = None, last_seq: int | None = None) -> dict:
    with store._connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT seq, ts, actor, action, subject_ref, detail, prev_hash, hash FROM audit_chain "
            "WHERE (? IS NULL OR seq >= ?) AND (? IS NULL OR seq <= ?) ORDER BY seq",
            (first_seq, first_seq, last_seq, last_seq),
        ).fetchall()]
    if not rows:
        raise ValueError("No audit rows in the requested range.")
    directory.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    name = f"audit-{rows[0]['seq']:012d}-{rows[-1]['seq']:012d}"
    (directory / f"{name}.jsonl").write_text(body, encoding="utf-8")
    manifest = {
        "segment": f"{name}.jsonl",
        "first_seq": rows[0]["seq"], "last_seq": rows[-1]["seq"],
        "first_prev_hash": rows[0]["prev_hash"], "last_hash": rows[-1]["hash"],
        "row_count": len(rows), "segment_sha256": digest,
    }
    (directory / f"{name}.manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def verify_segment(directory: Path, manifest_name: str) -> bool:
    """Verify a downloaded segment against its manifest, independently of the database."""
    manifest = json.loads((directory / manifest_name).read_text(encoding="utf-8"))
    body = (directory / manifest["segment"]).read_text(encoding="utf-8")
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != manifest["segment_sha256"]:
        return False
    rows = [json.loads(line) for line in body.splitlines()]
    if len(rows) != manifest["row_count"] or rows[0]["prev_hash"] != manifest["first_prev_hash"]:
        return False
    prev = manifest["first_prev_hash"]
    for r in rows:
        if r["prev_hash"] != prev:
            return False
        if audit._digest(r["prev_hash"], r["ts"], r["actor"], r["action"], r["subject_ref"], r["detail"]) != r["hash"]:
            return False
        prev = r["hash"]
    return prev == manifest["last_hash"]
