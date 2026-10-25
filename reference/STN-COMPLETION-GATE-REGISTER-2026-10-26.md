# STN completion gate register — 26 October 2026

**Release decision: HOLD — private development and synthetic data only.** This register is an execution/acceptance contract, not evidence that blocked gates have passed.

## Evidence currently available
- The private repository contains the prototype, reference requirements, source-import manifest, and source-fidelity acceptance gate.
- The STN master project records identify the Whole Person Assessment v2.5/v2.6 HTML, paper pilot HTML, Flutter packs v2/v3/v4, and Clinical Core v2 as source assets/baselines.
- Static JavaScript syntax checks passed for the inspected HTML prototypes. The repository prototype's report escaping and form restoration fixes were syntax-tested.
- Archive integrity and manifest hash checks passed for the collected source archive. These checks prove integrity, not clinical correctness or application readiness.

## Work items and objective exit criteria

### A. Reconcile source of truth
- [ ] Inventory each supplied source, version, size, SHA-256, origin and date.
- [ ] Compare Clinical Core v2, paper pilot, HTML v2.5/v2.6, and Flutter v2/v3/v4 without overwriting originals.
- [ ] Create a requirement-to-source matrix for every question, response option, scale, score, cutoff, safety flag, routing rule, report field and workflow step.
- [ ] Record conflicts and obtain an explicit clinical/product owner decision; never silently reconcile.
- **Exit evidence:** versioned manifest, diff report, signed source-of-truth decisions, and original assets preserved.

### B. Import source assets to private repository
- [ ] Import original HTML and Flutter archives byte-for-byte, preserving names and hashes.
- [ ] Store extracted Flutter source alongside original ZIPs; record SDK/dependency versions and licenses.
- [ ] Confirm repository visibility remains private; exclude real client data, secrets, credentials and live environment configuration.
- **Exit evidence:** repository tree links plus recomputed SHA-256 matching the source manifest.

### C. Reproducible build and runtime tests
- [ ] Install/pin supported Flutter and Dart SDKs in a suitable CI runner.
- [ ] Run dependency resolution, formatter check, analyzer, unit/widget tests, and debug/release builds.
- [ ] Run browser UI tests in a permitted browser runner for intake, navigation, validation, report generation, restoration, keyboard/mobile layout and error states.
- [ ] Test offline/low-bandwidth behavior and backup/recovery where supported.
- **Exit evidence:** CI run URL, build artifacts, test output and defect list. Static syntax checks alone do not pass this gate.

### D. Clinical Core v2 fidelity
- [ ] Build a traceability matrix against the approved paper pilot and Clinical Core v2.
- [ ] Add deterministic golden tests for question text/order, scales, scoring, cutoffs, safety endorsements, routing, integrated results and report outputs.
- [ ] Test missing, contradictory, declined and uncertain responses; do not infer safety from total scores.
- [ ] Validate each instrument against its licensed/authorised version and published scoring rules; confirm permitted use before embedding.
- [ ] Keep automated output clearly separate from clinician interpretation and diagnostic decision-making.
- **Exit evidence:** 100% mapped requirements, reviewed test cases, reproducible pass results, licensed-instrument register, and clinical owner approval.

### E. Safety and clinical governance
- [ ] Define response ownership, urgency, operating hours, escalation contacts, documentation, follow-up, incident review and failure/timeout handling.
- [ ] Simulate positive/uncertain suicide/self-harm and other urgent safety responses, unavailable clinician, offline mode and false/ambiguous responses.
- [ ] Ensure the system never claims to guarantee safety and never acts as autonomous diagnostician/crisis decision-maker.
- [ ] Obtain documented review by appropriately qualified NZ clinical governance lead and supervised pilot approval.
- **Exit evidence:** signed safety case, scenario results, escalation SOP, training/competency records and pilot protocol.

### F. Identity, data and privacy/security
- [ ] Implement server-side authentication, MFA where appropriate, role-based access and least privilege.
- [ ] Implement secure server persistence, schema validation, encryption in transit/at rest, audit events, session controls and secrets management.
- [ ] Implement immutable finalisation with controlled correction/addendum, version history and author/reason/timestamp.
- [ ] Complete NZ Privacy Act 2020 / Health Information Privacy Code 2020 assessment, privacy impact assessment, data-flow map, consent/authority, retention/disposal, access/correction, breach response, backups, recovery, vendor/cross-border/AI review and penetration/security testing.
- [ ] Verify no sensitive data is stored only in browser localStorage or embedded in logs/analytics.
- **Exit evidence:** tested deployment architecture, security test report, approved policies and privacy/legal sign-off.

### G. Release and pilot
- [ ] Confirm branding, accessibility, tablet workflows, error states and report print/export.
- [ ] Confirm third-party instrument/software licenses, dependency vulnerabilities, support ownership and rollback.
- [ ] Run a controlled, consented, synthetic-data pre-pilot followed by an approved supervised pilot only after all prior gates pass.
- [ ] Record acceptance decision, release version, approvers, known limitations and rollback plan.
- **Exit evidence:** signed go/no-go record. No public or real-client deployment before approval.

## Current limitation statement
The available work session did not establish a usable live Google Drive connector for the supplied folder URL, did not provide a supported binary upload path from the local runtime into GitHub, and could not execute a browser E2E session or Flutter/Dart build in its restricted environment. Therefore the source reconciliation, repository binary import, E2E/build evidence and clinical/security approvals remain **open**. These are explicit status facts, not waived requirements.

## Ownership
- Product/source owner: STN product owner.
- Clinical safety, scoring and pilot approval: appropriately qualified NZ clinical governance lead.
- Engineering/build/security: software engineering owner.
- Privacy: designated privacy officer/legal adviser.
- Release: named accountable STN release owner after evidence review.
