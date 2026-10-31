# STN informed-consent workflow — draft specification

**Status: DEVELOPMENT DRAFT — NOT APPROVED FOR CLINICAL OR PRODUCTION USE**

This document describes the consent capture now present in the browser prototype. It is not legal advice, an approved privacy notice, or a substitute for clinician explanation. STN's clinical governance lead, privacy officer and New Zealand legal adviser must approve the final client-facing wording and operational policy before any real-client use.

## 1. Purpose and separation of decisions

The application must distinguish:
1. Consent to participate in the Whole Person Initial Assessment.
2. Acknowledgement that the approved privacy notice was provided and explained.
3. The clinician's record that the client had an opportunity to ask questions and demonstrated understanding.
4. The clinician's consideration of decision-specific capacity and communication/support needs.
5. Separate, optional permissions for specific information sharing.
6. Separate agreement to telehealth, where relevant.
7. A later change or withdrawal of consent.

A privacy-notice acknowledgement is not consent. Optional sharing permissions are not bundled into assessment consent. An unchecked optional permission means no permission has been recorded; it must never be interpreted as permission.

## 2. Client explanation — draft prompts

Before asking for a decision, the clinician must explain in plain language:
- why the assessment is being offered and what topics it may cover;
- that screening responses are not, by themselves, a diagnosis or a complete risk assessment;
- what information will be collected and the purpose for collecting it;
- who may access the information within the service and what disclosures may be required or permitted by law or safety obligations;
- the approved privacy notice, including collection, use, disclosure, storage/processing, access and correction, retention/disposal and contact details;
- any relevant limits to confidentiality, explained before consent is requested;
- that participation is voluntary, questions are welcome, and the client may pause or decline;
- what happens if consent is declined or deferred;
- how to change or withdraw consent and what that means for future activity and any information already lawfully collected.

Do not promise absolute confidentiality, deletion of all historical records, or that withdrawal reverses disclosures or processing that have already lawfully occurred.

## 3. Required consent record

The prototype captures:
- assessment consent decision: Yes / No / Deferred / Withdrawn;
- consent wording version identifier;
- date/time recorded;
- person recording consent;
- method: written/electronic, verbal (with reason), or supported decision-making;
- privacy notice acknowledgement;
- understanding check;
- decision-specific capacity consideration and support needs;
- explanation/questions notes;
- whether a copy was offered/provided;
- optional permissions: GP, nominated whānau/family/support person, named other person/organisation, and telehealth;
- withdrawal date/time and person recording withdrawal.

For any named third-party permission, record the recipient, purpose, information categories, limits and duration/review point in the approved production data model. The current prototype's free-text field is only a temporary demonstration field.

## 4. Workflow rules

- Do not open screening unless affirmative assessment consent is recorded and required consent-record fields are complete.
- If consent is No or Deferred, do not start screening. Follow the approved service procedure for information already collected and any immediate safety concern.
- Optional sharing choices remain independently off unless specifically granted.
- If a client withdraws, record the withdrawal, stop future assessment progression, and route the case to an authorised clinician to determine appropriate next steps under policy and law.
- A new decision may be recorded later, but it must create a new timestamped event; it must not erase the earlier grant or withdrawal.
- Never treat an unanswered safety question as a negative response.
- Consent capture must not replace an immediate human safety response where one is required.

## 5. Production requirements not implemented by this browser demo

The browser prototype stores data in local browser storage. It does not provide an authenticated clinical record, immutable audit, server-side permission enforcement, reliable identity verification, secure multi-user separation or production-grade consent history.

Production implementation must add:
- append-only, versioned consent events with actor identity, timestamp, wording version and change reason;
- authenticated role-based access and server-side enforcement of sharing permissions;
- consent status visible at the point of access, export and disclosure;
- controls to prevent disclosure outside the scope of recorded permission unless an approved lawful basis/exception is documented;
- a process for updating or withdrawing permissions and recording the effect on future use;
- access/correction, retention/disposal and privacy-incident workflows;
- accessibility, interpreter and supported decision-making pathways;
- clear handling of urgent safety situations and legally required/permitted disclosures;
- secure backend persistence, backups, audit and recovery testing.

## 6. Approval and validation gates

Before production:
- [ ] STN-approved privacy notice and contact details inserted.
- [ ] New Zealand legal/privacy review completed against the Health Information Privacy Code as currently in force and relevant consumer-rights requirements.
- [ ] Clinical governance approves consent capacity/communication prompts and escalation policy.
- [ ] Client-facing wording tested for readability, accessibility and comprehension.
- [ ] Supported decision-making, interpreter and alternative-format pathways tested.
- [ ] Consent grant, refusal, deferral, partial optional permission, change and withdrawal tested end-to-end.
- [ ] Audit trail and server-side access/disclosure enforcement independently tested.
- [ ] Tablet, mobile and desktop UAT signed off.

## 7. Current prototype boundary

The UI labels the wording version as **STN-DRAFT-CONSENT-1.0 — NOT APPROVED FOR CLINICAL USE**. This marker must remain until a formally approved version is supplied and version-controlled. Do not enter identifiable client information in this prototype.
