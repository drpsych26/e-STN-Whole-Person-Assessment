"""Release gate engine G01-G13 with evidence validation and a readiness dashboard.

A gate passes only when the evidence for the exact release commit is complete and valid.
Status is derived from evidence every time; it is never stored or set by hand.

What the engine checks (and does not check):
- Each gate lists the evidence kinds it needs and the approvals it needs (by role).
- Every record must name the release commit, an artifact and an outcome (pass or fail).
- Artifacts inside the repository (a relative path) must exist at the evaluated checkout and
  match the recorded SHA-256. Artifacts outside it (an https URL) must carry a SHA-256 of the
  document; the engine cannot fetch or verify them and says so in the result.
- Approvals need an approver name, role and organisation, an approver who is not the person
  who recorded the evidence, and a digest-pinned signed record as the artifact. Clinical
  approvals also need a professional registration identifier. The engine checks that these
  are present and consistent; it cannot confirm anyone's identity or registration. Those
  are verified by the people accountable for the gate.
- G08 (penetration test) must come from an organisation other than STN.
- G13 (final release authorisation) is blocked until G01-G12 have all passed.
- A failing record for the commit fails the gate, whatever else is recorded.

Technical readiness never implies clinical readiness: the dashboard reports each domain
separately, and the release is allowed only when every gate has passed.

Usage:
  python -m app.release_gates --commit <sha> --evidence <file.json> [--repo-root DIR]
                              [--format text|markdown|json] [--output FILE]
Exit status 0 only when every gate passed; 1 when the release is blocked; 2 on bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

STN_ORGANISATION = "Supportive Therapy Network Limited"
DOMAINS = ("technical", "security", "privacy", "clinical", "deployment", "release")

EVIDENCE_KINDS = frozenset({
    "ci_run", "test_report", "uat_record", "idp_integration_report", "scoring_verification_report",
    "instrument_licence_register", "privacy_impact_assessment", "pen_test_report", "defect_register",
    "restore_drill_report", "infrastructure_validation_report", "approval",
})
APPROVER_ROLES = frozenset({
    "clinical_lead", "privacy_officer", "security_lead", "independent_security_tester",
    "operations_lead", "release_authoriser",
})
CLINICAL_ROLES = frozenset({"clinical_lead"})


@dataclass(frozen=True)
class Gate:
    gate_id: str
    name: str
    domain: str
    purpose: str
    evidence: tuple[str, ...]
    approvals: tuple[str, ...] = ()
    external_approver: bool = False
    requires_all_prior: bool = False


GATES: tuple[Gate, ...] = (
    Gate("G01", "Backend implementation complete", "technical",
         "The API, database and migrations for this release build and pass their full test suite.",
         ("ci_run", "test_report")),
    Gate("G02", "Customer onboarding verified", "technical",
         "Client registration, identity verification, consent and activation work end to end.",
         ("test_report", "uat_record")),
    Gate("G03", "Authentication and permissions verified", "security",
         "Sign-in, MFA, roles, organisation separation and record-level access work against the real identity provider.",
         ("test_report", "idp_integration_report", "approval"), ("security_lead",)),
    Gate("G04", "Clinical workflows validated", "clinical",
         "Assessment, review, sign-off and care-planning workflows are validated by clinicians in user acceptance testing.",
         ("uat_record", "approval"), ("clinical_lead",)),
    Gate("G05", "Assessment scoring verified", "clinical",
         "Every active instrument is licensed and its server-side scoring matches authoritative worked examples.",
         ("scoring_verification_report", "instrument_licence_register", "approval"), ("clinical_lead",)),
    Gate("G06", "Safety escalation verified", "clinical",
         "The escalation matrix is clinically approved and the escalation pathways pass end-to-end tests.",
         ("test_report", "approval"), ("clinical_lead",)),
    Gate("G07", "Privacy and security review passed", "privacy",
         "Privacy impact assessment completed and approved under the Privacy Act 2020 and HIPC 2020.",
         ("privacy_impact_assessment", "approval"), ("privacy_officer",)),
    Gate("G08", "Independent penetration testing passed", "security",
         "An independent tester has tested the release and no critical or high finding remains open.",
         ("pen_test_report",), ("independent_security_tester",), external_approver=True),
    Gate("G09", "All critical/high defects resolved and retested", "security",
         "The defect register shows no open critical or high defect, each with retest evidence.",
         ("defect_register", "approval"), ("security_lead",)),
    Gate("G10", "Database backup and restoration verified", "deployment",
         "A real restore of the target environment's database has been performed and verified.",
         ("restore_drill_report", "approval"), ("operations_lead",)),
    Gate("G11", "Production infrastructure validated", "deployment",
         "Production infrastructure is provisioned as defined and validated (TLS, keys, network, monitoring).",
         ("infrastructure_validation_report", "approval"), ("operations_lead",)),
    Gate("G12", "Clinical governance approval obtained", "clinical",
         "The accountable clinical lead approves this release for its stated clinical scope.",
         ("approval",), ("clinical_lead",)),
    Gate("G13", "Final production release authorisation", "release",
         "The owner authorises production release of this exact commit.",
         ("approval",), ("release_authoriser",), requires_all_prior=True),
)
GATE_IDS = {g.gate_id for g in GATES}

PASSED, FAILED, BLOCKED = "PASSED", "FAILED", "BLOCKED"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EvidenceError(ValueError):
    """The evidence file itself is malformed (exit status 2)."""


@dataclass(frozen=True)
class Evidence:
    gate_id: str
    kind: str
    commit: str
    artifact: str
    artifact_sha256: str
    outcome: str
    recorded_by: str
    recorded_on: str
    approver: dict[str, str] | None = None


@dataclass
class GateResult:
    gate: Gate
    status: str
    reasons: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    missing_approvals: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ReleaseDecision:
    commit: str
    results: list[GateResult]

    @property
    def allowed(self) -> bool:
        return all(r.status == PASSED for r in self.results)

    def domain_readiness(self) -> dict[str, str]:
        out = {}
        for domain in DOMAINS:
            statuses = [r.status for r in self.results if r.gate.domain == domain]
            out[domain] = "READY" if statuses and all(s == PASSED for s in statuses) else "NOT READY"
        return out


def parse_evidence(items: Any) -> list[Evidence]:
    if not isinstance(items, list):
        raise EvidenceError("Evidence file must contain a JSON list of records.")
    records = []
    required = ("gate_id", "kind", "commit", "artifact", "artifact_sha256", "outcome", "recorded_by", "recorded_on")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise EvidenceError(f"Record {index} is not an object.")
        unknown = set(item) - set(required) - {"approver"}
        if unknown:
            raise EvidenceError(f"Record {index} has unknown fields: {', '.join(sorted(unknown))}.")
        missing = [k for k in required if not isinstance(item.get(k), str) or not item[k].strip()]
        if missing:
            raise EvidenceError(f"Record {index} is missing: {', '.join(missing)}.")
        approver = item.get("approver")
        if approver is not None and (not isinstance(approver, dict)
                                     or not all(isinstance(v, str) for v in approver.values())):
            raise EvidenceError(f"Record {index}: approver must be an object of strings.")
        records.append(Evidence(**{k: item[k].strip() for k in required}, approver=approver))
    return records


def load_evidence(path: Path) -> list[Evidence]:
    try:
        return parse_evidence(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"{path} is not valid JSON: {exc}") from exc


def _record_problems(e: Evidence, gate: Gate, repo_root: Path, today: date) -> tuple[list[str], list[str]]:
    """Return (problems, notes) for one record. Any problem makes the record invalid."""
    problems: list[str] = []
    notes: list[str] = []
    label = f"{e.kind} record by {e.recorded_by}"
    if e.kind not in EVIDENCE_KINDS:
        problems.append(f"{label}: unknown evidence kind")
    elif e.kind not in gate.evidence:
        problems.append(f"{label}: kind is not used by {gate.gate_id}")
    if e.outcome not in {"pass", "fail"}:
        problems.append(f"{label}: outcome must be 'pass' or 'fail'")
    try:
        recorded = date.fromisoformat(e.recorded_on)
        if recorded > today:
            problems.append(f"{label}: recorded_on is in the future")
    except ValueError:
        problems.append(f"{label}: recorded_on must be YYYY-MM-DD")
    if not _SHA256.match(e.artifact_sha256):
        problems.append(f"{label}: artifact_sha256 must be 64 lowercase hex characters")
    elif e.artifact.startswith("https://"):
        notes.append(f"{label}: external artifact {e.artifact} - digest recorded, not verified by the engine")
    elif e.artifact.startswith(("http://", "file:")) or "://" in e.artifact:
        problems.append(f"{label}: artifact must be a repository path or an https URL")
    else:
        rel = PurePosixPath(e.artifact)
        if rel.is_absolute() or ".." in rel.parts:
            problems.append(f"{label}: artifact path must be relative and inside the repository")
        else:
            target = repo_root / rel
            if not target.is_file():
                problems.append(f"{label}: artifact {e.artifact} does not exist at this checkout")
            elif hashlib.sha256(target.read_bytes()).hexdigest() != e.artifact_sha256:
                problems.append(f"{label}: artifact {e.artifact} does not match its recorded SHA-256")
    if e.kind == "approval" or gate.external_approver:
        a = e.approver or {}
        for key in ("name", "role", "organisation"):
            if not a.get(key, "").strip():
                problems.append(f"{label}: approver.{key} is required")
        role = a.get("role", "")
        if role and role not in APPROVER_ROLES:
            problems.append(f"{label}: approver role '{role}' is not recognised")
        if role in CLINICAL_ROLES:
            if not a.get("registration_id", "").strip():
                problems.append(f"{label}: clinical approvals need approver.registration_id")
            else:
                notes.append(f"{label}: registration {a['registration_id']} must be checked on the public register; "
                             "the engine does not verify it")
        if a.get("name", "").strip().lower() == e.recorded_by.strip().lower():
            problems.append(f"{label}: the approver cannot be the person who recorded the evidence")
        if gate.external_approver and a.get("organisation", "").strip().lower() == STN_ORGANISATION.lower():
            problems.append(f"{label}: {gate.gate_id} must be carried out by an organisation independent of STN")
    return problems, notes


def evaluate(commit: str, evidence: Iterable[Evidence], repo_root: Path, today: date | None = None) -> ReleaseDecision:
    if not _SHA40.match(commit):
        raise EvidenceError("The release commit must be 40 lowercase hexadecimal characters.")
    today = today or date.today()
    records = list(evidence)
    for e in records:
        if e.gate_id not in GATE_IDS:
            raise EvidenceError(f"Unknown gate {e.gate_id!r} in evidence.")
    results: list[GateResult] = []
    for gate in GATES:
        result = GateResult(gate, BLOCKED)
        mine = [e for e in records if e.gate_id == gate.gate_id]
        current = [e for e in mine if e.commit == commit]
        if mine and not current:
            result.reasons.append("evidence exists only for other commits")
        valid: list[Evidence] = []
        for e in current:
            problems, notes = _record_problems(e, gate, repo_root, today)
            result.notes.extend(notes)
            if problems:
                result.reasons.extend(problems)
            else:
                valid.append(e)
        failing = [e for e in valid if e.outcome == "fail"]
        passing = [e for e in valid if e.outcome == "pass"]
        result.missing_evidence = [k for k in gate.evidence if not any(e.kind == k for e in passing)]
        approved_roles = {(e.approver or {}).get("role") for e in passing if e.approver}
        result.missing_approvals = [r for r in gate.approvals if r not in approved_roles]
        if gate.requires_all_prior:
            not_passed = [r.gate.gate_id for r in results if r.status != PASSED]
            if not_passed:
                result.reasons.append(f"blocked until {', '.join(not_passed)} pass")
        if failing:
            result.status = FAILED
            result.reasons.insert(0, f"{len(failing)} failing record(s) for this commit")
        elif not current and not mine:
            result.reasons.insert(0, "no evidence recorded")
        if result.status != FAILED and not result.missing_evidence and not result.missing_approvals \
                and not result.reasons:
            result.status = PASSED
        results.append(result)
    return ReleaseDecision(commit, results)


def render_text(d: ReleaseDecision) -> str:
    lines = []
    for r in d.results:
        why = "; ".join(r.reasons + [f"missing evidence: {', '.join(r.missing_evidence)}"] * bool(r.missing_evidence)
                        + [f"missing approval: {', '.join(r.missing_approvals)}"] * bool(r.missing_approvals))
        lines.append(f"{r.gate.gate_id} {r.status:8} {r.gate.name}{' - ' + why if why else ''}")
    lines.append(f"RELEASE {'ALLOWED' if d.allowed else 'BLOCKED'} for {d.commit}")
    return "\n".join(lines)


def render_markdown(d: ReleaseDecision) -> str:
    counts = {s: sum(r.status == s for r in d.results) for s in (PASSED, FAILED, BLOCKED)}
    out = [
        "# STN release readiness",
        "",
        f"**Release commit:** `{d.commit}`  ",
        f"**Decision:** {'RELEASE ALLOWED' if d.allowed else 'RELEASE BLOCKED'}  ",
        f"**Gates:** {counts[PASSED]} passed, {counts[FAILED]} failed, {counts[BLOCKED]} blocked",
        "",
        "Generated by `python -m app.release_gates` from committed evidence. Technical readiness does not "
        "imply clinical, privacy or release approval; each domain is reported separately.",
        "",
        "## Readiness by domain",
        "",
        "| Domain | Readiness | Gates |",
        "|---|---|---|",
    ]
    for domain, state in d.domain_readiness().items():
        gates = ", ".join(f"{r.gate.gate_id} {r.status.lower()}" for r in d.results if r.gate.domain == domain)
        out.append(f"| {domain.capitalize()} | {state} | {gates} |")
    out += ["", "## Gates", "", "| Gate | Domain | Status | Missing evidence | Missing approvals | Reasons |",
            "|---|---|---|---|---|---|"]
    for r in d.results:
        cell = lambda xs: "<br>".join(xs).replace("|", "\\|") if xs else "-"  # noqa: E731
        out.append(f"| {r.gate.gate_id} {r.gate.name} | {r.gate.domain} | **{r.status}** | {cell(r.missing_evidence)} "
                   f"| {cell(r.missing_approvals)} | {cell(r.reasons)} |")
    notes = [n for r in d.results for n in r.notes]
    if notes:
        out += ["", "## Items the engine could not verify", ""] + [f"- {n}" for n in notes]
    out += ["", "## Gate definitions", "", "| Gate | Purpose | Evidence | Approvals |", "|---|---|---|---|"]
    for g in GATES:
        extra = " (approver must be independent of STN)" if g.external_approver else ""
        extra += " (only after G01-G12 pass)" if g.requires_all_prior else ""
        out.append(f"| {g.gate_id} | {g.purpose} | {', '.join(g.evidence)} | {', '.join(g.approvals) or '-'}{extra} |")
    return "\n".join(out) + "\n"


def render_json(d: ReleaseDecision) -> str:
    return json.dumps({
        "commit": d.commit,
        "allowed": d.allowed,
        "domains": d.domain_readiness(),
        "gates": [{"gate_id": r.gate.gate_id, "name": r.gate.name, "domain": r.gate.domain, "status": r.status,
                   "missing_evidence": r.missing_evidence, "missing_approvals": r.missing_approvals,
                   "reasons": r.reasons, "notes": r.notes} for r in d.results],
    }, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.release_gates", description=__doc__.split("\n\n")[0])
    parser.add_argument("--commit", required=True)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        decision = evaluate(args.commit, load_evidence(args.evidence), args.repo_root.resolve())
    except (EvidenceError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = {"text": render_text, "markdown": render_markdown, "json": render_json}[args.format](decision)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered if rendered.endswith("\n") else rendered + "\n")
    return 0 if decision.allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
