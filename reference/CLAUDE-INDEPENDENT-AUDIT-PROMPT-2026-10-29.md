# Claude independent audit — STN

Act as an independent senior software assurance, clinical safety, privacy and release engineer. Audit the entire private repository `drpsych26/e-STN-Whole-Person-Assessment` and the STN release candidate package. Inspect actual source and tests; do not rely on README claims alone.

## Rules

- Treat the approved paper pilot and designated baseline assessment HTML as content source-of-truth. Preserve questions, response options, markers, scoring, routing and report semantics unless an approved change is recorded.
- Separate screening, clinician formulation, diagnostic indication and formal diagnosis.
- Safety flags must lead to a human-operated workflow; a badge or score is not a response.
- Do not infer clinical validation, legal compliance, agency integration, partnership, regulatory approval or production readiness from code or marketing copy.
- Use synthetic data only. Do not deploy, publish or merge to the protected default branch without explicit approval.
- Never claim zero bugs; state evidence and limitations.

## Required audit

1. Compare branches, commits, imported source assets, manifests and hashes. Report missing, stale or divergent files.
2. Trace every workflow, marker, scoring rule, route and report to code and automated tests.
3. Review navigation, state, validation, persistence, exports, unsafe HTML rendering/XSS, cross-client leakage and error handling.
4. Independently verify scoring fixtures and test missing, declined, contradictory, boundary and extreme responses.
5. Review positive/ambiguous risk responses, human escalation, acknowledgement, fallback, outage handling and false reassurance.
6. Inspect Flutter dependencies, package constraints, analyzer/build/test status and platform risks.
7. Threat-model identity, authorisation, storage, exports, backups, integrations and operations. Review privacy, consent, retention, audit, encryption, secrets, recovery and incident response.
8. Run available tests and report exact commands, tool versions and results. Mark unavailable tests NOT RUN; never call them PASS.

## Deliverables

- Verdict: HOLD / prototype demo / internal alpha / supervised-pilot candidate / production candidate.
- Severity-ranked findings with file/line, evidence, impact, reproduction and proposed fix.
- Requirement-to-code-to-test traceability matrix.
- Source integrity/divergence report.
- Clinical safety and security/privacy review.
- Test results and explicit unrun-test list.
- Ordered remediation plan with acceptance criteria.
- Regression tests and proposed PRs for fixes where feasible; preserve clinical content unless explicitly authorised.
- Updated release register, leaving gates open unless evidence and named sign-off exist.

Lead with any safety-critical finding. Do not state “no bugs”, “fully compliant”, “clinically validated”, “production ready”, or “approved by Health NZ/Corrections” without appropriate evidence.