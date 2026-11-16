# STN clinical release dossier

**Purpose:** Controlled evidence index for the STN Whole-Person Assessment release.
**Repository disposition:** Public source repository. This dossier records release evidence and does not itself constitute a regulatory certificate or deployment approval.

## 1. Product and release identity

- Product: STN Whole Person Assessment
- Current source baseline: main branch; record the exact release commit and tag at release
- Build artifact SHA-256: record for each release artifact
- Intended use and exclusions: governed by the approved STN clinical validation and service scope
- Accountable release owner: record in the signed release decision
- Clinical safety officer: record in the controlled governance record
- Privacy officer: record in the controlled governance record
- Technical/security owner: record in the controlled governance record

## 2. Clinical validation status

**Status: NOT VERIFIED FOR THIS RELEASE.** The repository does not currently contain a version-specific validation record that establishes the exact software build, assessment content, scoring rules, intended-use population, methodology, limitations, independent reviewer and accountable clinical sign-off covered by validation.

This status does not claim that no clinical review or validation work has ever occurred. It means the evidence has not been independently mapped to this release in the controlled evidence index. Do not describe clinical validation as complete for this release until the responsible clinical owner records the evidence reference, approval date, methodology, population, limitations, reviewer/signatory, intended use and exact assessment/software version covered. Confidential clinical evidence must remain in the controlled evidence store and must not be uploaded to this public repository.

## 3. Remaining release evidence index

| Control | Release evidence / record | Status |
|---|---|---|
| Clinical validation | Version-specific validation report, methodology, population, limitations, reviewer/signatory and exact release mapping | NOT VERIFIED FOR THIS RELEASE — evidence and accountable sign-off required |
| Clinical source traceability | Approved source item/rule → UI → logic → test → report mapping | Verify exact release coverage |
| Instrument permissions | Instrument-by-instrument written digital-use, reproduction, scoring and reporting permissions | Record/verify by instrument |
| Clinical safety case | Hazard log, risk controls, residual-risk acceptance and accountable sign-off | Release evidence required |
| Crisis escalation | Named responder, acknowledgement, timeout, fallback, after-hours coverage and drill record | Operational evidence required |
| Identity and access | Approved identity provider, MFA decision, role model and negative authorisation tests | Technical evidence required |
| Clinical record | Server-side persistence, encryption, tenant isolation and migration controls | Technical evidence required |
| Audit | Tamper-evident access, change, export and sign-off events | Technical evidence required |
| Privacy | Completed PIA, notices, consent, access/correction, disclosure and retention | Governance evidence required |
| Security | Threat model, SBOM, secret scan, penetration test and remediation | Security evidence required |
| Accessibility and UAT | Supported-device matrix, accessibility results and user acceptance | Test evidence required |
| Operations | Monitoring, backup/restore, incident response, support and rollback | Operational evidence required |

## 4. Release decision

The release decision must identify the exact source commit and artifact hashes, approved deployment environment, intended users, approved clinical scope, known limitations, monitoring and rollback arrangements. It must be signed and dated by the accountable release owner and the required clinical, privacy, security and operational approvers.

Clinical validation must not be represented as complete for a release until version-specific evidence and accountable sign-off are recorded. Production activation remains a separate release decision dependent on the technical, privacy, security, operational, licensing and clinical controls above.