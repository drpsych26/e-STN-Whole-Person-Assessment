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
