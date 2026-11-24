"""Audit-chain export to write-once storage: verification, continuity, tamper refusal. Local sink only."""
from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app import audit_export
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def make_events(act, n=3):
    act("clin-ae", "clinician")
    for i in range(n):
        client.post("/v1/clients", json={"display_code": f"SYN-AE-{i}"})


def test_export_verify_and_continue(backend, act, tmp_path, raw):
    sink = audit_export.LocalSink(str(tmp_path))
    make_events(act)
    first = audit_export.export_next(sink)
    assert first["exported"] > 0 and first["from_event_id"] == 1
    stored = (tmp_path / first["object"]).read_bytes()
    assert hashlib.sha256(stored).hexdigest() == first["sha256"]
    lines = [json.loads(line) for line in stored.decode().splitlines()]
    assert lines[0]["prev_hash"] == "0" * 64 and all("ciphertext" not in line for line in lines)
    assert audit_export.export_next(sink)["exported"] == 1  # only the export's own audit event is new
    make_events(act, 2)
    third = audit_export.export_next(sink)
    rows = raw("SELECT from_event_id, to_event_id, first_prev_hash, last_hash FROM audit_exports ORDER BY from_event_id")
    assert len(rows) == 3
    for prev, nxt in zip(rows, rows[1:]):
        assert nxt[0] == prev[1] + 1 and nxt[2] == prev[3]  # contiguous ranges, hash continuity
    assert third["to_event_id"] == rows[-1][1]


def test_broken_chain_is_never_exported(backend, act, tmp_path, raw):
    make_events(act)
    if backend == "sqlite":
        raw("DROP TRIGGER IF EXISTS audit_events_no_update")
        for (name,) in raw("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='audit_events'"):
            raw(f"DROP TRIGGER {name}")
    else:
        raw("ALTER TABLE audit_events DISABLE TRIGGER USER")
    raw("UPDATE audit_events SET outcome = 'tampered' WHERE id = 2")
    with pytest.raises(audit_export.ExportError, match="broken at event 2"):
        audit_export.export_next(audit_export.LocalSink(str(tmp_path)))
    assert raw("SELECT COUNT(*) FROM audit_exports")[0][0] == 0
    assert not any(tmp_path.rglob("*.jsonl"))


def test_write_once_and_readback_failure(backend, act, tmp_path, raw):
    make_events(act)
    sink = audit_export.LocalSink(str(tmp_path))

    class Corrupting(audit_export.LocalSink):
        def get(self, container, name):
            return b"corrupted"

    with pytest.raises(audit_export.ExportError, match="Read-back verification failed"):
        audit_export.export_next(Corrupting(str(tmp_path)))
    assert raw("SELECT COUNT(*) FROM audit_exports")[0][0] == 0  # not recorded, so the next run retries
    with pytest.raises(audit_export.ExportError, match="cannot be overwritten"):
        audit_export.export_next(sink)  # same range, object already there: refused, not overwritten
    assert audit_export.export_next(audit_export.LocalSink(str(tmp_path / "fresh")))["exported"] > 0
    with pytest.raises(Exception):
        raw("DELETE FROM audit_exports")  # the export register is append-only


def test_cli_and_dump_storage(backend, act, tmp_path, capsys):
    make_events(act)
    assert audit_export.main(["--sink", f"local:{tmp_path}"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    dump = tmp_path / "stn.dump"
    dump.write_bytes(b"synthetic dump bytes")
    assert audit_export.main(["--sink", f"local:{tmp_path}", "--store-dump", str(dump)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sha256"] == hashlib.sha256(b"synthetic dump bytes").hexdigest()
    assert audit_export.main(["--sink", "azure"]) == 1  # not deployed: fails closed with a clear error
    assert "not set" in json.loads(capsys.readouterr().out)["error"]
    assert audit_export.main(["--sink", "ftp://x"]) == 1


def test_azure_sink_uses_create_only_writes(monkeypatch):
    sink = audit_export.AzureBlobSink("https://ststnevstg.blob.core.windows.net")
    monkeypatch.setattr(sink, "_token", lambda: "synthetic-token")
    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b""

    def fake_urlopen(request, timeout):
        seen.update(method=request.get_method(), url=request.full_url, headers=dict(request.header_items()))
        return Resp()

    monkeypatch.setattr(audit_export.urllib.request, "urlopen", fake_urlopen)
    sink.put("audit-exports", "audit/x.jsonl", b"data")
    assert seen["method"] == "PUT" and seen["url"].endswith("/audit-exports/audit/x.jsonl")
    assert seen["headers"]["If-none-match"] == "*" and seen["headers"]["Authorization"] == "Bearer synthetic-token"
    with pytest.raises(audit_export.ExportError):
        audit_export.AzureBlobSink("http://insecure.example")
