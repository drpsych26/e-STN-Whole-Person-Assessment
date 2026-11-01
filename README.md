# STN Whole Person Initial Assessment — private development repository

Private project repository for Supportive Therapy Network Limited (STN).

## Current status — 1 November 2026

**DEVELOPMENT ACTIVE — NO GENERAL HOLD — PRIVATE / NON-LIVE — SYNTHETIC DATA ONLY.** Engineering, testing, integration, security remediation, documentation and launch-readiness work are authorised. Production deployment, public launch, external beta, real-client use and clinical operation remain unauthorised.

The repository remains private. No production environment is to be provisioned or connected. Keep development and test environments isolated from production. Do not enter identifiable client information, real health information, production credentials or secrets.

## Current verified implementation

- Browser-based Whole Person Initial Assessment demonstration with workflow gates and synthetic-data regression coverage.
- Flutter v4 four-module MVP with conservative non-diagnostic screening behaviour, local encrypted storage, profile/result/follow-up scaffolding and regression tests.
- Source manifests, section-level paper-pilot traceability baseline, controlled synthetic UAT protocol and release-gap documentation.
- PR #7 (Node 24-compatible GitHub Actions maintenance) is merged.
- PR #10 (controlled non-live safety gate, contrast fixes and source inventory baseline) is merged.
- PR #12 (Flutter Part A 25-item Core Intake) has passed all three latest GitHub Actions workflows on head `d45e0bae0766e2bdc6717cdaa5735c664b8fe202` and is now ready for review; it is not merged. The branch still requires base-branch reconciliation/review before merge.

## Verified PR #12 CI

All three workflows completed successfully on the latest PR head:
- Static quality: https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41270183394
- Flutter web validation: https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41270183352
- STN verification (including Flutter Android debug build): https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41270183354

The Part A change includes 25 source-worded items, five-point response scale, golden wording/structure tests, synthetic-only case/tester identifiers, local encrypted draft handling and explicit human-review flags for seven safety-tagged items. It does not implement the remaining 183 items, adaptive routing, PHQ-9/GAD-7, clinical escalation or server-side clinical records. Passing CI is engineering evidence, not clinical approval.

## Existing verified baseline

Repair PR #4 is merged into `main` at `d201460086919f4a0fdf7a9bbb7584bb4f7069dd`. Its post-merge verification, Flutter web validation and static-quality runs passed:
- https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41170645743
- https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41170645724
- https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41170645676

See `reference/POST-MERGE-VERIFICATION-2026-10-31.md` and `reference/PR12-VERIFICATION-2026-11-01.md` for recorded evidence.

## Browser prototype

Open `prototype/index.html` locally in a modern browser. GitHub's normal file viewer displays source rather than running it.

The demonstration workflow is:
Dashboard → Client & Consent → Whole Person Screening → Safety Gate → Integrated Results → Clinical Review → Whole-Person Care Plan → Report.

The browser prototype uses local browser storage for demonstration only. Workflow safeguards do not make it a secure clinical record system.

## Flutter scope

The original Flutter v4 archive is stored under `flutter/source-archives/parts/`. CI reconstructs it, verifies SHA-256, restores source and applies tracked fixes from `implementation-patches/flutter-v4/`.

The Flutter app currently contains MDD, GAD, PTSD and ADHD interim modules. PR #12 adds Part A of the paper pilot only and is pending review/merge. It is not the complete Whole Person Initial Assessment.

## Source reconciliation

The supplied paper pilot contains 208 items across 24 groups. The current browser prototype has nine simplified screening questions. PR #12 adds a partial Flutter Part A implementation of 25 items; it does not close the full source-to-code traceability requirement.

See:
- `reference/SOURCE-RECONCILIATION-INVENTORY-2026-11-01.md`
- `tests/PAPER-PILOT-SECTION-TRACEABILITY-2026-11-01.csv`
- `reference/SOURCE-IMPORT-MANIFEST.md`
- `reference/MASTER_SPEC.md`
- `reference/PRODUCTION-NZ-REQUIREMENTS.md`
- `reference/DEPLOYMENT-CHECKLIST.md`
- `SECURITY.md`

## Active development priorities

1. Reconcile PR #12 with current main, complete review and merge only after conflict/base checks and evidence review.
2. Import and hash-verify original source assets, including paper-pilot PDF and Flutter v2/v3/coding archives; preserve originals.
3. Complete item-level source traceability and clinical-owner decisions before implementing further clinical questions or routing.
4. Continue multi-client-safe data architecture, authenticated identity, server-side authorisation, audit and backend persistence in a non-production design/test environment.
5. Design and test the safety event lifecycle, human acknowledgement, escalation, timeout and fallback only against an approved clinical operating protocol.
6. Complete privacy impact, security threat modelling, dependency/SBOM/secret scanning, backup/recovery and accessibility test plans.
7. Keep changelog, evidence register, defects and version provenance current.

## Launch-readiness boundary

Launch-readiness engineering is authorised; launch is not. Do not enable production integrations, production credentials, real-client data, clinical use, public hosting or external beta. The application is not currently certified launch-ready: clinical source authority, instrument permissions, human safety operations, privacy/security approval, independent validation, accessibility/UAT and accountable go/no-go evidence remain open.

A private GitHub repository is still hosted by GitHub; it is not offline-only storage. Never commit real client records, credentials, API keys, private keys or identifiable health information.

## Flutter Whole Person Core Intake v0.9

A first Flutter implementation of Part A's 25 core intake items is maintained in `implementation-patches/flutter-v4/lib/screens/whole_person_initial_assessment_screen.dart`. It supports synthetic-ID-only entry, five-point responses, encrypted local draft save/reopen/delete and human-review flags for the paper-pilot safety-tagged items. The legacy profile screen is restricted to SYNTH- case IDs and TESTER- aliases; existing MDD/GAD/PTSD/ADHD interim modules require a saved SYNTH-/TESTER- profile, synthetic-data acknowledgement and complete responses before saving. It does not implement the remaining paper-pilot sections, licensed measures, adaptive routing, diagnostic scoring, safety tiers or real patient records. See `reference/FLUTTER-CORE-INTAKE-v0.9.md`.
