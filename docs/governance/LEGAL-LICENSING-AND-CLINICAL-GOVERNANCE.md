# STN Legal, Licensing and Clinical Governance Register

**Entity:** Supportive Therapy Network Limited (STN)  
**Product:** e-STN Whole Person Assessment  
**Document owner:** STN  
**Revision:** 1.0  
**Prepared:** 18 November 2026

## 1. Purpose and authority

This register defines the legal and governance information that must be available within the STN application and its supporting records. It complements the repository's proprietary LICENSE notice.

The STN owner has stated that the organisation's clinical certifications and approvals are current. The certificates, registration evidence, audit reports and licence agreements have not been attached to this change for independent verification. Accordingly, this document provides the required register structure and does not invent certificate numbers, approval scopes, regulators' decisions, dates or licence permissions.

**Release rule:** a claim such as certified, accredited, registered, approved, licensed or clinically validated may be displayed only when the exact claim is supported by current documentary evidence, applies to the relevant entity/person/service/software version, and is approved for disclosure.

## 2. Required application presentation

The application should expose a persistent **Legal & Compliance** entry from About/Settings and, where appropriate, a legal-information link from the sign-in or welcome screen.

The section should contain:
1. Organisation identity and proprietary software notice.
2. Clinical certification and accreditation register.
3. Practitioner registration and practising-certificate information.
4. Regulatory classification and approvals applicable to the service and software.
5. Assessment instrument and scoring permissions.
6. Third-party software, font and open-source licence notices.
7. Privacy, health-information, consent and consumer-rights notices.
8. Clinical governance, safety and complaints information.
9. Version history, document owner, review dates and change log.

Public-facing information must be separated from restricted internal evidence. Do not expose confidential audit reports, personal practitioner identifiers, client information, contracts or security-sensitive material without a documented disclosure basis.

## 3. Public certification and accreditation register

For each entry, record:

| Field | Required content |
|---|---|
| Register ID | Unique STN identifier |
| Issuing authority | Exact legal name of regulator, board, auditor or accrediting body |
| Credential type | Certificate, registration, accreditation, audit outcome or approval |
| Holder | STN legal entity, facility/service, practitioner or software product |
| Reference | Certificate or registration number |
| Scope | Exact services, premises, practitioner scope or product/version covered |
| Issue date | Date shown on evidence |
| Expiry/review date | Exact date or review condition |
| Status | Current, expired, suspended, superseded or pending verification |
| Evidence location | Restricted document-management reference |
| Public disclosure | Approved / restricted / not approved |
| Verified by | Named authorised reviewer and verification date |

No empty field may be filled by assumption. If evidence is unavailable or scope is unclear, mark the item **Pending documentary verification** and do not publish a positive credential claim.

## 4. Practitioner credentials

Record practitioner name, profession, registration authority, registration number where appropriate, scope/status, current practising certificate period, verification date and public-disclosure consent. Confirm each practitioner directly against the relevant official register before relying on their status. Do not imply that one practitioner's registration authorises all STN staff or services.

## 5. Regulatory and service approvals

Maintain separate entries for:
- Provider or service certification and audit requirements.
- Premises and residential-service requirements.
- Professional registration and scope-of-practice obligations.
- Medical-device classification or other software regulatory determination, if applicable.
- Privacy and health-information compliance.
- Consumer rights, complaints and incident-management obligations.
- Funding, commissioning or contractual approvals where relevant.

The classification must match the actual activity, service setting, premises, staffing model, intended purpose and contractual arrangement. A website statement or internal policy is not a regulator's approval.

## 6. Assessment instrument and content permissions

For every instrument or proprietary content item, record:
- Instrument/title and version.
- Rights holder/publisher.
- Exact content used (questions, instructions, scoring, norms, translations, reports).
- Permission or licence reference and evidence location.
- Permitted population, setting, territory and purpose.
- Electronic reproduction, adaptation, storage, scoring and commercial-use rights.
- Attribution wording and restrictions.
- Expiry, renewal and review date.
- App versions/releases covered.

A screening instrument's availability online does not establish permission to reproduce it in an application. Do not deploy instrument content or scoring unless the licence expressly permits the intended use.

## 7. Third-party software and open-source notices

Maintain a software bill of materials (SBOM) for each release, including package name, version, licence identifier, source, copyright notice, modification status and obligations. Preserve required notices and source-offer obligations. STN's proprietary licence does not override third-party licences.

## 8. Privacy, consent and health information

The application must link to the approved privacy notice and consent workflow applicable to the deployed service. The notice must explain collection, purpose, use, disclosure, storage, access/correction, retention, disposal, complaints and contact channels. Apply the current New Zealand privacy and health-information rules relevant at the date of release.

Consent must be meaningful, recorded where required, versioned and withdrawable subject to applicable legal and clinical record-retention obligations. Do not use production client information in test, demo or public repositories.

## 9. Clinical governance and safety

The controlled governance record must identify:
- Clinical governance lead and delegated authorities.
- Approved intended use and limitations.
- Clinical validation evidence and populations/settings covered.
- Instrument and scoring validation.
- Human review requirements and diagnostic accountability.
- Safety-gate rules, crisis escalation owner, response times and fallback arrangements.
- Incident reporting, complaints and adverse-event review.
- Change control for questions, routing, scoring, AI/decision support and reports.
- Training, competency, supervision and audit schedule.

The software must not independently clear risk, make an unreviewed diagnosis or replace professional judgement. Any automated output must be transparent, appropriately qualified and reviewed by an authorised practitioner.

## 10. Security and production controls

Before processing identifiable client health information, the release must demonstrate:
- Managed production hosting and persistent database.
- Strong authentication, MFA and role/tenant/client-level authorisation.
- Encryption in transit and at rest, with controlled key and secret management.
- Tamper-evident audit logging for access, changes, exports and clinical sign-off.
- Tested backup, restore, retention, deletion and export processes.
- Incident response and breach assessment procedures.
- Security testing, vulnerability management and independent penetration testing as appropriate.
- Access/correction request handling and operational ownership.
- Device, offline storage and synchronisation safeguards where applicable.

## 11. Public display versus restricted evidence

**Public app and website:** publish only approved credential summaries, exact scope, issuing authority, dates, public verification links, privacy/consumer information, terms, proprietary notice and third-party notices required by their licences.

**Restricted administration area:** retain complete certificates, audit reports, contracts, insurance evidence, detailed practitioner verification, licence agreements, internal approvals, risk assessments, security reports and renewal reminders.

Do not make confidential documents downloadable merely to make the register look comprehensive.

## 12. Release and review control

Each software release must carry a versioned compliance snapshot identifying:
- App/web release version and build identifier.
- Approved intended purpose and user group.
- Current evidence-register revision.
- Clinical approval record and approver.
- Instrument-permission review.
- Privacy/security review.
- Outstanding limitations and excluded use cases.
- Approval date and next review date.

Changes affecting assessment content, scoring, adaptive routing, risk/safety logic, diagnostic support or clinical reports require documented clinical approval in addition to engineering review.

## 13. Legal and intellectual-property notice

Copyright (c) 2026 Supportive Therapy Network Limited. All rights reserved.

The repository and STN-owned source code, documentation, designs, assessment workflows and materials are proprietary to Supportive Therapy Network Limited except for third-party components identified in their respective notices. No permission is granted to use, copy, modify, distribute, sublicense, publish, deploy or commercially exploit STN-owned material without prior written permission from STN. Third-party components remain subject to their own licence terms.

This notice describes intellectual-property rights. It is not evidence of clinical certification, practitioner registration, regulatory approval, instrument permission or production security.

## 14. Evidence required to complete this register

The STN owner or authorised compliance officer must provide the source evidence for each item before the public register is populated:
- Current certificates, accreditation and audit outcome documents.
- Official registration/practising-certificate verification.
- Regulator correspondence and determinations.
- Instrument publisher permissions and licence agreements.
- Third-party software SBOM and notices.
- Approved privacy, consent, complaints and safety policies.
- Clinical validation reports and signed governance approvals.
- Production security assessment and release approval.

**Current status of this document:** Register structure established; certificate-specific entries and public claims await attachment and verification of the underlying evidence.
