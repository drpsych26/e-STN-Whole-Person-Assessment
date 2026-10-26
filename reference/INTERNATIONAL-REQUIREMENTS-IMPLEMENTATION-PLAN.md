# International Requirements Implementation Plan

**Project:** STN Whole Person Initial Assessment  
**Status:** Private implementation backlog  
**Authority:** Founder authorisation received 26 October 2026 to make recommended product/documentation changes based on international app benchmarking.  
**Release state:** HOLD. No public release, production deployment, clinical use, or identifiable client data.

## 1. Change-control rules

1. Preserve STN Clinical Core v2 and the approved Whole Person Initial Assessment paper pilot as the clinical source of truth.
2. Do not silently change clinical item wording, instrument scoring, cut-offs, criteria or routing. Each rule needs an authoritative source, version, test cases and clinical approval.
3. Competitor products are design references, not clinical authority. Do not copy proprietary content, code, branding or licensed instruments.
4. Where evidence is absent or conflicting, mark the item UNVERIFIED/BLOCKED; do not invent a threshold or rule.
5. Keep development private and use synthetic data only until all release gates pass.
6. AI must not autonomously diagnose, clear risk, decide crisis disposition or silently override clinicians. Show provenance, uncertainty and limitations.

## 2. Benchmark-derived decisions

| Reference | Lesson | STN decision | Boundary |
|---|---|---|---|
| APA App Evaluation Model | Review accessibility/context, privacy/security, clinical foundation, engagement, therapeutic goal/data integration; include equity and AI | Add evidence-based review across these areas for each release | Checklist completion is not certification |
| One Mind PsyberGuide | Credibility, user experience and transparency are separate; app-store popularity is not clinical evidence | Maintain an evidence register for product and clinical claims | Desk research is not an audit |
| Calm Health | Screening can guide a personalised next step | Explain why each module is selected and connect screening to clinician-reviewed planning | Screening is not diagnosis |
| PTSD Coach | Clearly bound self-management and link to professional support | Label each module’s intended use and limitations; make help pathways visible | Self-management is not a substitute for care |
| MindShift CBT | CBT self-management may complement care; exports can support continuity | Consider consent-controlled clinician report/export and adjunctive-use language | Do not claim efficacy beyond evidence |
| Wysa | AI needs explicit scope and crisis boundaries | Disclose AI use, limitations, uncertainty and safe handoff/fallback | No autonomous crisis decisions |
| MindDoc | Longitudinal trends may help, but tracking/analytics raise privacy questions | If trends are added, show source/date range/missingness and obtain appropriate consent | Do not collect unnecessary data |

## 3. Required workstreams and acceptance criteria

### A. Clinical source fidelity and traceability — BLOCKING
- Map every active digital item to the approved paper pilot and Clinical Core v2.
- Record instrument/version, exact item text, response scale, scoring/missing-data rules, validated cut-offs, population, source/licence, routing consequences and tests.
- Remove generic score bands and unsupported diagnostic defaults unless an authoritative validated rule supports them.
- A missing, declined, ambiguous or incomplete safety answer must never mean “no risk.”
- Safety handling must cover positive/uncertain/missing answers, visible clinician review, acknowledgement, documented disposition and fallback if the clinician is unavailable.
- Pass evidence: completed traceability matrix, independent clinical review, tests for every rule and signed approval.

### B. Workflow and decision support — BLOCKING
- Preserve: Dashboard → New Client → Whole Person Initial Assessment → Safety Gate → Adaptive Routing → Selected Assessments → Integrated Results → Clinical Review → Diagnostic Decision Support → Whole-Person Care Plan → Finalise → Report → Follow-up.
- Separate screening, clinician formulation, differential considerations, diagnostic decision and care plan.
- Show the source and rationale for each suggestion. Unsupported criteria must be “not assessed/insufficient information,” never automatically met.
- Finalised records must be immutable; corrections/addenda retain the original and record author, timestamp and reason.
- Pass evidence: workflow acceptance tests, clinician usability review, audit demonstration and clinical governance approval.

### C. Privacy, security and information governance — BLOCKING
- Complete a NZ privacy impact assessment and data-flow map against the Privacy Act 2020 and Health Information Privacy Code 2020, including applicable IPP3A changes effective 1 May 2026.
- Document consent, purpose, minimisation, access/correction, retention/disposal, disclosures, breach response, backups/recovery, vendors/subprocessors, hosting location, cross-border disclosure and analytics/telemetry.
- Implement real authentication, role-based access, least privilege, session controls, secure secrets, encryption in transit/at rest, audit logs and tested backup/restore. Local profile fields or device-level encryption alone are insufficient.
- Separate test/staging/production; prevent real-client data entering fixtures, logs, analytics or crash reports.
- Pass evidence: approved privacy assessment, threat model, security test results, access-control tests, recovery test, incident procedure and accountable owner.

### D. AI governance — BLOCKING if AI is included
- Disclose AI purpose, inputs, outputs, limitations, and whether data leaves STN or the device.
- Do not send identifiable health data to an AI provider without approved lawful basis, contractual controls, privacy assessment and governance approval.
- Require clinician review for clinically meaningful outputs; show uncertainty/provenance and record model/version where material to a decision.
- Prohibit autonomous diagnosis, treatment allocation, risk clearance or crisis disposition.
- Pass evidence: AI impact assessment, failure-case tests, human-oversight procedure and clinical/privacy sign-off. Otherwise disable the AI function.

### E. Accessibility, equity and New Zealand context
- Test screen-reader/keyboard use, contrast, readable language, scalable text, validation messages, low-bandwidth/recovery behaviour and tablet/mobile layouts.
- Co-design with Māori and relevant communities; review cultural safety, equity, disability access and rural/remote suitability.
- Verify all NZ service pathways, emergency/support numbers, eligibility and hours before release.
- Pass evidence: accessibility tests, representative user testing, cultural-safety review and verified local resource register.

### F. Reporting and continuity of care
- Distinguish patient-reported answers, computed scores, clinician-entered findings, AI suggestions and final clinician decisions.
- Include assessment date, instrument/version, completion/missingness, scoring method, safety review status, limitations, author/reviewer and amendment history.
- Export only necessary information with appropriate consent/access control; record export events.
- Pass evidence: synthetic sample reports, export/access tests and clinician sign-off.

### G. Engineering quality and release operations — BLOCKING
- Pin a supported Flutter/Dart toolchain in CI.
- Run formatting, static analysis, unit/integration tests and a production-mode build on a clean runner.
- Add end-to-end tests for workflow, safety flags, interrupted sessions, offline/reconnect, duplicate/unknown answers, permissions, reports and finalisation/addenda.
- Add dependency/licence and secret scanning, vulnerability checks, build provenance and rollback/recovery plan.
- JavaScript syntax checks and ZIP integrity are not proof that the app works.
- Pass evidence: reproducible green CI run, build artefact, test report, dependency/licence report and release-candidate sign-off.

### H. Pilot and governance
- Start with synthetic scenarios. Any later clinical pilot needs separate written authorisation, applicable ethics/governance review, consent, incident monitoring and stop criteria.
- Define owners, versioning, change log, clinical incident review, staff competency, post-release monitoring and revalidation after scoring/routing/model changes.
- Pass evidence: approved pilot protocol, trained users, escalation plan and formal go/no-go decision.

## 4. Minimum test scenarios

Test each safety response as positive, negative, uncertain, declined and missing; contradictory answers; incomplete assessments; high total score without direct safety disclosure; direct safety disclosure with low total score; unknown IDs; duplicate/invalid answers; stale instrument versions; unsupported criteria; interrupted/offline sessions; reconnect/recovery; concurrent edits; unauthorised access and cross-client access; expired sessions; finalisation/addenda/correction/export/audit/retention; AI unavailable, contradictory, overconfident or unsafe output; clinician rejection and missing provenance; accessibility and low-bandwidth use. Use synthetic data only.

## 5. Release gates

| Gate | Minimum evidence | Current disposition |
|---|---|---|
| G1 Source fidelity | Complete Clinical Core v2/paper-pilot traceability and clinical approval | BLOCKED |
| G2 Scoring and safety | Validated rules, full tests, human escalation/fallback | BLOCKED |
| G3 Workflow and reports | End-to-end acceptance, immutable finalisation and clinician review | BLOCKED |
| G4 Privacy/legal | NZ privacy assessment, data map, vendor/cross-border review, notices/consent | BLOCKED |
| G5 Security | Authentication, access control, audit, encryption, threat model, tests and recovery | BLOCKED |
| G6 Accessibility/equity | Accessibility, cultural-safety and NZ pathway reviews | BLOCKED |
| G7 Engineering | Reproducible Flutter build, analysis, unit/integration/E2E and dependency checks | BLOCKED — Flutter/Dart toolchain unavailable in prior review |
| G8 Pilot governance | Approved protocol, trained users, synthetic test pass and go/no-go | BLOCKED |
| G9 Release approval | All prior gates evidenced and signed by accountable clinical, privacy, security and product owners | BLOCKED |

## 6. What may change now

Permitted in the private repository: add requirements, traceability, tests, privacy/security/accessibility documentation; fix clear implementation defects when supported by the source specification and covered by tests; disable unsupported scoring, criteria, routing or AI behaviour until validated; improve clarity, missing-data handling, auditability and clinician oversight without changing approved clinical meaning.

Not permitted without documented source and appropriate approval: invent/change clinical cut-offs, criteria, instrument wording or scoring; remove safety questions/warnings to simplify the interface; claim regulatory clearance, clinical validity, security certification, privacy compliance or production readiness without evidence; publish/deploy, enrol clients or use identifiable health data.

## 7. Execution order

1. Inventory source files and confirm the canonical paper pilot and Clinical Core v2.
2. Complete source-to-code traceability and label unknowns.
3. Repair or disable unsupported scoring/criteria/safety logic.
4. Establish Flutter CI and run analysis, unit, integration and end-to-end tests.
5. Complete privacy, security, AI, accessibility and cultural-safety reviews.
6. Conduct independent clinical review and controlled synthetic usability testing.
7. Reassess every gate; retain HOLD until each has objective evidence and named approval.

## 8. Benchmark evidence and limitations

The separate INTERNATIONAL-MENTAL-HEALTH-APP-BENCHMARK-2026-10-26.md is desk research on MindDoc, Calm Health, Wysa, PTSD Coach, MindShift CBT, APA App Evaluation Model and One Mind PsyberGuide. It is not hands-on competitor testing, clinical audit, certification or evidence that STN is safe/effective. Recheck primary sources before making external claims.

**Current decision: PRIVATE DEVELOPMENT ONLY — RELEASE HOLD.** Founder authorisation permits implementation work; it does not replace clinical, legal, privacy, security, accessibility or release approval.
