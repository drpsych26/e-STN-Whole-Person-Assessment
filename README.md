# STN Whole Person Initial Assessment — private development repository

Private project repository for Supportive Therapy Network Limited (STN).

## Current status — 31 October 2026

**HOLD — private development only — synthetic data only.** Do not enter real or identifiable client information. This repository is not approved for clinical use, public deployment or production operation.

The repository contains:
- a browser-based Whole Person Initial Assessment demonstration;
- a Flutter v4 module-app MVP source archive, preserved as encoded source parts and verified by SHA-256 in CI;
- tracked conservative Flutter implementation patches and regression tests;
- project requirements, source manifests and release-gate documents.

The Flutter v4 module MVP is not the complete Whole Person Initial Assessment workflow. It is not a validated diagnostic instrument and does not establish diagnosis, clinical risk disposition or treatment eligibility.

## Browser prototype

Open `prototype/index.html` locally in a modern browser. GitHub's normal file viewer displays source rather than running it.

The intended workflow is:

Dashboard → Client & Consent → Whole Person Screening → Safety Gate → Integrated Results → Clinical Review → Whole-Person Care Plan → Report.

The browser prototype uses local browser storage for demonstration only. It now blocks progression when required client consent, screening responses, safety responses, clinician review or care-plan fields are incomplete. Storage write failures stop further progression. These are workflow safeguards, not a secure clinical record system.

## Flutter v4 module MVP

The original supplied Flutter v4 archive is stored under `flutter/source-archives/parts/`. CI reconstructs it, verifies the expected SHA-256, restores the source and applies tracked fixes from `implementation-patches/flutter-v4/`.

The Flutter app currently contains MDD, GAD, PTSD and ADHD screening modules, local encrypted Hive storage, profile capture and response-summary export. It is an MVP scaffold:
- the response-severity sum is descriptive only;
- diagnostic criteria are not assessed;
- incomplete answers and designated review items trigger a clinician-review flag;
- local encrypted storage is not authentication, server-side authorisation, multi-user isolation, an immutable audit trail or a production clinical record.

## Latest post-merge verification — 31 October 2026

Repair PR #4 is merged into `main` at `d201460086919f4a0fdf7a9bbb7584bb4f7069dd`. The post-merge verification, Flutter web validation, and static-quality GitHub Actions runs all passed:
- https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41170645743
- https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41170645724
- https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41170645676

An Android debug APK was built and uploaded as GitHub Actions artifact `13031137407` (expires 7 November 2026). It is for internal synthetic-data testing only, not a production release.

See `reference/POST-MERGE-VERIFICATION-2026-10-31.md` for the exact checks, artifact details, repaired defects and remaining release blockers.

A separate draft PR #7 proposes upgrading GitHub Actions to Node.js 24-compatible releases. It must pass its own CI before merge.

## Controlled non-live UAT v0.8

The browser prototype includes explicit `Yes`, `No`, `Unsure`, `Declined` and `Not asked` safety responses. Every non-`No` response remains flagged for human review; missing responses block the safety gate. A flagged response requires a documented human review note before the simulated care-plan workflow can continue. This does not assign, notify, acknowledge or hand over to a clinician.

See `reference/CONTROLLED-UAT-PROTOCOL-v0.7.md`. The application is restricted to synthetic-data UAT. It is not authorised for real-patient use, diagnosis, triage, risk clearance or identifiable health information.

## Source reconciliation status — 1 November 2026

A local source inventory and section-level traceability baseline are recorded in `reference/SOURCE-RECONCILIATION-INVENTORY-2026-11-01.md` and `tests/PAPER-PILOT-SECTION-TRACEABILITY-2026-11-01.csv`. The supplied paper pilot contains 208 table items across 24 groups. The current browser prototype has 9 simplified screening questions and the Flutter v4 archive is a four-module MVP; neither is an exact implementation of the paper pilot. Original source import, authoritative-version approval, instrument permissions and item-level traceability remain open.

## Flutter Whole Person Core Intake v0.9

A first Flutter implementation of Part A's 25 core intake items is maintained in `implementation-patches/flutter-v4/lib/screens/whole_person_initial_assessment_screen.dart`. It supports synthetic-ID-only entry, five-point responses, encrypted local draft save/reopen/delete and human-review flags for the paper-pilot safety-tagged items. The legacy profile screen is restricted to SYNTH- case IDs and TESTER- aliases; existing MDD/GAD/PTSD/ADHD interim modules require a saved SYNTH-/TESTER- profile, synthetic-data acknowledgement and complete responses before saving. It does not implement the remaining paper-pilot sections, licensed measures, adaptive routing, diagnostic scoring, safety tiers or real patient records. See `reference/FLUTTER-CORE-INTAKE-v0.9.md`.

## Automated verification

GitHub Actions checks:
- browser prototype JavaScript syntax;
- browser workflow regression behaviour using synthetic data;
- source archive integrity and SHA-256;
- Flutter dependency resolution, formatting, static analysis, unit/widget tests and Android debug build;
- Flutter web static analysis, tests and release build.

See the current Actions runs and PR #4 for the exact commit and result. A workflow being queued or configured is not a passing check. Do not claim the current head passes until its runs complete successfully.

## Source completeness and traceability

The supplied Flutter v4 archive is now preserved in the repository. The other supplied HTML versions and Flutter v2/v3 packs have not all been imported and reconciled. The approved paper-pilot and Clinical Core v2 baseline still require clinical-owner sign-off and question-by-question source-to-code traceability.

See:
- `reference/SOURCE-IMPORT-MANIFEST.md`
- `reference/VERIFIED-ORIGINAL-SOURCE-HASHES.md`
- `reference/REMEDIATION-EXECUTION-LOG-2026-10-31.md`
- `reference/STN-COMPLETION-GATE-REGISTER-2026-10-26.md`

## Production gates

Before real-client use, implement and approve:
- authenticated clinician identity and role-based permissions;
- secure backend persistence, server-side authorisation, audit and change history;
- key lifecycle, backup, recovery and retention/disposal controls;
- privacy notices, consent, access/correction and breach response workflows;
- approved/licensed instruments and governed scoring rules;
- clinician-led safety escalation, acknowledgement, handover and fallback;
- NZ privacy/security review, independent testing, clinical governance, validation and supervised UAT.

See `reference/PRODUCTION-NZ-REQUIREMENTS.md`, `reference/DEPLOYMENT-CHECKLIST.md`, `reference/MASTER_SPEC.md` and `SECURITY.md`.

## Privacy and repository access

Keep this repository private while the project is being developed. Never commit real client records, credentials, API keys, private keys or identifiable health information. A private GitHub repository is still hosted by GitHub; it is not offline-only storage.
