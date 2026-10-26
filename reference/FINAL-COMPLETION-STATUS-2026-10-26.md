# STN completion status — 26 October 2026

## Decision

**NOT COMPLETE — PRIVATE DEVELOPMENT ONLY — RELEASE HOLD.**

This record distinguishes changes made from evidence not yet available. It must not be represented as a certificate of clinical validity, legal compliance, security, or production readiness.

## Requested acceptance criteria

| Requested item | Evidence available | Disposition |
|---|---|---|
| Flutter formatting, analysis, unit tests and build | Safety-reviewed ZIP integrity checked. Flutter/Dart SDK absent in the execution environment; network DNS unavailable for fetching the SDK. CI workflow updated but Flutter project source is not present under the workflow's configured source path in the repository. | **NOT VERIFIED / BLOCKED** |
| Full Clinical Core v2 source-to-code traceability | Paper pilot HTML and v2.6 HTML source are available. The canonical, approved Clinical Core v2 rulebook/structured source and instrument licensing records have not been located in the reviewed import bundle. Draft Flutter module questions are explicitly marked unvalidated. | **BLOCKED** — do not infer clinical mapping |
| Complete human safety escalation and handover | Interim code flags incomplete assessments and non-zero designated review items. No authenticated clinician assignment, acknowledgement, handover, timeout/fallback, incident audit or operational escalation service is evidenced. | **PARTIAL SAFETY GUARD ONLY; NOT A COMPLETE WORKFLOW** |
| Authentication, role-based access and clinical-record security | Local profiles and device-encrypted Hive storage exist. They do not demonstrate authentication, server-side authorisation, multi-user record integrity, audit, revocation, retention/disposal, backup/recovery or tested security controls. | **BLOCKED** |
| NZ privacy, clinical governance and instrument licensing reviews | Requirements checklist exists. No completed privacy impact assessment, legal review, approved data processing/vendor register, signed clinical governance decision, or instrument permissions register is evidenced. | **BLOCKED** |
| Independent clinical validation and supervised pilot approval | No independent validation dataset/protocol/results, named independent clinical reviewer sign-off, supervised pilot protocol, ethics/governance determination, staff competency evidence, or signed go/no-go is evidenced. | **BLOCKED — CANNOT BE CLAIMED COMPLETE** |

## Changes completed in the repository

- Added the international requirements implementation plan.
- Added the Flutter v4 safety patch execution record.
- Added tracked interim scoring engine and unit-test source under implementation-patches/flutter-v4/.
- Updated the GitHub Actions workflow to conditionally run Flutter checks when a project is present at the configured source path.
- Recorded the status and limitations in the release-blockers issue.

## Exact blockers to close

1. Place the canonical Flutter source in the repository and pin the Flutter SDK version. Run formatter, analyzer, all tests and a clean Android build in CI; retain logs and artifact digest.
2. Identify and approve the canonical Clinical Core v2 source, exact instrument versions and licensing/permission evidence. Complete item-by-item mapping from approved paper/source to code; clinical owner must approve every scoring and routing rule.
3. Implement a real safety case workflow: distinct positive/negative/uncertain/declined/missing statuses; urgent clinician notification; authenticated acknowledgement; ownership and escalation timers; alternate on-call route; documented disposition; failed-delivery alerts; audit trail; interruption/offline fallback and user-facing emergency guidance.
4. Choose and implement a production architecture with identity provider, MFA where appropriate, server-side authorisation, tenant/client scoping, least privilege, encrypted transport/storage, managed secrets, append-only audit, backup/restore, retention/disposal, access/correction/export workflows, and tested incident response.
5. Obtain qualified NZ privacy/legal review, complete the PIA and data-flow/vendor/cross-border assessment, approve consent and privacy notices, and document the instrument permissions register.
6. Obtain independent clinical review and a controlled pilot protocol. Define inclusion/exclusion, supervision, training, incident response, stop rules, outcome measures, consent, data governance and a signed go/no-go.

## Verification record

- ZIP integrity check of the safety-reviewed Flutter archive: passed.
- Inline JavaScript syntax checks on supplied HTML files were previously recorded as passed.
- Flutter/Dart format/analyze/test/build: not run.
- End-to-end runtime test: not passed/evidenced.
- Clinical validity and diagnostic accuracy: not established.
- Privacy/security compliance: not established.
- Independent validation and supervised pilot: not performed.

A status marked BLOCKED means the evidence or accountable approval required to close that gate does not exist in the reviewed material.