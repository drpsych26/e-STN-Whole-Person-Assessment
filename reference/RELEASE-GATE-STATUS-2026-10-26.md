# STN release gate status — 26 October 2026

**Overall status: NOT RELEASE-READY. Keep private. No deployment. Synthetic data only.**

This status reflects evidence available in the current work session. `OPEN` means no accepted evidence is available; `BLOCKED` means the required test could not be executed in the available environment; `FAIL` means static review found a substantive defect. A document describing a requirement is not evidence that the requirement has been implemented.

| Gate | Status | Evidence / reason | Exit requirement |
|---|---|---|---|
| Private repository and no deployment | PASS for current observed state only | Repository was checked as private in the prior execution pass; no deployment action was taken in this pass. Recheck before any release. | Confirm visibility, deployment targets, secrets, DNS and hosting are still disabled. |
| HTML inline JavaScript syntax | PASS for inspected versions | Prior Node syntax checks passed for non-empty inline scripts. | Repeat in CI for imported source and deployed build artifact. |
| Source archive integrity | PASS for tested archives | ZIP integrity checks passed; integrity is not correctness. | Preserve originals and compare SHA-256 values against a committed manifest. |
| Original source reconciliation/import | OPEN | Original HTML/Flutter source assets and Clinical Core v2 have not been fully reconciled and imported byte-for-byte into the repo. | Complete manifest, hash verification, diffs, traceability matrix and owner-approved conflict decisions. |
| Flutter dependency resolution and build | BLOCKED | Flutter/Dart SDK build was not available in the prior environment; no build pass is claimed. | Pinned CI run for dependency resolution, formatter, analyzer, unit/widget tests and debug/release builds. |
| Browser/tablet end-to-end tests | BLOCKED | Browser execution was blocked; fallback rendered no usable UI. | Working browser runner, scripted end-to-end results, screenshots/logs and defect closure. |
| Clinical Core v2 fidelity | OPEN | No accepted full mapping or golden-test evidence. | 100% traceability and clinician-approved expected outputs for all supported questions, scoring, routing, safety flags and reports. |
| Flutter v4 scoring/criteria logic | FAIL | Static review found generic total-score bands without source traceability and non-MDD criteria gating defaulting to true. | Correct against approved source; unsupported modules must report not assessed/not implemented; golden tests pass. |
| Safety response and escalation | FAIL / OPEN | Hard-coded boolean risk rules do not demonstrate a complete human acknowledgement/escalation pathway or uncertain/missing response handling. | Approved safety case and tested positive/uncertain/missing/offline/unavailable-clinician workflows. |
| Instrument licences and permissions | OPEN | Exact instruments/versions and permitted use have not been documented as accepted evidence. | Instrument register and permissions verified before inclusion. |
| Authentication and role enforcement | OPEN | Local profiles are not verified identity or access control. | Approved identity provider/session model plus server-side role enforcement tests. |
| Secure backend and audit trail | OPEN | A complete production record lifecycle has not been demonstrated. | Secure persistence, server-side validation, append-only audit, controlled finalisation/addenda, export controls and revocation tests. |
| Privacy impact assessment and NZ review | OPEN | No signed PIA/legal/privacy approval is evidenced. | Qualified review of applicable NZ privacy/health information obligations, data flows, consent, retention, access/correction, breach and cross-border processing. |
| Security testing and recovery | OPEN | No penetration test, backup restore evidence or approved incident plan is evidenced. | Independent security testing, vulnerability triage, successful restore drill and incident response approval. |
| Accessibility and device UAT | OPEN | No accepted UAT record. | Tested desktop/tablet/mobile, keyboard/accessibility, print/export, low-bandwidth/offline and failure paths. |
| Clinical governance and supervised pilot | OPEN | No signed clinical safety case, competency evidence or pilot protocol is evidenced. | Appropriately qualified NZ clinical governance approval and supervised synthetic/pre-pilot protocol. |
| Final release authorisation | NOT AUTHORISED BY EVIDENCE | User authorisation to proceed is recorded, but the technical/clinical/privacy acceptance gates are not closed. | Separate documented go/no-go after all evidence is reviewed and accepted. User instruction here is to remain non-live. |

## Immediate priority order
1. Reconcile and hash all original sources; establish the single approved Clinical Core/paper pilot baseline.
2. Import the verified source and create a reproducible CI build/test pipeline using the actual project root.
3. Fix the known scoring/criteria/safety defects only against approved clinical source material; add golden and regression tests.
4. Implement and test authentication, authorisation, backend record lifecycle and audit controls.
5. Complete privacy/security assessment, licensing, clinical governance, accessibility and UAT.
6. Produce a signed internal release-candidate report while leaving public deployment and real-client persistence disabled.

## Release-control rule
No gate may be marked PASS solely because a task is planned, documented, authorised, or represented in UI. Every PASS requires objective evidence and required reviewer acceptance. No production activation is permitted under this plan.