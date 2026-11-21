"""Release gate engine G01-G13.

A gate is PASSED only when linked, version-specific evidence exists for it. The
status is derived from the evidence and is never stored as a manually set flag.
Evidence must name the release commit it covers, the artifact it points to, and
its outcome. A gate with failing evidence, evidence for another commit, or no
evidence is blocked.

This module does not decide whether a gate's underlying work is sound. It only
checks that the evidence exists, matches the release, and reports a pass.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

GATES: dict[str, str] = {
    "G01": "Backend implementation complete",
    "G02": "Customer onboarding verified",
    "G03": "Authentication and permissions verified",
    "G04": "Clinical workflows validated",
    "G05": "Assessment scoring verified",
    "G06": "Safety escalation verified",
    "G07": "Privacy and security review passed",
    "G08": "Independent penetration testing passed",
    "G09": "All critical/high defects resolved and retested",
    "G10": "Database backup and restoration verified",
    "G11": "Production infrastructure validated",
    "G12": "Clinical governance approval obtained",
    "G13": "Final production release authorisation",
}

PASS = "pass"
FAIL = "fail"
VALID_OUTCOMES = {PASS, FAIL}


@dataclass(frozen=True)
class Evidence:
    gate_id: str
    commit: str
    artifact_ref: str
    outcome: str
    recorded_by: str
    recorded_on: str

    def __post_init__(self) -> None:
        if self.gate_id not in GATES:
            raise ValueError(f"Unknown gate: {self.gate_id}")
        if self.outcome not in VALID_OUTCOMES:
            raise ValueError(f"Outcome must be 'pass' or 'fail', got {self.outcome!r}")
        for name in ("commit", "artifact_ref", "recorded_by", "recorded_on"):
            if not getattr(self, name).strip():
                raise ValueError(f"Evidence for {self.gate_id} is missing '{name}'")


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    name: str
    status: str  # "PASSED" or "BLOCKED"
    reason: str


@dataclass(frozen=True)
class ReleaseDecision:
    commit: str
    results: tuple[GateResult, ...]

    @property
    def allowed(self) -> bool:
        return all(r.status == "PASSED" for r in self.results)

    @property
    def blocked(self) -> list[GateResult]:
        return [r for r in self.results if r.status != "PASSED"]


def evaluate(commit: str, evidence: Iterable[Evidence]) -> ReleaseDecision:
    """Derive each gate's status for a release candidate commit."""
    if not commit.strip():
        raise ValueError("A release commit is required")
    by_gate: dict[str, list[Evidence]] = {gid: [] for gid in GATES}
    for item in evidence:
        by_gate[item.gate_id].append(item)

    results = []
    for gid, name in GATES.items():
        records = by_gate[gid]
        for_commit = [e for e in records if e.commit == commit]
        if not records:
            results.append(GateResult(gid, name, "BLOCKED", "no evidence recorded"))
        elif not for_commit:
            results.append(GateResult(gid, name, "BLOCKED", "evidence exists only for other commits"))
        elif any(e.outcome == FAIL for e in for_commit):
            results.append(GateResult(gid, name, "BLOCKED", "failing evidence recorded for this commit"))
        else:
            results.append(GateResult(gid, name, "PASSED", f"{len(for_commit)} passing evidence record(s)"))
    return ReleaseDecision(commit=commit, results=tuple(results))


def load_evidence(path: Path) -> list[Evidence]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Evidence file must contain a JSON list")
    return [Evidence(**item) for item in data]


def main(argv: list[str]) -> int:
    """Usage: python -m app.release_gates <commit> <evidence.json>

    Exit 0 only when every mandatory gate has passing evidence for the commit.
    """
    if len(argv) != 3:
        print("usage: python -m app.release_gates <commit> <evidence.json>", file=sys.stderr)
        return 2
    decision = evaluate(argv[1], load_evidence(Path(argv[2])))
    for r in decision.results:
        print(f"{r.gate_id} {r.status:8} {r.name} - {r.reason}")
    if decision.allowed:
        print(f"RELEASE ALLOWED for {decision.commit}")
        return 0
    print(f"RELEASE BLOCKED for {decision.commit}: {len(decision.blocked)} gate(s) not passed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
