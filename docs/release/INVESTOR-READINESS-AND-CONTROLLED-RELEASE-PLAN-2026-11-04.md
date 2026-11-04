# STN investor readiness and controlled release plan

**Prepared:** 4 November 2026  
**Repository baseline:** `main` at `e3b23a142ca78cc864abd492b805251b12cec402`  
**Purpose:** Establish an evidence-based work programme for product completion, investor diligence and a controlled production release.

## Executive status

STN has a private development repository containing a browser demonstration and a Flutter v4 MVP. On the recorded main commit, the configured GitHub Actions workflows passed:
- static quality and browser prototype regression checks;
- Flutter web validation (format, static analysis, tests and web release build);
- Flutter Android debug build and its configured tests.

A debug APK artifact was generated. These results establish only that the configured software checks and build completed. They do not establish complete product functionality, clinical validity, legal compliance, cybersecurity assurance, production readiness or a successful live deployment.

The owner has stated that clinical and other approvals have been granted. The approval documents, issuing authorities, scope, conditions, approved software version and accountable signatories have not yet been attached to this repository's controlled release evidence. Treat this as an owner-provided assertion until verified against the approved build.

## Current product inventory

| Area | Evidence in repository | Current interpretation |
|---|---|---|
| Browser prototype | `prototype/index.html`, `prototype/follow-up-assessment.html`, standalone HTML | Demonstration workflow; local browser storage; synthetic data only |
| Flutter mobile app | Reconstructed v4 source plus tracked patches | MVP with MDD, GAD, PTSD and ADHD interim modules and whole-person intake scaffolding |
| Automated checks | `.github/workflows/` | Passing configured CI at recorded baseline |
| Android | CI-generated debug APK artifact | Installable engineering/UAT build; not a signed production APK |
| Web | CI Flutter web release bundle and standalone browser HTML | Build artifact exists; no verified production hosting or backend integration |
| Brand | Canonical logo, SHA-256 and regression test | Source consistency controls in place |
| Clinical source traceability | 208-item/24-group paper-pilot baseline; partial 25-item Flutter Part A record in prior project history | Full item-to-screen-to-logic-to-test-to-report traceability remains to be demonstrated |
| Clinical records | Local encrypted Hive implementation in Flutter; localStorage in browser prototype | Not a production multi-user clinical record service |
| Identity and access | No verified production identity/MFA/RBAC implementation in reviewed evidence | Production access-control gate remains open |
| Safety operations | Screening flags and workflow gates | Live escalation, responder acknowledgement, timeout/fallback and drill evidence remain to be demonstrated |
| Privacy/security | PIA template, NZ requirements checklist, security guidance | Templates/checklists are not completed assurance evidence |

## Required workstreams and exit criteria

### 1. Product completeness and functional verification
- Establish an authoritative requirements register and screen/workflow inventory.
- Trace every approved source requirement and instrument item to UI, validation, scoring, persistence, report output and automated test.
- Implement and test all supported paths, error states, permissions, empty states, interrupted sessions, offline/online transitions and recovery.
- Perform automated browser/device end-to-end tests and documented human UAT across supported Android devices, tablets and desktop browsers.
- Record defects with severity, reproduction steps, owner, fix commit and retest evidence.

**Exit evidence:** signed requirements traceability matrix, passing CI, test reports, UAT acceptance, closed critical/high defects or formally accepted residual risks.

### 2. Clinical safety and validity
- Identify intended purpose, intended users, target population, exclusions and clinical claims.
- Confirm written digital-use, reproduction, scoring and reporting permissions for every instrument.
- Validate scoring and interpretation against approved source/version and independent reference cases.
- Complete clinical hazard analysis, safety case, risk controls and residual-risk acceptance.
- Define human review, crisis escalation, responder ownership, acknowledgement, timeout, fallback, after-hours coverage and incident drills.
- Verify that the application does not imply autonomous diagnosis or replace clinician judgement.

**Exit evidence:** approved clinical protocol, instrument permission register, validation report, hazard log, safety case, escalation drill records and dated clinical sign-off for the exact release.

### 3. Production architecture and cybersecurity
- Replace device-only/local browser storage as the authoritative clinical record with a managed backend and documented data model.
- Implement authenticated identity, MFA, least-privilege role-based access, tenant isolation and server-side authorisation.
- Add encrypted transport and storage, managed key/secret rotation, tamper-evident audit events, secure exports and session controls.
- Add monitoring, vulnerability/dependency scanning, SBOM, threat model, penetration testing and remediation.
- Implement backup, restore, disaster recovery, retention, deletion and incident response.
- Verify no patient data, credentials or secrets are stored in source control, logs or analytics.

**Exit evidence:** architecture/security review, threat model, penetration-test report, access-control tests, SBOM, backup/restore evidence, incident plan and security owner sign-off.

### 4. New Zealand privacy and operational governance
- Complete a system-specific Privacy Impact Assessment, not just the template.
- Confirm applicable privacy and health-information obligations with qualified New Zealand advisers.
- Finalise collection notices, consent/authority, purpose limitation, access/correction, disclosure, retention, disposal and complaint processes.
- Document hosting location, subprocessors, overseas processing and contractual controls.
- Establish clinician onboarding, training, support ownership, change management, complaints, incident response and business continuity.

**Exit evidence:** signed PIA, approved notices and policies, hosting/data-flow register, operational procedures, training records and privacy/operations sign-off.

### 5. Android and web release engineering
- Create a controlled production signing process; signing keys must remain outside the repository and be stored in an approved secret manager.
- Build a release-mode Android App Bundle/APK with versioning, package identity, signing verification and reproducible artifact hashes.
- Test install, upgrade, migration, uninstall/reinstall, permissions, network failure and supported Android versions.
- Deploy the web application to an approved production host with TLS, domain/DNS, security headers, monitoring, backups and rollback.
- Separate development, UAT, staging and production; do not point UAT builds at production records.
- Verify the exact deployed web/mobile build against the release approval.

**Exit evidence:** signed APK/AAB, signing verification, release notes, artifact hashes, deployment record, smoke tests, rollback rehearsal and production owner sign-off.

### 6. Investor diligence package
Prepare a controlled investor pack containing:
- company and product overview, problem statement, target users and intended market;
- product demo and screenshots clearly labelled as prototype/UAT where applicable;
- roadmap, milestones, resourcing and technical architecture;
- evidence-based development status and known limitations;
- clinical governance, privacy and security roadmap;
- intellectual-property ownership and third-party instrument/dependency licensing register;
- commercial model assumptions clearly labelled as assumptions, not achieved revenue or contracted demand;
- funding requirement, use of funds, milestone-linked budget and risk register;
- management, adviser and governance roles, with names/credentials only where verified.

Do not present unverified clinical approval, regulatory status, customer traction, efficacy, revenue, contracts or deployment as established facts.

## Release gates

| Gate | Required owner | Minimum release evidence |
|---|---|---|
| Product and engineering | Engineering lead | Requirements traceability, E2E/UAT, defect disposition, reproducible builds |
| Clinical | Accountable clinical lead | Exact-version clinical validation, safety case, instrument permissions, escalation approval |
| Privacy | Privacy officer | Completed PIA, data-flow and retention controls, approved notices |
| Security | Security lead | Threat model, penetration test, access-control evidence, incident and recovery tests |
| Operations | Service owner | Staffing, training, support, escalation coverage, continuity and rollback |
| Executive | Accountable director/release owner | Signed go/no-go for exact commit, artifact hashes, environment and scope |

No single CI result or general statement of authorisation substitutes for these version-specific release gates. If approval documents already exist, register them confidentially with issuer, reference, date, scope, conditions and approved software version; do not place confidential records in a public website or public repository.

## Immediate next actions

1. Attach or register the approval evidence and map it to the exact product version and intended deployment.
2. Run a complete code and architecture audit against the inventory above.
3. Complete the full clinical source traceability and instrument permission register.
4. Implement production identity, backend clinical records, audit, safety escalation and operational controls.
5. Execute the full E2E, security, privacy, accessibility and UAT programmes.
6. Build and sign the production Android release; deploy the web application to the approved host.
7. Close the release gates and prepare the investor diligence pack from verified evidence only.

## Non-negotiable data boundary during development

Until the exact release gates are closed and production deployment is formally approved, use synthetic test data only. Do not enter identifiable client or health information into the browser prototype, debug APK, public website forms or GitHub issues.
