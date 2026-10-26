# STN NZ privacy, security and clinical review pack

**Status:** Requirements and evidence checklist; not a legal opinion, completed PIA, security certification or clinical approval.

## 1. Intended processing inventory

Before selecting a production architecture, document:
- controller/agency and all service providers with access to health information;
- purposes for each data field, collection source, consent/legal basis, recipients and retention period;
- data locations, backups, support access, telemetry, crash reports, analytics, AI services and overseas subprocessors;
- access, correction, export, restriction, retention and disposal paths;
- incident detection, privacy breach assessment, notification and recovery responsibilities.

Do not collect identifiable client information in the current prototype or test logs.

## 2. Minimum privacy review deliverables

- approved privacy impact assessment and data-flow map;
- collection notice and informed-consent wording reviewed for the actual workflow;
- access and correction process, identity verification and response ownership;
- retention/disposal schedule with legal/clinical record requirements confirmed by NZ counsel;
- disclosure and overseas-processing assessment, including vendor contracts and subprocessors;
- breach response and notification procedure, incident register and staff training;
- data minimisation review and documented reason for each sensitive field;
- review of the Health Information Privacy Code 2020, applicable Privacy Act 2020 obligations and amendments in force at deployment.

## 3. Minimum security architecture

A device-only Flutter app with encrypted local Hive boxes is not a complete multi-user clinical-record platform. Before clinical deployment, document and test:
- identity provider, secure authentication, account lifecycle, MFA decision, session expiry/revocation and recovery;
- server-side role-based access and client/organisation scoping on every API and data operation;
- least privilege, separation of duties, administrator controls and periodic access review;
- encryption in transit and at rest, managed keys/secrets, rotation and recovery;
- append-only audit events for view, create, update, sign, finalise, export, correction, deletion and administrative access;
- versioned immutable finalisation with addendum/correction rather than silent overwrite;
- backup, restore, disaster recovery, outage and offline reconciliation;
- secure build/release pipeline, dependency/SBOM and licence scanning, secret scanning, vulnerability management and signed artifact provenance;
- penetration testing, threat modelling, secure configuration review and documented remediation;
- incident response, monitoring, alerting, breach triage and tested recovery.

## 4. Clinical governance evidence

- named clinical governance lead and decision authority;
- approved Clinical Core version and change-control board;
- instrument inventory with exact version, copyright/licence/permission, intended use, population, scoring instructions and permitted digital reproduction;
- item-level source-to-code traceability and independent rule review;
- diagnostic decision-support boundaries, uncertainty statuses and clinician sign-off;
- safety escalation/handover protocol, staffing model, after-hours fallback and drills;
- user competency/training and supervision records;
- adverse-event/near-miss register, stop criteria and change-triggered revalidation;
- signed go/no-go approval from clinical, privacy, security and product owners.

## 5. Instrument permissions register — mandatory fields

| Field | Required evidence |
|---|---|
| Instrument name and acronym | Exact name |
| Version and publication | Primary source/version date |
| Copyright holder | Verified owner |
| Licence/permission | Written permission or terms allowing digital use |
| Translation/adaptation | Permission and validation evidence where applicable |
| Items and response options | Exact authorised wording and order |
| Scoring/missing data | Authorised manual and version |
| Cut-offs/interpretation | Primary evidence and intended population |
| Digital use/export/storage | Permission explicitly covers the intended implementation |
| Reviewer and approval date | Named accountable reviewer |

No instrument may be represented as validated or licensed until documentary evidence is attached and approved.

## 6. Approval register

| Approval | Required approver | Current status |
|---|---|---|
| NZ privacy impact assessment | STN privacy lead and qualified NZ privacy/legal reviewer | NOT PROVIDED |
| Security threat model and test report | Qualified security engineer | NOT PROVIDED |
| Clinical Core and instrument approval | STN clinical governance lead plus independent qualified clinician | NOT PROVIDED |
| Safety workflow and crisis fallback | Clinical governance lead and service operations owner | NOT PROVIDED |
| Pilot protocol and staff competency | Clinical governance/ethics as applicable and pilot supervisor | NOT PROVIDED |
| Release go/no-go | Named clinical, privacy, security and product owners | NOT PROVIDED |

## 7. Pilot design — outline only

A controlled pilot protocol must specify objective, intended population, exclusion/escalation criteria, participant information and consent, clinician supervision, instrument licensing, training, data minimisation, outcome measures, incident capture, adverse event review, stop rules, data retention, analysis plan, and independent sign-off. Begin with synthetic usability testing. Any later use with real participants requires a separate approved protocol and governance decision. This document is not that approval.