"""Release gate engine tests. Synthetic evidence only."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.release_gates import GATES, Evidence, evaluate, load_evidence, main

COMMIT = "a" * 40
OTHER = "b" * 40


def ev(gate, commit=COMMIT, outcome="pass", ref="artifact://test-report-1"):
    return Evidence(gate, commit, ref, outcome, "tester-1", "2026-11-21")


def all_passing(commit=COMMIT):
    return [ev(g, commit) for g in GATES]


def test_no_evidence_blocks_every_gate():
    decision = evaluate(COMMIT, [])
    assert not decision.allowed
    assert len(decision.blocked) == len(GATES) == 13


def test_all_thirteen_gates_defined():
    assert list(GATES) == [f"G{n:02d}" for n in range(1, 14)]


def test_full_passing_evidence_allows_release():
    decision = evaluate(COMMIT, all_passing())
    assert decision.allowed
    assert decision.blocked == []


def test_evidence_for_other_commit_does_not_pass():
    decision = evaluate(COMMIT, all_passing(commit=OTHER))
    assert not decision.allowed
    assert all("other commits" in r.reason for r in decision.blocked)


def test_failing_evidence_blocks_even_with_passing_record():
    evidence = all_passing() + [ev("G09", outcome="fail", ref="artifact://retest-2")]
    decision = evaluate(COMMIT, evidence)
    blocked = {r.gate_id: r for r in decision.blocked}
    assert set(blocked) == {"G09"}
    assert "failing evidence" in blocked["G09"].reason


def test_one_missing_gate_blocks_release():
    evidence = [e for e in all_passing() if e.gate_id != "G08"]
    decision = evaluate(COMMIT, evidence)
    assert [r.gate_id for r in decision.blocked] == ["G08"]


def test_unknown_gate_is_rejected():
    with pytest.raises(ValueError, match="Unknown gate"):
        ev("G99")


def test_invalid_outcome_is_rejected():
    with pytest.raises(ValueError, match="Outcome"):
        ev("G01", outcome="passed")


@pytest.mark.parametrize("field", ["commit", "artifact_ref", "recorded_by", "recorded_on"])
def test_evidence_requires_every_reference_field(field):
    values = dict(gate_id="G01", commit=COMMIT, artifact_ref="artifact://x",
                  outcome="pass", recorded_by="tester", recorded_on="2026-11-21")
    values[field] = "   "
    with pytest.raises(ValueError, match=field):
        Evidence(**values)


def test_empty_release_commit_is_rejected():
    with pytest.raises(ValueError, match="release commit"):
        evaluate("  ", [])


def test_status_is_derived_not_settable():
    decision = evaluate(COMMIT, [])
    assert all(r.status == "BLOCKED" for r in decision.results)
    with pytest.raises(AttributeError):
        decision.results[0].status = "PASSED"  # frozen dataclass


def test_cli_blocks_and_allows(tmp_path: Path, capsys):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps([e.__dict__ for e in all_passing()[:5]]), encoding="utf-8")
    assert main(["x", COMMIT, str(path)]) == 1
    assert "RELEASE BLOCKED" in capsys.readouterr().out

    path.write_text(json.dumps([e.__dict__ for e in all_passing()]), encoding="utf-8")
    assert main(["x", COMMIT, str(path)]) == 0
    assert "RELEASE ALLOWED" in capsys.readouterr().out


def test_cli_usage_error():
    assert main(["x"]) == 2
