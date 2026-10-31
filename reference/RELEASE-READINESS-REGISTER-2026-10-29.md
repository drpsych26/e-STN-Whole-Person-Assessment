# STN release-readiness register — 29 October 2026

**Disposition: HOLD — private development only. Do not publish or use with real clients.**

This register is an evidence gate, not a declaration of readiness. Each item requires a named owner, dated evidence and explicit sign-off.

| Gate | Required evidence | Status |
|---|---|---|
| Source-of-truth | Approved baseline and traceability from paper pilot to implementation | OPEN |
| Functional completeness | Every workflow, marker, score, route and report mapped to automated tests | OPEN |
| Instruments/scoring | Exact versions, permissions, scoring specs and independently checked fixtures | OPEN |
| Safety | Approved protocol, named human responder, acknowledgement, fallback and fail-safe tests | OPEN |
| Clinical validation | Independent evaluation and signed limitations report | OPEN |
| Privacy/consent | Privacy impact assessment, notice, consent, access/correction, disclosure and retention workflows | OPEN |
| Security | Threat model, independent penetration test, secrets/dependency scans and remediation | OPEN |
| Identity/access | Approved identity provider, least privilege, role boundaries and revocation tests | OPEN |
| Persistence/audit | Managed database, encryption, immutable audit, backup/restore and disposal evidence | OPEN |
| Integration | Approved interface specs, data authority, consent, error handling and partner agreements | OPEN |
| Accessibility/usability | Keyboard/screen reader, contrast, plain-language, cultural-safety and usability testing | OPEN |
| Platform QA | Reproducible CI tests and supported web/tablet/mobile builds | OPEN |
| Operations | Monitoring, incident response, support ownership, rollback and disaster recovery | OPEN |
| Legal/regulatory | Qualified review of intended purpose, applicable NZ obligations and claims | OPEN |
| Pilot approval | Approved protocol, staff training, safety coverage, stop criteria and evaluation plan | OPEN |
| Final release | All critical/high defects closed; signed gates and tagged build | OPEN |

## Stop conditions

Any missed or silently downgraded safety-positive response; cross-client access; unsafe report rendering; unexplained/non-reproducible scoring; unapproved instruments; production use of browser localStorage as the clinical record; missing human escalation owner; or unresolved critical/high security issue blocks release.

## Release stages

1. Prototype demonstration using synthetic data only.
2. Internal alpha with synthetic data and controlled access.
3. Supervised pilot only after formal clinical, privacy, security and operational approvals.
4. Production only after all gates close with evidence.

A checked box without a test result or signed evidence is not closure.