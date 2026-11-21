# Defect and remediation register

**Commit reviewed:** 3d6d541 (branch `feature/stage1-corrections`)
**Status key:** FIXED (code change plus passing test), OPEN (no fix yet), PARTIAL (mitigated, not closed), EXTERNAL (needs a person, account or document outside this repo)

| ID | Severity | Finding | Status | Evidence / remediation |
|---|---|---|---|---|
| D-001 | High | Onboarding verification flags were caller-supplied booleans | FIXED | Verification now only from signed IdP events (`verification.py`). Tests: `test_intake_cannot_mark_verification_by_assertion`, `test_advance_route_ignores_caller_evidence_and_requires_events`, the signed-event tests. |
| D-002 | High | Provisional accounts could be granted clinical roles | FIXED | Refused at grant (`ProvisionalRestriction`) and denied at check (`access.denied_provisional`). Tests: `test_provisional_account_cannot_be_granted_clinical_role`, `test_provisional_account_is_denied_clinical_routes_even_if_role_held`. |
| D-003 | High | Intake staff could attest their own advancement | FIXED | Separation of duties enforced (`attester != advancer`, customer cannot attest). Tests: `test_attester_cannot_advance_same_stage`, `test_customer_cannot_attest_own_stage`. |
| D-004 | High | Live Entra External ID tenant not connected; no real sign-in tested | EXTERNAL | Needs tenant ID, client registration and an account owner. Until then all protected routes fail closed (503). |
| D-005 | High | Access-denial rows were lost when the exception rolled back the transaction | FIXED | Denials committed before raising. Covered by `test_access_denial_is_audited_on_routes` and `test_denied_grant_is_audited`. |
| D-006 | Medium | No migration framework; schema created on every connection | FIXED | Forward-only runner with checksum enforcement and transactional apply. Tests in `test_migrations_and_export.py`. |
| D-007 | Medium | Two audit trails (legacy `audit_log` and `audit_chain`) | FIXED | Legacy table dropped by migration `0003`. All client audit uses the chain. Test: `test_legacy_audit_log_is_dropped_and_chain_is_the_only_trail`. |
| D-008 | High | Audit chain protected only by SQLite triggers, which can be dropped by anyone with file access | PARTIAL | External, independently verifiable export added (`audit_export.py`). Not yet shipped to write-once storage (see D-009). Triggers remain the only in-database control. |
| D-009 | High | No immutable external retention | EXTERNAL | Export segments and manifests are implemented and verified offline. Upload to write-once storage needs the Azure storage account and an immutability policy. |
| D-010 | Medium | Client-record and onboarding routes had no rate limiting | OPEN | Not implemented. Required before any public exposure. |
| D-011 | Medium | Fail-closed tests accepted 401 or 503 for garbage tokens | PARTIAL | Tests assert a non-200 response and the correct code when the IdP is unconfigured. Tightening to 401 requires the IdP configured in tests. |
| D-012 | Medium | Audit detail not checked for personal data | OPEN | Convention only. Needs a schema or allow-list for each action. |
| D-013 | High | Prototype clinical data stored in browser `localStorage` | OPEN | Prototypes are not connected to the API. Must not be used with real client data. |
| D-014 | High | No Content-Security-Policy on prototype pages | OPEN | Not implemented. |
| D-015 | High | Crisis numbers absent from prototype and Flutter builds | OPEN | Present only in `reference/source-html/assessment-demo.REVIEW-CORRECTED.html`. A release candidate must be chosen and its panel verified (H10). |
| D-016 | High | Safety escalation is display-only | OPEN | Stage 2 design covers the escalation record. Not built. |
| D-017 | Medium | Gate engine not run on release candidates | FIXED | Workflow `.github/workflows/release-gates.yml` added; dry run blocks all 13 gates. |
| D-018 | Medium | Public clinical repository holds governance and business material | EXTERNAL | Visibility change blocked by the session proxy (HTTP 403). The account owner must change it. |
| D-019 | Medium | PR #41 and PR #16 are open, stale and on the release path | OPEN | See `docs/release/PR-REVIEW-41-16.md`. Not merged. |
| D-020 | High | Database is SQLite; no managed encrypted database; no tested restore | OPEN | Gate G10. Not started. |
| D-021 | Medium | Encryption key comes from an environment variable; no rotation | OPEN | Needs a secrets manager (Azure Key Vault) and a rotation procedure. |
| D-022 | Medium | Registration grants the `customer` role before identity is verified | PARTIAL | Customer role carries read-own permissions only. Account creation via real sign-in is still pending (D-004). |
