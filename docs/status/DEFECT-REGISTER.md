# Defect register

Updated 25 Nov 2026. Evidence = tests executed in this environment (SQLite + PostgreSQL 16 + Redis) and/or GitHub CI on the named PR. Responsible agent: Claude (engineering) unless an owner or clinical action is named.

| ID | Description | Severity | Status | Evidence / PR | Files | Dependency / next step | Verified |
|---|---|---|---|---|---|---|---|
| D-01 | Workflow command injection | High | Verified (not present) | `check_workflow_security.py` in CI (#59) | `.github/workflows/*`, `tools/` | — | 25 Nov |
| D-02 | Untrusted interpolation | High | Verified (not present) | same | same | — | 25 Nov |
| D-03 | Unpinned actions | High | Verified | #59 app, #14 website; CI rule | workflows | Merge | 25 Nov |
| D-04 | Audit transaction integrity | High | Verified on main | advisory lock, in-transaction audit | `audit.py`, `db.py` | — | 25 Nov |
| D-05 | Denial persistence | Medium | Verified on main | refusals audited | modules | — | 25 Nov |
| D-06 | Live IdP integration | High | **Requires external dependency** | synthetic-token tests only | `auth.py`, `identity_events.py` | Entra tenant; event-relay decision (`IDENTITY-AND-ONBOARDING.md` §5) | — |
| D-07 | Onboarding and provisional accounts | High | Implemented + Verified (synthetic) | #63: 70 tests | `client_accounts.py`, `clinician_registry.py`, `identity_events.py`, migration 005 | Live tenant; client UI | 25 Nov |
| D-08 | Attestation reference validation | High | Implemented + Verified | #63: 14 tests | `clinician_registry.py` | Approved register hosts list | 25 Nov |
| D-09 | PII in audit | High | Verified on main | schema review | `audit.py` | — | 25 Nov |
| D-10 | Rate limiting | Medium | Verified | Redis tests | `ratelimit.py` | — | 25 Nov |
| D-11 | CSP `'unsafe-inline'` in prototypes | Medium | Implemented + Verified for scripts | #67: browser workflow run, CI check | `prototype/*.html`, `tools/prototype_strict_csp.py` | `style-src 'unsafe-inline'` remains (low) | 25 Nov |
| D-12 | SQLite / no-TLS in hosted envs | High | Verified | #59: 9 tests | `db.py`, `main.bicep` | Merge | 25 Nov |
| D-13 | Backup storage and real restore | High | Implemented (code/IaC); **Blocked** for live restore | #68: dump upload with read-back; restore drill in CI | `audit_export.py`, `evidence-storage.bicep` | Azure subscription + cost approval | 25 Nov (local) |
| D-14 | Key rotation against Key Vault | Medium | Implemented; **Blocked** live | `rekey.py` tests | `rekey.py`, `crypto.py` | Azure | — |
| D-15 | Client crisis panel | High | Implemented + Verified; **Requires clinical approval** | #66: Node, backend, browser, axe 0 | `frontend/crisis-panel/`, `crisis_resources.py` | D-SAFE-01; human check of regional numbers | 25 Nov |
| D-16 | Safety escalation lifecycle | High | Implemented + Verified; **Requires clinical approval** | #59, #64 | `safety_escalations.py` | D-SAFE-01..05 | 25 Nov |
| D-17 | App repository public | High | **Requires owner action** | API shows public; change refused in-session | — | O-1 | — |
| D-18 | External immutable audit retention | High | Implemented (code/IaC); **Blocked** live | #68: 9 tests | `audit_export.py`, `evidence-storage.bicep` | Azure + lock decision | 25 Nov (local) |
| A-02 | Prototypes use `localStorage` | Medium | Open (synthetic UAT only) | — | `prototype/` | Replace with API once client portal exists | — |
| A-03 | Android job-wide `contents: write` | Medium | Implemented | #62 + CI rule 4 | `android-apk.yml` | One manual build with keystore secrets to confirm | 25 Nov (static) |
| A-04 | 51 stale branches | Low | Open | — | — | Owner approves cleanup list | — |
| A-05 | Disposal during unresolved escalation | Medium | Implemented + Verified | #59 | `governance.py` | D-SAFE-06 confirm | 25 Nov |
| W-01 | Website lists Lifeline as 24/7 | **Critical (safety)** | Implemented; **live until merge** | website #14 | 10 pages | **Owner merge #14** | 25 Nov |
| W-02 | Website HTTPS certificate / redirect | High | **Requires owner action** | cert `*.github.io` on custom domain | Pages settings | O-2 | — |
| W-03 | Website publishes `PRIVACY-NOTICE-DRAFT.md` and `README.md` | Medium | Implemented; **live until merge** | website #15, CI build green | `pages.yml` | Owner merge #15 | 25 Nov |
| W-04 | Website heading order, no canonical/OG, no robots/sitemap/404 | Low | Implemented + Verified | #15, axe 0 on 22 page views | pages | Merge | 25 Nov |
| W-05 | Website PRs never validated by CI | Low | Implemented + Verified | #15 PR run: build success, deploy skipped | `pages.yml` | Merge | 25 Nov |
| B-01 | Release decision could never pass (evidence read from the candidate commit) | High | Fixed | #60 | `release-gates.yml` | Merge | 25 Nov |
| B-02 | JWKS/identity-event audience could equal API audience | High | Prevented by design | #63: fail closed if equal | `identity_events.py` | — | 25 Nov |
