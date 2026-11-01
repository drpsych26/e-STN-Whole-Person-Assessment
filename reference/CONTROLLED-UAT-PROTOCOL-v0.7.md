# STN Controlled UAT Protocol — v0.7

**Status:** Private, non-live development and usability testing only
**Permitted test data:** Synthetic cases only
**Not authorised:** Clinical care, diagnosis, triage, risk clearance, real-client record keeping, or use with identifiable health information.

## Purpose

This protocol supports structured staff testing of the STN browser prototype. It is not a clinical pilot protocol and does not authorise use with patients.

## Hard boundaries

- Use invented names, dates of birth, IDs and case narratives. Never use real names, initials, contact details, NHI numbers, addresses, screenshots of clinical records, or combinations that could identify a person.
- Do not enter real patient information, even if the repository and application are private.
- Do not use outputs to make or influence diagnosis, triage, referral, treatment, discharge or safety decisions.
- The safety screen is a workflow prompt only. It does not contact, assign, notify or hand over to a clinician.
- Browser local storage is not a clinical record system. Use a dedicated test browser profile/device and clear it after each test.
- Do not publish the prototype or share its test reports as clinical validation evidence.

## Test roles

1. **UAT facilitator:** controls the test session and records defects.
2. **Clinical reviewer:** checks wording, workflow clarity and whether limitations are visible; does not treat the prototype as clinically approved.
3. **Tester:** completes synthetic scenarios and records usability issues.
4. **Technical reviewer:** verifies storage, rendering, export and failure handling.

## Required synthetic scenarios

| Scenario | Input | Expected behaviour |
|---|---|---|
| S01 — baseline | All safety items = No | Results may display; screen explicitly says a negative screen is not safety clearance |
| S02 — positive | One item = Yes | Human-review flag remains visible; no automated disposition |
| S03 — uncertain | One item = Unsure | Human-review flag remains visible |
| S04 — declined | One item = Declined | Human-review flag remains visible |
| S05 — not asked | One item = Not asked | Human-review flag remains visible |
| S06 — incomplete | One item unanswered | Safety save and results remain blocked |
| S07 — storage failure | Browser storage unavailable | Workflow stops; unsaved responses are not treated as saved |
| S08 — report escaping | HTML-like text in notes | Output renders as escaped text, not executable markup |
| S09 — changed review | Edit review after save | Care-plan progression is blocked until review is saved again |
| S10 — changed care plan | Edit plan after save | Report progression is blocked until care plan is saved again |

## Acceptance evidence

For each test, record:
- app commit / version and browser/device;
- synthetic scenario ID;
- expected and observed behaviour;
- pass/fail and reproducible steps;
- screenshot with synthetic data only, if needed;
- defect severity, owner and remediation commit.

## If a real-patient evaluation is later proposed

That is a separate project gate. It requires a written intended-use statement, approved study/pilot protocol, ethics and organisational approvals as applicable, privacy impact assessment, consent materials, instrument permissions, independent clinical safety review, trained supervision, incident/stop criteria, secure approved data environment, and signed go/no-go approval by accountable clinical, privacy, security and organisational owners. This UAT protocol does not grant that approval.

## Current decision

**Suitable for private synthetic-data workflow and usability testing only. Not authorised for patients or clinical care.**