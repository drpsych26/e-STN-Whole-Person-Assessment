"""Export the audit hash chain to write-once storage, then verify what was stored (D-18).

    python -m app.audit_export --sink local:/path/to/dir      # local or test
    python -m app.audit_export --sink azure                   # STN_EVIDENCE_BLOB_ENDPOINT + managed identity
    python -m app.audit_export --sink azure --store-dump FILE # put a logical dump into db-dumps and verify it

Each run:
1. Verifies the whole chain (app.audit.verify_chain). A broken chain is NOT exported: the run records
   nothing, prints the first broken event id and exits 1, so tampering is never laundered into the archive.
2. Takes the events after the last verified export (at most --max-events), and checks continuity: the
   first event's prev_hash must equal the previous export's last hash.
3. Writes them as canonical JSON lines (one event per line, sorted keys) to a new object named by its
   event-id range. The sink refuses to overwrite an existing object.
4. Reads the object back and compares SHA-256. Only then is the export recorded (audit_exports, append-only)
   and an audit event written. Any failure exits non-zero and records nothing, so the next run retries.

Audit events hold identifiers and codes only (see app.audit), so exports contain no clinical content.

Status: the local sink is tested. The Azure sink speaks the Blob REST API with a managed-identity token
(azure-identity, in the production image) and has NOT been run against a real storage account.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import audit, db

AUDIT_CONTAINER = "audit-exports"
DUMP_CONTAINER = "db-dumps"


class ExportError(RuntimeError):
    pass


class LocalSink:
    """Directory sink for tests and local drills. Refuses to overwrite, like an immutable container."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.label = f"local:{root}"

    def put(self, container: str, name: str, data: bytes) -> None:
        path = self.root / container / name
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "xb") as handle:
                handle.write(data)
        except FileExistsError as exc:
            raise ExportError(f"{container}/{name} already exists; write-once storage cannot be overwritten.") from exc

    def get(self, container: str, name: str) -> bytes:
        return (self.root / container / name).read_bytes()


class AzureBlobSink:
    """Blob REST API with an Entra token (no shared keys). If-None-Match: * makes every write create-only."""

    API_VERSION = "2023-11-03"

    def __init__(self, endpoint: str) -> None:
        if not endpoint.startswith("https://"):
            raise ExportError("STN_EVIDENCE_BLOB_ENDPOINT must be the https blob endpoint.")
        self.endpoint = endpoint.rstrip("/")
        self.label = f"azure:{self.endpoint}"

    def _token(self) -> str:
        try:
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:
            raise ExportError("azure-identity is not installed (production image extra 'azure').") from exc
        return DefaultAzureCredential().get_token("https://storage.azure.com/.default").token

    def _request(self, method: str, container: str, name: str, data: bytes | None = None) -> bytes:
        headers = {"Authorization": f"Bearer {self._token()}", "x-ms-version": self.API_VERSION,
                   "x-ms-date": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")}
        if method == "PUT":
            headers.update({"x-ms-blob-type": "BlockBlob", "If-None-Match": "*",
                            "Content-Type": "application/octet-stream", "Content-Length": str(len(data or b""))})
        request = urllib.request.Request(f"{self.endpoint}/{container}/{name}", data=data, method=method, headers=headers)
        try:
            # Bandit B310 reviewed: the endpoint is required to be https in __init__.
            with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (409, 412):
                raise ExportError(f"{container}/{name} already exists; write-once storage cannot be overwritten.") from exc
            raise ExportError(f"Blob {method} failed with HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise ExportError("Blob endpoint unreachable.") from exc

    def put(self, container: str, name: str, data: bytes) -> None:
        self._request("PUT", container, name, data)

    def get(self, container: str, name: str) -> bytes:
        return self._request("GET", container, name)


def sink_from(spec: str) -> Any:
    if spec.startswith("local:"):
        return LocalSink(spec[len("local:"):])
    if spec == "azure":
        endpoint = os.getenv("STN_EVIDENCE_BLOB_ENDPOINT", "").strip()
        if not endpoint:
            raise ExportError("STN_EVIDENCE_BLOB_ENDPOINT is not set (evidence storage is not deployed).")
        return AzureBlobSink(endpoint)
    raise ExportError("--sink must be local:<dir> or azure.")


def _canonical(row: dict[str, Any]) -> str:
    return json.dumps({k: row[k] for k in sorted(row)}, sort_keys=True, separators=(",", ":"), default=str)


def export_next(sink: Any, max_events: int = 50000) -> dict[str, Any]:
    chain = audit.verify_chain()
    if not chain["ok"]:
        raise ExportError(f"Audit chain is broken at event {chain['first_broken_event_id']}; nothing exported.")
    with db.transaction() as conn:
        last = conn.execute(
            "SELECT to_event_id, last_hash FROM audit_exports ORDER BY to_event_id DESC LIMIT 1").fetchone()
        after = int(last["to_event_id"]) if last else 0
        rows = conn.execute("SELECT * FROM audit_events WHERE id > ? ORDER BY id LIMIT ?", (after, int(max_events))).fetchall()
    if not rows:
        return {"exported": 0, "reason": "nothing new"}
    expected_prev = last["last_hash"] if last else audit.GENESIS
    if rows[0]["prev_hash"] != expected_prev:
        raise ExportError("Continuity check failed: the chain does not continue from the last export.")
    body = ("\n".join(_canonical(r) for r in rows) + "\n").encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    first_id, last_id = int(rows[0]["id"]), int(rows[-1]["id"])
    stamp = datetime.now(timezone.utc)
    name = f"audit/{stamp:%Y/%m}/{first_id:012d}-{last_id:012d}.jsonl"
    sink.put(AUDIT_CONTAINER, name, body)
    if hashlib.sha256(sink.get(AUDIT_CONTAINER, name)).hexdigest() != digest:
        raise ExportError(f"Read-back verification failed for {AUDIT_CONTAINER}/{name}; export not recorded.")
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO audit_exports (id, from_event_id, to_event_id, event_count, first_prev_hash, last_hash, sha256, "
            "sink, object_name, exported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), first_id, last_id, len(rows), rows[0]["prev_hash"], rows[-1]["hash"], digest,
             sink.label, f"{AUDIT_CONTAINER}/{name}", stamp.isoformat()),
        )
        audit.append(conn, "system:audit-export", "audit_export.verified", "audit_export", name, "ok", content_hash=digest)
    return {"exported": len(rows), "from_event_id": first_id, "to_event_id": last_id, "object": f"{AUDIT_CONTAINER}/{name}",
            "sha256": digest}


def store_dump(sink: Any, path: str) -> dict[str, Any]:
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    name = f"{datetime.now(timezone.utc):%Y/%m/%d}/{Path(path).name}"
    sink.put(DUMP_CONTAINER, name, data)
    sink.put(DUMP_CONTAINER, name + ".sha256", f"{digest}  {Path(path).name}\n".encode())
    if hashlib.sha256(sink.get(DUMP_CONTAINER, name)).hexdigest() != digest:
        raise ExportError(f"Read-back verification failed for {DUMP_CONTAINER}/{name}.")
    return {"object": f"{DUMP_CONTAINER}/{name}", "sha256": digest, "bytes": len(data)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.audit_export")
    parser.add_argument("--sink", required=True)
    parser.add_argument("--max-events", type=int, default=50000)
    parser.add_argument("--store-dump")
    args = parser.parse_args(argv)
    try:
        sink = sink_from(args.sink)
        result = store_dump(sink, args.store_dump) if args.store_dump else export_next(sink, args.max_events)
    except (ExportError, db.StoreNotConfigured, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps({"ok": True, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
