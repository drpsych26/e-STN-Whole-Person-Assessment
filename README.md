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

## Controlled UAT v0.7

The browser prototype now includes explicit `Yes`, `No`, `Unsure`, `Declined` and `Not asked` safety responses. Every non-`No` response remains flagged for human review; missing responses block the safety gate. A flagged response also requires a clinician review note before the simulated care-plan workflow can continue. This is a workflow safeguard only: it does not assign, notify, acknowledge or hand over to a clinician.

See `reference/CONTROLLED-UAT-PROTOCOL-v0.7.md`. This is private synthetic-data UAT only. It does not authorise real-patient use, clinical care, triage, diagnosis, risk clearance or identifiable health information.

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
