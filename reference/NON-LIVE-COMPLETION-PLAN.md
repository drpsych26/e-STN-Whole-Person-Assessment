# STN non-live completion plan and release controls

**State: PRIVATE / NON-LIVE / SYNTHETIC DATA ONLY**  
**Release decision: HOLD.** This plan is a work-control document, not evidence that any open gate has passed.

## Non-negotiable controls
- Keep the GitHub repository private.
- Do not publish a web deployment, enable production hosting, or configure a live client database.
- Use synthetic or de-identified test data only; never place identifiable health information, credentials, tokens, or secrets in the repository, test logs, analytics, screenshots, or issue comments.
- Do not change clinical question wording, scoring, cutoffs, safety rules, or routing to make tests pass. Record discrepancies and obtain a documented clinical/product owner decision.
- Do not enable autonomous diagnosis or automated crisis decisions. Safety endorsements and uncertain responses require a defined human review/escalation pathway.
- A user’s authorisation to proceed is not a substitute for build evidence, source fidelity, professional approval, or legal/privacy review.

## Work packages and acceptance evidence

### 1. Source-of-truth and import
- Inventory all supplied files, including Clinical Core v2, the approved paper pilot, HTML v2.5/v2.6, Flutter packs v2/v3/v4, and relevant master specifications.
- Preserve original bytes and filenames; calculate SHA-256 hashes and compare against a committed manifest.
- Extract and inspect the actual Flutter project, pubspec.yaml, source, assets, licences and SDK constraints.
- Produce a requirement-to-source traceability matrix covering every question, response, scale, score, cutoff, safety flag, routing rule, report field and workflow transition.
- Log conflicts; do not silently merge versions.
- **Pass evidence:** complete manifest, source diff, 100% requirement mapping, conflict log and approved source decisions.

### 2. Build and application tests
- Use a controlled CI runner with pinned Flutter/Dart SDK versions and locked dependencies.
- Run formatting checks, static analysis, unit tests, widget tests and debug/release builds.
- Run browser/tablet end-to-end tests for intake, navigation, required-field validation, save/resume, routing, report rendering/export, accessibility, keyboard operation, narrow screens, errors and interrupted sessions.
- Test offline/low-bandwidth behavior, reconnect/retry behavior and data integrity.
- Test only with synthetic fixtures.
- **Pass evidence:** green CI run, build artifacts, test reports, coverage summary, resolved critical/high defects and reproducible instructions.

### 3. Clinical correctness
- Convert the approved Clinical Core and paper pilot into a versioned traceability and golden-test suite.
- Verify question text/order, response options, instrument-specific scoring, cutoff interpretation, missing/declined/uncertain answers, branching, safety flags, integrated results and final report output.
- Verify all instruments and scoring rules against the exact authorised/licensed version and permitted use.
- Ensure risk is not inferred from a total score and that a missing answer is never treated as a negative safety response.
- Keep computed results, source responses and clinician interpretation distinct.
- **Pass evidence:** all mapped requirements tested, reviewed expected results, instrument permission register and signed clinical validation.

### 4. Safety and clinical governance
- Define escalation ownership, hours of coverage, response time targets, backup contact, unavailable-clinician procedure, documentation and follow-up.
- Simulate positive, uncertain, contradictory and missing safety responses; clinician unavailable; device offline; interrupted session; false positives; and urgent non-suicidal safety concerns.
- Define staff training, competency, incident review, change control and supervised pilot protocol.
- **Pass evidence:** approved safety case/SOP, scenario results, competency records and signed NZ clinical governance approval.

### 5. Privacy, security and records
- Document data flows, purposes, collection notices, consent/authority, user roles, access/correction process, retention/disposal, disclosures, vendor/subprocessor processing, cross-border transfers and any AI processing.
- Complete a Privacy Impact Assessment and review against applicable New Zealand privacy and health-information requirements with a qualified privacy adviser.
- Implement server-side authentication, least-privilege roles, appropriate MFA, secure sessions, TLS, encryption at rest, managed secrets, server-side validation, audit events, monitoring and controlled exports.
- Implement immutable finalisation with versioned, attributed addenda/corrections; never silently overwrite a signed assessment.
- Ensure browser localStorage is not the clinical system of record.
- Test backup restoration, disaster recovery, incident/breach response, access revocation, vulnerability management and penetration testing.
- **Pass evidence:** architecture and threat model, approved privacy documents, security test report, successful restore drill and sign-offs.

### 6. Non-live release candidate
- Keep deployment disabled and secrets/production credentials absent.
- Package a reproducible build for private engineering review only.
- Complete synthetic-data UAT across desktop/tablet/mobile and verify report print/export.
- Maintain defect triage, known limitations, support ownership, rollback instructions and release versioning.
- **Pass evidence:** signed internal acceptance checklist with all blockers closed. This still does not authorise real-client use.

### 7. Separate go-live gate (not authorised by this plan)
Real-client use requires a separate explicit release decision after all prior evidence has been reviewed and signed by the accountable engineering, clinical governance, privacy/security and STN release owners. No implied approval is granted by this plan.

## Current known blockers
- Flutter/Dart SDK build and test evidence is not established in the prior execution environment.
- Browser end-to-end testing was blocked by environment policy; prior fallback loaded no usable UI and is not a pass.
- Original source assets and Flutter project are not yet fully reconciled/imported byte-for-byte in the private repository.
- Clinical Core v2 scoring, safety routing and instrument permissions are not validated.
- Production authentication, backend persistence, audit controls, privacy impact assessment, security testing and professional approvals are not evidenced.
- A static JavaScript syntax check and ZIP integrity check do not close any of those blockers.

## Status vocabulary
- **PASS:** objective evidence exists, is reviewable, and the required reviewer has accepted it.
- **BLOCKED:** the test or review cannot currently be run.
- **FAIL:** a test was run and did not meet its acceptance criterion.
- **OPEN:** not yet evidenced.
- **NOT APPLICABLE:** rationale recorded and approved.

Never mark a gate PASS because work was requested, authorised, documented, or planned.