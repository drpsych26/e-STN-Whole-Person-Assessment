# Defect and remediation register

**Revision:** 2 (responds to the PR #52 independent review, items 1–10)
**Status key:** FIXED (code change plus a passing test in this repository), PARTIAL (mitigated; not closed), OPEN (no fix), EXTERNAL (needs an account, person or document outside this repository), DESIGN (designed, not built)
**Important:** Test results here come from backend tests using synthetic identities and synthetic data. They are not production validation, and no item is closed on that basis alone.

## Findings from the first review (revision 1)

| ID | Severity | Finding | Status | Evidence / remaining work |
|---|---|---|---|---|
| D-001 | High | Verification flags were caller-supplied booleans | FIXED | Verification comes only from signed events (`verification.py`). The event source is itself unproven against Entra; see D-023. Tests: `test_intake_cannot_mark_verification_by_assertion`, `test_advance_route_ignores_caller_evidence_and_requires_events`. |
| D-002 | High | Provisional accounts could be granted clinical roles | FIXED | Refused at grant and denied at check. Tests: `test_provisional_account_cannot_be_granted_clinical_role`, `test_provisional_account_is_denied_clinical_routes_even_if_role_held`. |
| D-003 | High | Intake staff could attest their own advancement | FIXED | Separation of duties enforced. Tests: `test_attester_cannot_advance_same_stage`, `test_customer_cannot_attest_own_stage`. |
| D-004 | High | Live Entra External ID tenant not connected; no real sign-in tested | EXTERNAL | Tenant needed (owner). Until then all protected routes fail closed. |
| D-005 | High | Access-denial rows were lost on rollback | FIXED | Denials committed before raising. Covered by the transaction tests (D-028). |
| D-006 | Medium | No migration framework | FIXED | Forward-only runner with checksums. Tests in `test_migrations_and_export.py`. |
| D-007 | Medium | Two audit trails | FIXED | Legacy table dropped by migration `0003`. |
| D-008 | High | Audit chain protected only by SQLite triggers | PARTIAL | Triggers can be removed by anyone with file access. Mitigation is the offline export (`audit_export.py`). Real protection needs D-009. |
| D-009 | High | No immutable external retention | EXTERNAL | Export and offline verification exist. Upload to write-once storage needs an Azure storage account with immutability policy (owner decision). |
| D-010 | Medium | No rate limiting | PARTIAL | Sliding-window limits added (`ratelimit.py`) on write and sensitive-read routes and on verification ingestion. Limits are **per process in memory**, so they are not effective across multiple instances until a shared store is added. Tests: `test_ratelimit.py` (7). |
| D-011 | Medium | Fail-closed tests accepted 401 or 503 | PARTIAL | Tightening to 401 needs the IdP configured in tests. |
| D-012 | Medium | Audit detail not checked for personal data | FIXED | Action-specific allow-list with enumerated values and identifier patterns. Unknown actions and free text are refused before any write. Tests: `test_schema_refusal_writes_neither_audit_nor_data`, plus the existing chain tests now use schema-valid actions. |
| D-013 | High | Prototype clinical data stored in browser `localStorage` | OPEN | Prototypes are not connected to the API and must not hold real client data. |
| D-014 | High | No Content-Security-Policy on prototype pages | PARTIAL | CSP meta tag added to all three prototype pages, with no external scripts, no `eval` and no wildcards (`test_prototype_csp.py`, 10 tests). `script-src` keeps `'unsafe-inline'` because the prototypes use inline handlers. Removing it needs the handlers moved to external files. `frame-ancestors` is ignored in a meta tag and needs a response header on the hosting platform (EXTERNAL). |
| D-015 | High | Crisis numbers absent from prototype and Flutter builds | PARTIAL | Verified content register built (`crisis_resources.py`) and served publicly (`GET /v1/safety/crisis-resources`). On-screen panel not built in any build. Clinical review not done (`clinically_reviewed: false`). Two hours entries unresolved. See `docs/design/CRISIS-PANEL-AND-ESCALATION.md`. |
| D-016 | High | Safety escalation display-only | PARTIAL | Escalation workflow built: open, acknowledge, resolve with ownership, timestamps, coded resolution and owned documentation (migration `0005`, `safety.py`, 20 tests). No on-call notification (D-025). Not yet exercised with clinical staff. |
| D-017 | Medium | Gate engine not run on release candidates | FIXED | Workflow runs on PR (backend tests) and on dispatch (gate report). A dry run blocks all 13 gates with exit 1. Not yet run on GitHub Actions in this pass; see the test report. |
| D-018 | Medium | Public repository holds governance and business material | EXTERNAL | Visibility change blocked by the session proxy. Owner action. |
| D-019 | Medium | PR #41 and #16 open on the release path | OPEN | Review in `docs/release/PR-REVIEW-41-16.md`. Decision on PR #16 (brand) and PR #41 (gate document) pending the owner. Neither merged. |
| D-020 | High | SQLite database; no managed encrypted database; no tested restore | OPEN | Gate G10. Not started. |
| D-021 | Medium | Encryption key from environment; no rotation | OPEN | Needs Azure Key Vault and a rotation procedure (owner decision on Azure). |
| D-022 | Medium | Customer role granted before identity verified | PARTIAL | Customer role has read-own permissions only. Real sign-in pending D-004. |

## Findings from the PR #52 review (revision 2)

| ID | Severity | Finding | Status | Evidence / remaining work |
|---|---|---|---|---|
| D-023 | High | Verification event architecture is not Entra-native. Entra does not post signed verification events to a custom endpoint, and no documented `phone_verified` claim was found. | OPEN (blocker) | Documented in `docs/security/IDENTITY-PROVIDER-VERIFICATION.md`. Requires a tenant spike (captured tokens, `amr` values, JWKS validation). Phone verification has no proven evidence source. Onboarding cannot complete against a live provider until resolved. |
| D-024 | Medium | Escalations are not assigned to a named clinician at opening | OPEN | Design gap; depends on team allocation (Stage 3). |
| D-025 | High | No notification of on-call staff for urgent escalations; visibility depends on polling | OPEN | Required before client-facing release. |
| D-026 | Critical | GitHub Actions script injection: `inputs.commit` and `inputs.evidence` interpolated into `run:` | FIXED | Inputs now reach the shell only through `env:`, are validated against strict patterns before any checkout, and no `${{ }}` expression appears in a `run:` block (checked by script). Path traversal refused. Workflow file `.github/workflows/release-gates.yml`. |
| D-027 | Medium | Third-party actions pinned to mutable tags | FIXED | All 20 `uses:` references pinned to a 40-character commit SHA with the tag in a comment. Caveat: SHAs were resolved with `git ls-remote` on 21 November 2026, not from a signed or independently verified source. Reviewer should compare against the upstream repositories. |
| D-028 | High | Audit transaction boundaries untested | FIXED | `test_audit_transactions.py` (11 tests): denied read and update leave durable audit rows; missing-record reads indistinguishable from denial; failed decryption recorded as `integrity_failure` and committed; an application exception after a denial does not erase it; create and update are atomic when the audit write fails; schema refusal writes nothing. |
| D-029 | High | Attestation references were free text (for example `screen-1`) | FIXED | Migration `0004` adds `platform_records`. An attestation must cite an active record of the matching type, in the same case and for the same subject, whose responsible staff member is the attester. A team assignment record names its assignee, who must hold the authorised clinician role. Free-text rows do not satisfy a stage (test). Records are append-only with fixed fields; only `active` to `withdrawn` is permitted. Tests: 9 new record tests in `test_onboarding_controls.py`. |
| D-030 | Medium | Platform records and escalations can be altered at database level | PARTIAL | Triggers enforce append-only and fixed fields. As with D-008, a person with file access can remove triggers. External retention (D-009) is the real control. |
| D-031 | Medium | Prototype CSP allows inline script | PARTIAL | See D-014. |
| D-032 | High | Gate evidence not independently verifiable | PARTIAL | The gate job records the evidence file's SHA-256 in the run summary, confirms the file is tracked at the commit, and reports without setting any gate. Missing: a signed record or an independent verifier that re-computes the digest from the repository. |
| D-033 | Medium | Pull-request validation not automated | FIXED | `pull_request` trigger runs backend tests on every PR. Release evaluation stays manual (`workflow_dispatch`). No workflow approves clinical release. |
| D-034 | Medium | Stale and conflicting open PRs | OPEN | See D-019. |
| D-035 | Medium | Lifeline and Suicide Crisis Helpline hours conflict between sources | OPEN | Recorded as unresolved in `crisis_resources.py`. Must be confirmed with each service before display. |
| D-036 | Medium | Escalation overdue threshold (15 minutes) is an engineering value | OPEN | Must be set by the clinical reviewer. |
| D-037 | High | Clinical review not performed | EXTERNAL | Independent clinical reviewer appointment required (owner decision). |
