# STN Whole Person Initial Assessment — Digital Prototype

Private project repository for Supportive Therapy Network Limited (STN).

## Current prototype

Open `prototype/index.html` from the repository to inspect the tablet-friendly browser demonstration. GitHub's normal file viewer displays the source rather than running it. For local testing, download the HTML file and open it in a modern browser.

## Intended workflow

Initial Assessment: Dashboard → Client & Consent → Whole Person Screening → Safety Gate → Integrated Results → Clinical Review → Whole-Person Care Plan → Report.

Second-stage assessment: Clinical Follow-Up & Diagnostic Formulation, opened after the Initial Assessment for additional chronology, MSE, diagnostic-domain evidence review, differential considerations, 5Ps + Te Whare Tapa Whā formulation, clinician-led diagnostic indication statuses and care planning.

## Assessment modules

- `prototype/index.html` — Whole Person Initial Assessment.
- `prototype/follow-up-assessment.html` — second-stage Clinical Follow-Up & Diagnostic Formulation Assessment.
- Both are designed to adapt to phone and tablet screens. The follow-up module is linked from the Initial Assessment navigation.

## Current implementation

- Responsive browser-based demonstration interface.
- Client intake and consent field capture.
- Illustrative screening items with local progress and domain summaries.
- Separate safety screen with positive responses flagged for clinician review.
- Clinical review, formulation, care-plan and follow-up fields.
- Printable assessment summary.
- Local browser storage for demonstration only.

## Latest verification update — 26 October 2026

The prototype source has received a narrow safety/quality patch:
- User-entered values rendered in the assessment report are HTML-escaped.
- Client and assessment fields now have explicit restore mappings so the stored client name is mapped back to the correct form control.

These changes were committed and the updated inline JavaScript passed a syntax parse in the available tool environment; the HTML-escaping helper was also exercised with a script-tag payload. This is not an end-to-end browser test. The browser execution environment blocked local/localhost page loading, and Flutter/Dart SDKs were unavailable, so browser workflow tests and Flutter build/test remain outstanding.

See:
- `reference/EXECUTION-VERIFICATION-2026-10-26.md`
- `reference/ADDITIONAL-STATIC-CHECK-RESULTS-2026-10-26.md`

The project remains **HOLD — private development only**. Do not enter real client data. No clinical validation or production security approval is implied.

## Important status notice

This is a development prototype, not a production-ready or clinically validated diagnostic system. Demonstration questions and scores are not validated instruments. Do not use this tool alone to diagnose, triage, determine emergency disposition, or make treatment decisions. Do not enter real or identifiable client information.

The repository currently contains a browser demonstration and selected project/governance documents. The complete supplied reference HTML files and Flutter ZIP packs have **not yet been imported** into this repository. This repository must not be treated as the full STN project handover until those original assets are added and checked.

## Production gates

Before real-client use, implement and approve:
- authenticated clinician access and role-based permissions;
- secure backend persistence, encryption and auditable access/change events;
- privacy notices, consent, access/correction, retention and disposal workflows;
- human-led safety escalation and documented crisis response;
- approved/licensed instruments and governed scoring rules;
- clinical governance, regression testing, UAT, security testing and recovery plans.

See `reference/PRODUCTION-NZ-REQUIREMENTS.md`, `reference/DEPLOYMENT-CHECKLIST.md`, `reference/MASTER_SPEC.md`, and `SECURITY.md`.

## Privacy and repository access

Keep this repository private while the project is being developed. Never commit real client records, credentials, API keys, private keys, or identifiable health information. A private GitHub repository is still hosted by GitHub; it is not offline-only storage.


## Branding and consolidated source update — 26 October 2026

The browser prototype now uses the STN purple/black/white palette (accent `#AF2CFF`), dark panels, and a Manrope-first sans-serif stack. This is a visual branding update to the repository prototype; it does not establish that the original uploaded logo asset or all locally supplied HTML/Flutter archives are stored in GitHub.

A consolidated local review package is available from the working session as `STN_MASTER_CONSOLIDATED_PRIVATE.zip`. It preserves supplied HTML versions and Flutter v2/v3/v4 packs separately with a SHA-256 source inventory. Those local archives still need a deliberate repository asset-import step; this commit does not claim that binary ZIPs have been uploaded to GitHub.

**Release remains on hold for real-client use.** Keep this repository private. No public deployment, copyright assignment, clinical validation, or production security approval is implied.


## Flutter v4 source recovery and CI — 31 October 2026

The original uploaded Flutter v4 ZIP is now preserved in `flutter/source-archives/` as a base64-encoded file so the original archive bytes can be restored without alteration. GitHub Actions decodes it and verifies the full SHA-256 before extraction. The workflow then applies the separately tracked conservative scoring-engine and UI/report patches and runs Flutter 3.24.5 formatting, analysis, unit tests and an Android debug build.

The Flutter app remains an MVP, not the full Whole Person Initial Assessment. Its four module question sets are not established as licensed or validated instruments. The app uses encrypted device-local Hive storage; this is not identity authentication, server-side RBAC or a secure multi-user clinical record. The UI explicitly identifies diagnostic criteria as not evaluated and the descriptive sum as non-diagnostic. Incomplete assessments can be saved as drafts and are flagged for review by the interim engine. A local review flag is not a human handover or crisis response service.

The PR's CI run must pass before the source/build path is considered verified. The repository still requires original HTML source reconciliation, the approved Clinical Core v2 rulebook, an operational clinician escalation/acknowledgement service, production identity and backend architecture, NZ privacy/security assessment, instrument permissions, independent clinical validation and written clinical governance/pilot approval. Release remains **HOLD — private development and synthetic data only**.
