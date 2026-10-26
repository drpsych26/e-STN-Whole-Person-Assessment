# STN National Rollout Readiness Programme — Non-Live

**Current decision: HOLD. Private development and synthetic data only. No public deployment or real-client data.**

This document defines release gates; it is not evidence of compliance, certification, clinical validation, or approval. User authorisation to proceed permits the work but does not replace required testing and qualified review.

## Non-negotiable controls
- Keep the repository, builds, and test environment private.
- Use synthetic data only until a separate supervised-pilot approval is documented.
- Do not silently replace or override STN Clinical Core v2, the approved paper pilot, instrument wording, scoring, cutoffs, or routing. Resolve source conflicts through documented clinical/product owner decisions.
- Never treat a local profile as authentication, an unsupported diagnostic criterion as met, a missing safety answer as negative, or a total score as proof of safety.
- No public hosting, production credentials, app-store distribution, or production persistence before a separate go/no-go decision.

## Gate A — Source baseline and traceability
1. Inventory Clinical Core v2, the approved paper pilot, HTML versions, Flutter v2/v3/v4 packs, specifications, assets, instruments and versions.
2. Preserve originals byte-for-byte; record filenames, provenance, versions and SHA-256 hashes.
3. Map every supported question, response, scale, scoring rule, cutoff, safety flag, routing condition, report field and workflow to source and tests.
4. Record conflicts and obtain clinical/product owner decisions; keep a versioned approved baseline.
5. Verify instrument licence/permission for electronic use, reproduction, translation, populations and redistribution.
**Exit evidence:** complete source manifest, approved conflict log, 100% traceability for supported requirements, and signed baseline approval.

## Gate B — Reproducible application build
1. Identify the actual Flutter project root and pin supported Flutter/Dart SDK versions and dependencies.
2. CI runs formatting, dependency resolution, `flutter analyze`, unit tests, widget tests, integration tests, and debug/release builds.
3. Test navigation, required fields, save/resume, interrupted sessions, report rendering/export, accessibility, mobile/tablet layouts, low-bandwidth/offline behavior and failure recovery.
4. Add dependency vulnerability/licence checks and secret scanning.
5. Produce a reproducible internal artifact with version, commit SHA, release notes, software bill of materials and known limitations.
**Exit evidence:** reproducible successful build, retained test logs/artifacts, and no unresolved critical/high defects without approved mitigations.

## Gate C — Clinical scoring and safety
1. Remove generic/unverified scoring thresholds and defaults that imply diagnostic criteria are met.
2. Implement only rules traceable to the authorised instrument version and approved Clinical Core baseline.
3. Distinguish raw answers, missing/declined/uncertain answers, computed results, screening interpretation, clinician assessment and formal diagnosis.
4. Do not infer safety from total scores. Positive, uncertain, declined or missing safety responses follow an approved human-led workflow.
5. Test positive, uncertain, missing, contradictory and declined answers; offline/interrupted sessions; unavailable clinician; handover; acknowledgement; documentation and follow-up.
6. No autonomous diagnosis or unreviewed crisis decision-making.
**Exit evidence:** reviewed golden tests for all supported modules, instrument permissions, approved safety SOP, scenario results and signed NZ clinical governance approval.

## Gate D — Identity, records and security
1. Define architecture and threat model covering devices, shared tablets, accounts, APIs, database, exports, staff and vendors.
2. Implement real authentication, secure sessions, server-side role/permission enforcement, least privilege, account lifecycle, revocation and risk-appropriate MFA.
3. Implement secure backend persistence, server-side validation, TLS, encryption at rest, managed secrets and key lifecycle.
4. Audit access, edits, sign-off, addenda, exports and administrative actions; restrict alteration of audit records.
5. Support immutable/versioned finalisation with attributed correction/addendum, reason and timestamp.
6. Test access control, client isolation, exports, session expiry, revocation, backup/restore, disaster recovery and incident response.
7. Browser localStorage is not the clinical system of record.
**Exit evidence:** tested architecture, security report with no unresolved critical/high findings, successful restore drill and engineering/security sign-off.

## Gate E — New Zealand privacy and legal review
1. Map collection, purpose, consent/authority, use/disclosure, hosting, retention/disposal, access/correction, vendors, AI processing and overseas transfers.
2. Complete a Privacy Impact Assessment and qualified review of applicable NZ privacy/health-information, consumer-rights and professional obligations.
3. Approve privacy notices, consent, rights requests, retention, disposal, breach response, complaints and cross-border/vendor arrangements.
4. Obtain qualified advice on instrument permissions, intended clinical function, marketing claims, professional roles and any applicable regulatory requirements; do not assume exemption or certification.
**Exit evidence:** signed privacy/legal review and approved policies.

## Gate F — Operations and national readiness
1. Name accountable service, clinical, privacy, security, engineering and release owners.
2. Complete SOPs, user guides, staff training and competency, support hours, on-call/escalation matrix, incident response and complaints handling.
3. Define monitoring, maintenance, uptime/support targets, capacity, backup/recovery objectives, business continuity and vendor exit plans.
4. Test accessibility, supported devices, rural/low-bandwidth workflow and safe fallback processes.
5. Maintain environment separation, secret-free staging, migration/rollback plan, change control and release pipeline.
**Exit evidence:** accepted runbooks, training records, support model, continuity and rollback plan.

## Gate G — UAT and staged rollout
1. Complete synthetic-data UAT, clinical simulation, security testing and device coverage.
2. Plan phases: internal sandbox, separately approved supervised pilot, limited cohort, evaluated expansion, national rollout. Each phase needs entry/exit criteria, named owner, incident thresholds and rollback triggers.
3. Assemble source manifest, traceability, build/test results, defect register, licence register, clinical safety case, privacy/legal reviews, security report, restore evidence, UAT, training, runbooks, release notes and rollback plan.
**Exit evidence:** independent evidence review and signed go/no-go from accountable release owners.

## Known blockers from the current review
- Flutter/Dart build, analyzer and automated test results are not evidenced.
- Browser end-to-end tests were blocked; a prior fallback rendered no usable UI and is not a pass.
- Original sources and Clinical Core v2 are not fully reconciled/imported byte-for-byte.
- Static review found generic scoring thresholds without proven instrument traceability, non-MDD criteria gating defaulting to true, and incomplete evidence for human safety escalation.
- Authentication, server-side authorisation, secure backend persistence, audit controls, PIA, independent security tests, instrument permissions and signed clinical approval are not evidenced.

## Status vocabulary
- **PASS:** objective evidence exists and the required reviewer accepts it.
- **FAIL:** a test/review found a defect.
- **BLOCKED:** the test cannot currently be run.
- **OPEN:** evidence or review is missing.
- **NOT APPLICABLE:** rationale documented and approved.

Never mark a gate complete because it was requested, authorised, described, or partially implemented.

## Decision
**HOLD — private development and synthetic data only.** Public release and real-client use require a separate documented decision after every applicable gate passes. This plan does not authorise deployment.