# STN clinical release dossier

**Purpose:** Evidence index for a controlled clinical software release.
**Current repository disposition:** Private development / release candidate. This dossier is a template and evidence index, not a certificate of clinical approval.

## 1. Product and release identity

- Product: STN Whole Person Assessment
- Version/build: v0.6.1+7 (supplied archive metadata; verify against the final build)
- Release commit: to be recorded
- Build artifact SHA-256: to be recorded
- Intended use and exclusions: to be approved and version-controlled
- Accountable release owner: to be named in signed decision
- Clinical safety officer: to be named
- Privacy officer: to be named
- Technical/security owner: to be named

## 2. Approval and authorisation evidence

Record the issuing body, approval reference, date, expiry/review date, approved software version, approved setting, clinician roles, intended population, conditions, exclusions and any post-market obligations. Attach the source approval in the controlled company evidence store. Do not publish confidential approval documents in a public repository.

**Status:** Owner has stated that government authorisation and clinical verification exist. The approval details and scope have not been independently evidenced in this repository.

## 3. Mandatory evidence index

| Control | Evidence required | Status |
|---|---|---|
| Clinical validation | Protocol, sample/method, results, limitations, independent reviewer and signed report | Not evidenced here |
| Clinical safety case | Hazard log, risk controls, residual-risk acceptance and safety sign-off | Not evidenced here |
| Crisis escalation | Live workflow, named responder, acknowledgement, timeout, fallback and drill results | Not evidenced here |
| Instrument permissions | Instrument-by-instrument written digital-use and scoring permissions | Not evidenced here |
| Clinical Core traceability | Source item/rule → UI → logic → test → report mapping | Not evidenced here |
| Identity and access | Approved identity provider, MFA, role model and negative authorisation tests | Not evidenced here |
| Clinical record | Server-side persistence, encryption, tenant isolation and migration controls | Not evidenced here |
| Audit | Tamper-evident access, change, export and sign-off events | Not evidenced here |
| Privacy | PIA, collection notices, consent, access/correction, disclosure and retention | Not evidenced here |
| Security | Threat model, SBOM, secret scan, penetration test and remediation | Not evidenced here |
| Accessibility and UAT | Supported-device matrix, accessibility results and user acceptance | Not evidenced here |
| Operations | Monitoring, backup/restore, incident response, support and rollback | Not evidenced here |

## 4. Release decision

A release decision must identify the exact commit and artifact hash, approved deployment environment, intended users, approved clinical scope, outstanding limitations, monitoring and rollback arrangements. It must be signed and dated by the accountable release owner and required clinical, privacy and security approvers.

**Decision:** No production clinical deployment is authorised by this repository record. Do not use real patient information in this build until the evidence is attached to the controlled release record and all mandatory gates are closed.
