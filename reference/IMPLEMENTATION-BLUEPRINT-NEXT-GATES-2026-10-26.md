# STN Whole Person Assessment — gated implementation blueprint
**Date:** 26 October 2026  
**Status:** Private development only — release hold  
**Repository:** `drpsych26/e-STN-Whole-Person-Assessment`

## Purpose
Convert the previously identified blockers into an implementation sequence that can be executed and evidenced. This is a design and acceptance document, not evidence that the features have been implemented or validated.

## Non-negotiable controls
- Do not deploy publicly or use identifiable client information until the release gates in this document are signed off.
- The approved STN Whole Person Initial Assessment paper pilot and approved STN Clinical Core v2 are the authoritative content sources. Do not infer missing questions, scoring rules, cutoffs, routing criteria, or instrument permissions.
- A questionnaire score is not a diagnosis. No automated result may clear suicide/self-harm, violence, overdose, abuse, safeguarding, or other urgent safety concerns.
- An unanswered, declined, uncertain, contradictory, or positive safety response must remain visible and require a documented human decision under a clinician-approved protocol.
- A system may show a notification as delivered or a handover as accepted only when a reliable receipt/acknowledgement has been recorded.
- Use synthetic test data only until privacy and clinical governance approvals explicitly authorise a supervised pilot.

## Target workflow
Dashboard → New Client → Whole Person Initial Assessment → Safety Gate → Adaptive Routing → Selected Assessments → Integrated Results → Clinical Review → Diagnostic Decision Support → Whole-Person Care Plan → Finalise → Report → Follow-up.

Every transition must be represented by a state and an auditable event. A screen transition alone is not proof that a safety action or clinical handover happened.

## Work packages and acceptance evidence

### Gate 0 — source authority and content freeze
**Work**
1. Identify the exact approved version/date of the paper pilot and Clinical Core v2.
2. Inventory every source file and label it authoritative, derivative, superseded, draft, or reference-only.
3. Record content owner, approval date, change history, instrument name/version, licence/permission basis, and permitted digital use.
4. Resolve conflicts with the clinical content owner; do not silently choose a version.

**Accept when**
- Source register is complete and signed by the clinical content owner.
- Each question, response option, scale, scoring rule, cutoff, safety rule and routing rule has a source identifier.
- Instrument licences/permissions are documented before digitisation or distribution.

### Gate 1 — source-to-code traceability
**Work**
- Populate `tests/CLINICAL-CORE-V2-TRACEABILITY-TEMPLATE.csv` with one row per atomic requirement or rule.
- Include source document/version/page/section/question ID and exact excerpt or controlled paraphrase; target code path and symbol; test case; status; reviewer and approval date.
- Track omissions and deviations as defects. Do not label inferred content as source-approved.

**Accept when**
- 100% of in-scope questions, options, scales, scoring rules, missing-data rules, cutoffs, safety rules and routing rules are mapped.
- Each executable rule has at least one positive and one negative/boundary test where applicable.
- An independent reviewer confirms source fidelity and signs the mapping.

### Gate 2 — deterministic assessment engine
**Required behavior**
- Keep raw responses, calculated values and clinician interpretation separate.
- Preserve question-level provenance and version identifiers.
- Distinguish unanswered, declined, unable to answer, uncertain, not applicable and answered values wherever the approved clinical content supports these states.
- Validate duplicate, unknown and out-of-scope question IDs.
- Never apply generic score bands or substitute rules for unlicensed/unvalidated instruments.
- Make incomplete assessments explicit; do not silently impute missing answers.
- Return a review-required state rather than a clinical risk level unless a validated, approved rule explicitly supports the latter.
- Version every scoring/routing configuration and include it in the result record.

**Accept when**
- Golden test vectors are derived from approved source rules and independently checked.
- Boundary, missingness, contradictory answer, unknown module, duplicate response, version mismatch and regression tests pass.
- Test evidence includes the exact commit, Flutter/Dart versions, commands, exit codes and CI run URL.

### Gate 3 — human safety escalation and handover
Implement a state machine, not a lone boolean flag.

**Minimum states**
1. `not_screened`
2. `screening_in_progress`
3. `review_required`
4. `urgent_action_required` (only where a clinician-approved protocol supports this classification)
5. `clinician_assigned`
6. `handover_pending`
7. `handover_acknowledged`
8. `action_documented`
9. `closed_by_authorised_clinician`

Add `unable_to_route` / `escalation_failed` as explicit failure states. State transitions must not be silently skipped. The exact classifications, response times and escalation actions must be set by a qualified clinical governance owner, not by the software developer.

**Required event data**
- Assessment and question-set version; response status and timestamp.
- Reason the review/escalation was triggered; do not reduce this to an opaque total score.
- Assigned responsible role/person and assignment timestamp.
- Notification channel, attempt time, delivery receipt if available, and failure reason.
- Acknowledgement identity/role/time; next action and due time as specified by the approved protocol.
- Escalation attempt and alternate route if no acknowledgement.
- Handover summary, receiving clinician, explicit acceptance, action taken, outcome and closure authorisation.
- Audit events for every state transition and amendment.

**Fail-safe rules**
- A failed notification is not a completed handover.
- A sent message is not an acknowledged handover.
- No available clinician or failed integration must surface as an operational incident and trigger the approved fallback procedure.
- The interface must not tell a person that help is on its way unless that is confirmed and the service actually provides it.
- Crisis-service numbers, response windows and fallback instructions must be jurisdiction- and service-specific, reviewed and version-controlled.
- Pilot simulations must cover positive, uncertain, declined, missing, contradictory responses; lost connectivity; app backgrounding; duplicate notifications; unavailable recipient; failed delivery; timeout; reassignment; and failed audit persistence.

**Accept when**
- Clinician-approved protocol and RACI exist.
- End-to-end simulations demonstrate each state transition and failure branch.
- A clinical safety reviewer signs off test results; no unresolved critical/high safety defects remain.

### Gate 4 — identity, authorisation and record security
**Minimum architecture**
- Use a supported authentication provider; no local profile field may be treated as authentication.
- Enforce authorisation on the server/API and data layer, not only in the UI.
- Define least-privilege roles (e.g. system administrator, clinician, supervisor, assessor, auditor) and tenant/team/client assignment boundaries.
- Require MFA for privileged and clinical accounts where supported by the risk assessment.
- Use secure session expiry/revocation, recovery controls, rate limiting and account lifecycle management.
- Encrypt transport and persisted data; manage keys through a controlled secret/key-management service. Document threat model and device-loss response.
- Record access, exports, changes, finalisation, permission changes and administrative actions in a tamper-evident audit trail.
- Define backup, restore, recovery-point/recovery-time objectives, retention, legal holds, disposal and breach response.
- Separate development, test and production environments. No production secrets or client data in source control, logs or test fixtures.

**Accept when**
- Threat model, data-flow diagram, access matrix and security test report are approved.
- Tests prove denied access for unauthorised roles and cross-client access attempts.
- Restore test and incident/breach tabletop are documented.
- Independent security review has no unresolved critical/high findings.

### Gate 5 — NZ privacy, health-information and clinical governance
Complete a documented applicability review, not a blanket “compliant” claim:
- Privacy Act 2020 and applicable Information Privacy Principles.
- Health Information Privacy Code 2020, including amendments in force at the review date.
- Health and Disability Commissioner Code and applicable professional standards.
- Purpose/authority for collection, notice, access/correction, disclosure, retention, disposal and complaints.
- Privacy impact assessment; data inventory and flow map; processor/vendor agreements; cross-border access/storage; breach response; privacy officer ownership.
- Clinical governance, scope of practice, informed consent, accessibility, Māori data sovereignty/cultural safety, bias, interpretation limitations and complaints/escalation process.
- Records of clinical content approval, instrument licence/permission, change control and user training.

**Accept when**
- A NZ privacy professional/privacy officer and appropriate clinical governance lead sign the review.
- All high-risk findings have documented remediation and verification.
- Instrument owners/licensors have confirmed permitted digital use where required.

### Gate 6 — independent validation and supervised pilot
**Before any pilot**
- Approved protocol, intended-use statement, inclusion/exclusion criteria, supervision and incident plan.
- Independent clinician review of content, scoring, safety routing, reports and limitations.
- Test plan covering usability/accessibility, language/cultural considerations, reliability of calculations, security, privacy, operational fallback and clinical workflow.
- Synthetic-data end-to-end tests completed; no critical/high defects open.
- Pilot site, trained users, consent materials, support contact, monitoring and stop criteria approved.
- Written go/no-go approval from accountable clinical and organisational owners.

**Pilot constraints**
- Small, supervised, explicitly authorised, time-limited and monitored.
- No autonomous diagnosis or risk clearance.
- A clinician remains responsible for assessment and disposition.
- Pause immediately on a serious safety event, missed escalation, material data exposure, wrong scoring/routing or loss of reliable records, pending formal review.

**Accept when**
- Independent validation report and signed pilot approval are present.
- Pilot outcomes and adverse events are reviewed before any expansion.
- Separate release approval is issued; passing one gate does not waive another.

## Release decision
The product remains **NOT COMPLETE — PRIVATE DEVELOPMENT ONLY — RELEASE HOLD** until every mandatory gate has evidence and formal approval. Documentation, a passing static check, a green build, or a working prototype alone does not establish clinical validity, legal compliance or readiness for use with clients.
