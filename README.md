# STN Whole Person Initial Assessment — Digital Prototype

Private project repository for Supportive Therapy Network Limited (STN).

## Current prototype

Open `prototype/index.html` from the repository to inspect the tablet-friendly browser demonstration. GitHub's normal file viewer displays the source rather than running it. For local testing, download the HTML file and open it in a modern browser.

## Intended workflow

Dashboard → Client & Consent → Whole Person Screening → Safety Gate → Integrated Results → Clinical Review → Whole-Person Care Plan → Report.

## Current implementation

- Responsive browser-based demonstration interface.
- Client intake and consent field capture.
- Illustrative screening items with local progress and domain summaries.
- Separate safety screen with positive responses flagged for clinician review.
- Clinical review, formulation, care-plan and follow-up fields.
- Printable assessment summary.
- Local browser storage for demonstration only.

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
