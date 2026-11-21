# STN platform gap analysis

**Date:** 21 November 2026
**Scope:** repository `drpsych26/e-STN-Whole-Person-Assessment` at commit 68b95a2 (branch `feature/backend-release-gate-engine`), plus the STN-Website repository.
**Correction (21 November 2026):** an earlier version of this report said crisis numbers were absent from all builds. That was wrong; see section 3.1.

**Open pull requests on the public repository, not reviewed by this work:** #41 (`release/harden-testing-apk-and-dossier`) and #16 (`release/brand-copyright-polish-2026-11-04`), both targeting `main`.

**Release status:** NOT CLINICALLY SIGNED OFF. NOT CLIENT READY. PRODUCTION GO-LIVE NOT AUTHORISED.

This analysis states what the repository contains and what it does. Each finding cites the file or check it came from. Items marked UNVERIFIED have not been tested.

## 1. Current implementation state

| Component | Location | State |
|---|---|---|
| Web assessment prototype | `prototype/STN-Whole-Person-Assessment-Standalone.html`, `prototype/index.html` | Static HTML. No calls to any backend endpoint (search for `fetch(`, `XMLHttpRequest`, `/v1/` returns 0). Stores data in `localStorage`. |
| Follow-up assessment prototype | `prototype/follow-up-assessment.html` | Static HTML, `localStorage` only. |
| Flutter v4 app | `flutter/source-archives/` and `implementation-patches/flutter-v4/` (14 Dart files) | The archive reassembles from parts 1, 2 and 4 and matches its recorded SHA-256. The full project is not checked in; CI extracts it at build time. Patched scoring and report files are partial. |
| Backend API | `backend/app/` | FastAPI. Modules: auth (token verification), encrypted client-record store, RBAC, hash-chained audit trail, onboarding state machine, release gate engine. 67 tests pass locally on commit 68b95a2 (`pytest -o addopts=""`). |
| Website | `STN-Website` (public) | Static `index.html`, `legal.html`, draft privacy notice. Deployed to GitHub Pages. |
| CI | `.github/workflows/` (5 workflows) | Prototype static checks, API tests, static quality, Flutter web validation, Flutter build tests. |

## 2. Missing functionality

1. **No working sign-in.** Token verification exists, but the identity provider is not configured, so protected routes return 503. Microsoft Entra External ID is the chosen provider and is not connected. Customer MFA is not implemented.
2. **No customer account management.** Profiles, contact preferences, consent management, account recovery, suspension and deletion are not built beyond the onboarding case.
3. **No email or SMS verification.** Onboarding accepts evidence flags (`email_verified`, `phone_verified`) that nothing produces. No messaging integration exists.
4. **No clinical assessment engine.** The prototypes hold the questionnaires in client-side JavaScript. The backend stores encrypted JSON records but does not score, validate, track completion or version assessments.
5. **No clinical documentation, care plans, clinical reports or referral records.**
6. **No appointments or service allocation.** The onboarding stages `allocated` and `team_assigned` accept evidence references only.
7. **No notifications.** No email, SMS or clinician alerting.
8. **No secure document storage.**
9. **No reporting.** No reports or exports beyond the audit verification function.
10. **No frontend that calls the backend.** Nothing connects the prototypes or the Flutter app to the API.

## 3. Broken or incomplete functionality

1. **Crisis numbers are missing from the prototypes and the Flutter source.** Checked with a precise search for `111` and `0800 543 354`: `reference/source-html/assessment-demo.REVIEW-CORRECTED.html` contains the 111 emergency line, Lifeline 0800 543 354 and 1737. `prototype/STN-Whole-Person-Assessment-Standalone.html`, `prototype/index.html`, `prototype/follow-up-assessment.html` and the Flutter screens and scoring logic contain none. The prototypes contain the word "crisis" but no numbers. The release candidate must be chosen and its crisis panel verified (H10). This is release-blocking.
2. **The safety route is display-only.** The prototypes show a crisis screen. Nothing records the escalation, notifies a clinician, timestamps acknowledgement or tracks resolution.
3. **Two prototypes differ.** `STN-Whole-Person-Assessment-Standalone.html` and the v2.6 source are not the same build. Which one is authoritative has not been recorded.
4. **Flutter build not verified in this session.** The CI workflow is designed to build the APK, but it has not been run here.

## 4. Incomplete frontend components

- Prototype HTML has no routing, no session handling, and no accessibility testing.
- Flutter screens exist for home, module, results, profiles and the whole-person intake, but are not connected to any backend.
- No clinician dashboard connected to the API, no administrator screens and no customer account screens.

## 5. Missing backend services

- Identity integration (Entra External ID), token validation against a configured tenant, and session management.
- Messaging for verification.
- Assessment scoring and versioned assessment content.
- Clinical documentation and report generation.
- Appointment and allocation services.
- Notification and escalation services with acknowledgement tracking.
- Document storage.
- Reporting and export.
- API versioning beyond `/v1`, rate limiting and request logging.

## 6. Database deficiencies

- **SQLite only.** The production target is an encrypted managed database. No migration tool is in use; schema is created with `CREATE TABLE IF NOT EXISTS` on every connection. There is no migration history.
- No foreign keys between tables. `client_records`, `onboarding_cases`, `role_assignments` and `audit_chain` are not linked by referential integrity.
- No backup, restore or retention configuration. Restore has not been tested.
- The original `audit_log` table in `store.py` is not append-only and not hash-chained. The newer `audit_chain` table is. Both exist.
- Encryption: client records are encrypted at the application layer with AES-256-GCM. The key is supplied by environment variable. No key management or rotation exists.

## 7. Missing assessment modules

The directive requires modules for Major Depressive Disorder, Generalised Anxiety Disorder, PTSD, ADHD, suicide and self-harm risk, substance use, functional impairment, psychosocial assessment and whole-person assessment. The prototypes contain instruments for these areas (PHQ-9, GAD-7, PCL-5, ASRS-5, AUDIT-C, DAST-10, K10, WHODAS 2.0, C-SSRS) according to their on-page text. None is implemented as a versioned, server-side module.

**Licensing is UNVERIFIED.** The clinical decision record marks C06 (instrument licence and permission status) as open. Several of these instruments have licence conditions. No written confirmation was found in the repository.

## 8. Clinical workflow deficiencies

- The required workflow (Dashboard → Client Registration → Whole Person Assessment → Safety Gate → Adaptive Routing → Selected Assessments → Integrated Results → Clinical Review → Diagnostic Decision Support → Care Plan → Clinical Approval → Finalise → Clinical Report) is not implemented end to end.
- No clinical review step exists in the backend.
- Clinical sign-off items C03, C04, C05, H02, M07, C06, H10 and H09 are recorded as pending independent review (`docs/clinical/CLINICAL-SIGNOFF-FORM.md`).

## 9. Security vulnerabilities and weaknesses

Findings from code and configuration review. Penetration testing has not been performed.

1. **No Content-Security-Policy** on any prototype page (search returns 0).
2. **Prototypes store client data in `localStorage`** on the device. This is unencrypted, shared by every page on the origin, and not cleared on sign-out (no sign-out exists).
3. **No rate limiting** on any endpoint.
4. **No input size limits** beyond the 64 KB client-record payload cap.
5. **Access denials are audited, but no alerting exists** on repeated denials.
6. **The audit chain is append-only at the database layer,** but the database is a local file with no access control beyond the operating system.
7. **The clinical repository is public** and holds governance and business material (see section 11).
8. **Secrets handling:** `STN_DATA_KEY` and `STN_DATA_DB` come from the environment. No secrets manager is wired up.

## 10. Missing integrations

- Microsoft Entra External ID (identity, MFA).
- Email and SMS providers (deferred pending cost review).
- Azure hosting, database and secrets (see `docs/infrastructure/`). No Azure subscription has been provided or inspected.
- Clinician register checks (not required by code, but needed for clinician onboarding).
- Website to platform integration (none; the website has no sign-in).

## 11. Outstanding release requirements

| Gate | Requirement | Status | Evidence in repo |
|---|---|---|---|
| G01 | Backend implementation complete | OPEN | Not complete: sections 2, 5, 6 |
| G02 | Customer onboarding verified | OPEN | No end-to-end test with real verification |
| G03 | Authentication and permissions verified | OPEN | RBAC tested with synthetic identities; no IdP |
| G04 | Clinical workflows validated | OPEN | Workflow not implemented |
| G05 | Assessment scoring verified | OPEN | No server-side scoring |
| G06 | Safety escalation verified | OPEN | Display-only (section 3.2) |
| G07 | Privacy and security review passed | OPEN | No review performed |
| G08 | Independent penetration testing passed | OPEN | Not performed; must be independent |
| G09 | Critical/high defects resolved and retested | OPEN | Defect register to be created |
| G10 | Backup and restoration verified | OPEN | Not implemented |
| G11 | Production infrastructure validated | OPEN | No subscription provided |
| G12 | Clinical governance approval obtained | OPEN | Pending independent clinical review |
| G13 | Final production release authorisation | WITHHELD | Depends on all gates |

## 12. What is achievable here, and what is not

**Achievable by implementation and automated testing:** sign-in integration once a tenant exists, the server-side workflow, storage, scoring code with unit tests, the safety escalation record, audit, reporting and the frontend connections.

**Not achievable from this environment:** clinical governance approval, instrument licence confirmation, independent penetration testing, the privacy review, production infrastructure and the clinician register check. These require people, documents or accounts outside this repository. The release report must record them as open.

## 13. Next actions, in order

1. Confirm the crisis panel in the rendered prototype build (H10).
2. Connect Entra External ID for sign-in (requires tenant).
3. Build the assessment engine: versioned definitions, server-side scoring, missing-data handling, completion tracking.
4. Build the clinical workflow and the safety escalation record with acknowledgement tracking.
5. Connect the Flutter app and the prototype to the API.
6. Replace SQLite with a migration-managed database and add backup and restore tests.
7. Write end-to-end tests and the defect and remediation register.
8. Publish the release acceptance report with every gate marked by its evidence.
