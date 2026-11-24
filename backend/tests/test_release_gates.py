"""Release gate engine: evidence validation and release blocking. Synthetic evidence only."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from app import release_gates as rg

COMMIT = "a" * 40
OTHER = "b" * 40
TODAY = date(2026, 11, 25)
APPROVERS = {
    "clinical_lead": {"name": "Synthetic Clinician", "role": "clinical_lead", "organisation": "Synthetic Clinic",
                      "registration_id": "SYN-REG-0001"},
    "privacy_officer": {"name": "Synthetic Privacy", "role": "privacy_officer", "organisation": rg.STN_ORGANISATION},
    "security_lead": {"name": "Synthetic Security", "role": "security_lead", "organisation": rg.STN_ORGANISATION},
    "independent_security_tester": {"name": "Synthetic Tester", "role": "independent_security_tester",
                                    "organisation": "Synthetic Testing Ltd"},
    "operations_lead": {"name": "Synthetic Ops", "role": "operations_lead", "organisation": rg.STN_ORGANISATION},
    "release_authoriser": {"name": "Synthetic Owner", "role": "release_authoriser", "organisation": rg.STN_ORGANISATION},
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "release" / "evidence" / "artifacts").mkdir(parents=True)
    return tmp_path


def artifact(repo: Path, name: str) -> tuple[str, str]:
    rel = f"release/evidence/artifacts/{name}.txt"
    data = f"synthetic artifact {name}\n".encode()
    (repo / rel).write_bytes(data)
    return rel, hashlib.sha256(data).hexdigest()


def full_evidence(repo: Path) -> list[dict]:
    records = []
    for gate in rg.GATES:
        for kind in gate.evidence:
            rel, digest = artifact(repo, f"{gate.gate_id}-{kind}")
            rec = {"gate_id": gate.gate_id, "kind": kind, "commit": COMMIT, "artifact": rel,
                   "artifact_sha256": digest, "outcome": "pass", "recorded_by": "Synthetic Engineer",
                   "recorded_on": "2026-11-24"}
            if kind == "approval" or gate.external_approver:
                rec["approver"] = dict(APPROVERS[gate.approvals[0]])
            records.append(rec)
    return records


def decide(repo: Path, records: list[dict], commit: str = COMMIT) -> rg.ReleaseDecision:
    return rg.evaluate(commit, rg.parse_evidence(records), repo, today=TODAY)


def status(decision: rg.ReleaseDecision, gate_id: str) -> rg.GateResult:
    return next(r for r in decision.results if r.gate.gate_id == gate_id)


def test_no_evidence_blocks_every_gate(repo):
    d = decide(repo, [])
    assert not d.allowed
    assert all(r.status == rg.BLOCKED for r in d.results)
    assert set(d.domain_readiness().values()) == {"NOT READY"}
    assert status(d, "G12").missing_approvals == ["clinical_lead"]


def test_complete_valid_evidence_allows_release(repo):
    d = decide(repo, full_evidence(repo))
    assert d.allowed, rg.render_text(d)
    assert set(d.domain_readiness().values()) == {"READY"}
    assert any("does not verify" in n for n in status(d, "G12").notes)


def test_technical_readiness_does_not_imply_clinical(repo):
    records = [r for r in full_evidence(repo) if r["gate_id"] in {"G01", "G02"}]
    d = decide(repo, records)
    assert d.domain_readiness()["technical"] == "READY"
    assert d.domain_readiness()["clinical"] == "NOT READY"
    assert not d.allowed


def test_evidence_for_another_commit_blocks(repo):
    records = full_evidence(repo)
    for r in records:
        if r["gate_id"] == "G01":
            r["commit"] = OTHER
    g = status(decide(repo, records), "G01")
    assert g.status == rg.BLOCKED and "evidence exists only for other commits" in g.reasons


def test_failing_record_fails_gate_and_blocks_g13(repo):
    records = full_evidence(repo)
    bad = copy.deepcopy(next(r for r in records if r["gate_id"] == "G09"))
    bad["outcome"] = "fail"
    records.append(bad)
    d = decide(repo, records)
    assert status(d, "G09").status == rg.FAILED
    assert status(d, "G13").status == rg.BLOCKED and "blocked until G09 pass" in status(d, "G13").reasons
    assert not d.allowed


def test_tampered_artifact_is_rejected(repo):
    records = full_evidence(repo)
    target = next(r for r in records if r["gate_id"] == "G10" and r["kind"] == "restore_drill_report")
    (repo / target["artifact"]).write_text("edited after recording\n")
    g = status(decide(repo, records), "G10")
    assert g.status == rg.BLOCKED and any("does not match" in x for x in g.reasons)


def test_missing_artifact_and_path_escape_are_rejected(repo):
    records = full_evidence(repo)
    a = next(r for r in records if r["gate_id"] == "G01" and r["kind"] == "test_report")
    a["artifact"] = "release/evidence/artifacts/not-there.txt"
    b = next(r for r in records if r["gate_id"] == "G02" and r["kind"] == "test_report")
    b["artifact"] = "../outside.txt"
    d = decide(repo, records)
    assert any("does not exist" in x for x in status(d, "G01").reasons)
    assert any("inside the repository" in x for x in status(d, "G02").reasons)


def test_self_approval_is_rejected(repo):
    records = full_evidence(repo)
    rec = next(r for r in records if r["gate_id"] == "G12")
    rec["recorded_by"] = rec["approver"]["name"]
    g = status(decide(repo, records), "G12")
    assert g.status == rg.BLOCKED and any("cannot be the person" in x for x in g.reasons)


def test_clinical_approval_needs_registration(repo):
    records = full_evidence(repo)
    del next(r for r in records if r["gate_id"] == "G06" and r["kind"] == "approval")["approver"]["registration_id"]
    g = status(decide(repo, records), "G06")
    assert g.status == rg.BLOCKED and "clinical_lead" in g.missing_approvals


def test_wrong_role_does_not_satisfy_approval(repo):
    records = full_evidence(repo)
    rec = next(r for r in records if r["gate_id"] == "G12")
    rec["approver"] = dict(APPROVERS["operations_lead"])
    g = status(decide(repo, records), "G12")
    assert g.status == rg.BLOCKED and g.missing_approvals == ["clinical_lead"]


def test_pen_test_must_be_independent(repo):
    records = full_evidence(repo)
    next(r for r in records if r["gate_id"] == "G08")["approver"]["organisation"] = rg.STN_ORGANISATION
    g = status(decide(repo, records), "G08")
    assert g.status == rg.BLOCKED and any("independent of STN" in x for x in g.reasons)


def test_external_artifact_is_accepted_but_flagged(repo):
    records = full_evidence(repo)
    rec = next(r for r in records if r["gate_id"] == "G08")
    rec["artifact"] = "https://example.org/synthetic-pen-test-report.pdf"
    g = status(decide(repo, records), "G08")
    assert g.status == rg.PASSED and any("not verified by the engine" in n for n in g.notes)
    rec["artifact"] = "http://example.org/report.pdf"
    assert status(decide(repo, records), "G08").status == rg.BLOCKED


def test_future_date_and_wrong_kind_are_rejected(repo):
    records = full_evidence(repo)
    next(r for r in records if r["gate_id"] == "G01")["recorded_on"] = "2027-01-01"
    next(r for r in records if r["gate_id"] == "G02")["kind"] = "pen_test_report"
    d = decide(repo, records)
    assert any("in the future" in x for x in status(d, "G01").reasons)
    assert any("not used by G02" in x for x in status(d, "G02").reasons)


def test_malformed_evidence_is_an_error(repo):
    with pytest.raises(rg.EvidenceError):
        rg.parse_evidence({"not": "a list"})
    with pytest.raises(rg.EvidenceError):
        rg.parse_evidence([{"gate_id": "G01"}])
    with pytest.raises(rg.EvidenceError):
        decide(repo, [dict(full_evidence(repo)[0], gate_id="G99")])
    with pytest.raises(rg.EvidenceError):
        decide(repo, [], commit="HEAD")


def test_cli_exit_codes_and_dashboard(repo, tmp_path, capsys):
    ev = tmp_path / "ev.json"
    ev.write_text("[]")
    assert rg.main(["--commit", COMMIT, "--evidence", str(ev), "--repo-root", str(repo)]) == 1
    assert "RELEASE BLOCKED" in capsys.readouterr().out
    out = tmp_path / "dash.md"
    assert rg.main(["--commit", COMMIT, "--evidence", str(ev), "--repo-root", str(repo),
                    "--format", "markdown", "--output", str(out)]) == 1
    text = out.read_text()
    assert "| Clinical | NOT READY |" in text and "Technical readiness does not imply clinical" in text
    ev.write_text(json.dumps(full_evidence(repo)))
    # Evidence is dated before TODAY in tests; the CLI uses the real date, which is later.
    assert rg.main(["--commit", COMMIT, "--evidence", str(ev), "--repo-root", str(repo), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["allowed"] is True
    ev.write_text("not json")
    assert rg.main(["--commit", COMMIT, "--evidence", str(ev), "--repo-root", str(repo)]) == 2


def test_committed_evidence_file_blocks_current_release():
    root = Path(__file__).resolve().parents[2]
    records = rg.load_evidence(root / "release" / "evidence" / "current.json")
    d = rg.evaluate(COMMIT, records, root)
    assert not d.allowed


def test_gate_definitions_are_consistent():
    assert [g.gate_id for g in rg.GATES] == [f"G{i:02d}" for i in range(1, 14)]
    for g in rg.GATES:
        assert g.domain in rg.DOMAINS and set(g.evidence) <= rg.EVIDENCE_KINDS and set(g.approvals) <= rg.APPROVER_ROLES
        if g.approvals and not g.external_approver:
            assert "approval" in g.evidence, f"{g.gate_id} needs an approval record to carry its approver"
