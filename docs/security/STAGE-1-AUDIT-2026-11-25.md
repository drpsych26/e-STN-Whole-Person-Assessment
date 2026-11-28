# Stage 1 repository audit and defect register — 25 November 2026

**Scope:** Stage 1 of the STN Master Autonomous Development Directive: verified baseline, PR #52 review, the 18 listed defects, and fixes that can be made and tested without external credentials.
**Release status (unchanged): NOT CLINICALLY SIGNED OFF. NOT CLIENT READY.** Nothing in this audit changes that.

## 1. Verified baseline

| Item | Verified state | How verified |
|---|---|---|
| Default branch | `main`, head `0337d87` (24 Nov 2026, PR #58 deploy kit) | `git` clone |
| Branches | 51 besides `main`. Most were squash-merged, so git cannot tell which are finished; none were deleted | `git branch -r` |
| Repository visibility | **Public** | Anonymous clone succeeded |
| PR #52 | Open, draft, 8 commits, no reviews, no check results shown | GitHub PR page |
| PR #41 | Closed without merging on 23 Nov 2026 (superseded) | GitHub PR page |
| PR #16 | Not re-verified in this session (GitHub rate limit) | — |
| Backend tests on `main` | **331 passed, 4 skipped** with real PostgreSQL 16 and Redis. The 4 skips are by design (a parameter combination that does not apply) | Local run, `STN_REQUIRE_PG_TESTS=1` |
| Backend tests on `feature/stage1-corrections` | 172 passed (SQLite only) | Local run |
| Repo checks (`tests/*.test.js`, `tools/static_quality_check.py`) | Pass | Local run |

## 2. PR #52 finding: do not merge; port what is unique

`main` moved on after PR #52 branched from `af5122f`. PRs #54 to #58 independently built the audit chain, role checks, rate limiting, migrations and client store, with a different design (organisation separation, PostgreSQL and SQLite migrations in separate folders, Entra role claims). Merging #52 into `main` produces **8 file conflicts** (`audit.py`, `clients.py`, `main.py`, `migrate.py`, `ratelimit.py`, `rbac.py`, `store.py`, `tests/test_ratelimit.py`), and its migrations (`0001`–`0005`) do not fit `main`'s migration layout.

| PR #52 component | On `main`? | Recommendation |
|---|---|---|
| Hash-chained audit, RBAC, rate limiting, migrations, store | Yes, re-implemented (stronger: org separation, advisory-locked audit chain, Redis limiter) | Drop #52's versions |
| Safety escalation (`safety.py`, migration 0005) | **No** | **Ported in this change** (section 4) |
| Crisis resources register | No | Verified content moved to `docs/clinical/SAFETY-ESCALATION-MATRIX.md` (hours corrected; see D-12) |
| Release gate engine G01–G13 + workflow | No | Port next (needs adapting to `main`'s evidence locations) |
| Onboarding state machine, IdP signed verification events, attestations | No | Port only when client accounts exist. `main` has clinician sign-in only; there is no client identity yet |
| Audit export (`audit_export.py`) | Partly (export log on `main`) | Compare with `main`'s export before porting |
| Stage 2 design, defect register | Docs only | Keep as reference; this file supersedes the defect register |

Keep PR #52 open and unmerged as a reference until the remaining components are ported, then close it as superseded.

## 3. Defect register (the 18 listed defects, checked against `main` at `0337d87`)

Status uses the directive's scale. **VERIFIED** means a test or check was run in this session and passed; it does not mean approved or deployed.

| # | Defect | Status | Evidence / what remains |
|---|---|---|---|
| D-01 | GitHub Actions command injection | VERIFIED (not present) | All `inputs.*` reach shell only through `env:` and are validated (`deploy-staging.yml` preflight). New `tools/check_workflow_security.py` fails CI if this regresses |
| D-02 | Untrusted workflow input interpolation | VERIFIED (not present) | Same check. No `pull_request_target` triggers |
| D-03 | Third-party action pinning | **FIXED, VERIFIED** | 27 `uses:` lines were tag-pinned (`@v7`, `@v2`). `subosito/flutter-action@v2` ran in the same job as the Android release keystore and a `contents: write` token. All now pinned to commit SHAs; the check fails the build on any unpinned action (confirmed failing on the old files, passing on the new). Dependabot keeps SHAs current |
| D-04 | Audit transaction integrity | VERIFIED (resolved on `main`) | Audit row is written in the same transaction as the change; `pg_advisory_xact_lock` serialises the chain; append-only trigger |
| D-05 | Denial-event persistence | VERIFIED (resolved on `main`) | Refusals are audited as `denied_or_missing` / `rejected_*` inside the transaction before the error is raised |
| D-06 | Identity-provider compatibility | IMPLEMENTED (clinician side) | Entra-style role, org and MFA claims on `main`. Not tested against a real tenant: **blocked on Entra tenant** |
| D-07 | Provisional account restrictions | IMPLEMENTED (clinicians) | Invited, suspended and deactivated clinician accounts are refused. Client accounts do not exist yet |
| D-08 | Attestation reference validation | NOT STARTED on `main` | Exists only on #52; port with onboarding |
| D-09 | Personal information in audit | VERIFIED (resolved on `main`) | Audit columns hold subject ids, codes and record ids only; no payloads |
| D-10 | Rate limiting | VERIFIED (resolved on `main`) | Redis-backed shared limiter, tested against Redis in this session |
| D-11 | Content Security Policy | **FIXED, VERIFIED (partial)** | No CSP on `main` prototypes. Added to all three pages. Checked in headless Chrome: no violations, buttons and logo work. **Residual:** `script-src 'unsafe-inline'` remains because the pages use ~30 inline `onclick` handlers; removing it needs a refactor. A pre-existing 404 on `index.html` is unrelated (same on unmodified `main`) |
| D-12 | SQLite production limitations | **FIXED, VERIFIED** | Infrastructure already used PostgreSQL. Added a fail-closed guard: with `STN_ENVIRONMENT=staging` or `production` (now set by `main.bicep`), the API refuses SQLite and refuses PostgreSQL URLs without `sslmode=require`/`verify-ca`/`verify-full`. 9 tests. Bicep builds and lints |
| D-13 | Backup and restoration | IMPLEMENTED, partly verified | Restore drill script runs in CI. Production keeps 35-day point-in-time backups in NZ North; geo-redundant backup is deliberately off (NZ North has no paired region). **Open:** the immutable logical-dump storage described in the runbook is not provisioned in Bicep. A restore of a real staging database has not been done: **blocked on Azure subscription** |
| D-14 | Encryption key rotation | IMPLEMENTED | `rekey.py` and tests on `main`. Not exercised against Key Vault: **blocked on Azure** |
| D-15 | Crisis panel implementation | NOT STARTED (client-facing) | There is no client-facing crisis panel on `main`; the prototypes are clinician-facing. Verified contact register is ready in `docs/clinical/SAFETY-ESCALATION-MATRIX.md`. **Correction:** Lifeline and the Suicide Crisis Helpline now run 7am to midnight, not 24/7 |
| D-16 | Safety escalation | **IMPLEMENTED, VERIFIED (engineering only)** | New lifecycle: open → acknowledge (ownership) → handover → resolve with coded outcome and documentation; four tiers; overdue queue; admins can view but not act; org separation; append-only. 16 tests on SQLite and PostgreSQL. **Not clinically approved; no notifications.** Open decisions D-SAFE-01 to 06 |
| D-17 | Public repository exposure | OPEN — owner decision | Repository is public. No secrets found in workflows; signing material is in GitHub secrets. Risk: clinical content, licensed instrument text and internal governance documents are publicly readable. Decide: make private, or confirm what may be public and audit the tree for licensed instrument text (ASRS-5, DAST-10, PCL-5, C-SSRS, WHODAS) |
| D-18 | External immutable audit retention | OPEN | Hash chain and append-only triggers exist in the database. No export to immutable external storage is provisioned. Needs a storage account with a time-based retention lock in NZ North: **blocked on Azure subscription and a cost decision** |

### Additional findings

| # | Finding | Severity | Status |
|---|---|---|---|
| A-01 | PR #52 cannot be merged (8 conflicts, incompatible migrations) | High (process) | Documented; porting plan in section 2 |
| A-02 | Prototypes keep assessment data in browser `localStorage` | Medium | Open. Acceptable for synthetic UAT only; must not hold identifiable data |
| A-03 | `android-apk.yml` holds `contents: write` for the whole job, including third-party steps | Medium | Mitigated by D-03 pinning. Further hardening: move release creation to a separate job that receives only the APK artifact |
| A-04 | 51 branches beside `main` | Low | Owner to approve a cleanup list; nothing deleted |
| A-05 | Client-record disposal does not check for unresolved safety escalations | Medium | Open decision D-SAFE-06 |

## 4. Changes in this audit (branch `fix/stage1-audit-remediation`)

| Area | Files |
|---|---|
| Action pinning + CI guard | `.github/workflows/*.yml`, `tools/check_workflow_security.py`, `static-quality.yml` step |
| Hosted-environment database guard | `backend/app/db.py`, `infra/azure/main.bicep`, `backend/tests/test_hosted_environment.py` |
| Safety escalation | `backend/app/safety_escalations.py`, `backend/app/safety_routes.py`, `backend/app/main.py`, `backend/app/migrations/{sqlite,postgres}/004_safety_escalations.sql`, `backend/tests/test_safety_escalations.py`, `backend/openapi.json` |
| CSP | `prototype/*.html` |
| Documentation | this file, `docs/clinical/SAFETY-ESCALATION-MATRIX.md` |

**Test evidence after the changes:** backend **356 passed, 4 skipped** (SQLite + PostgreSQL 16 + Redis, `STN_REQUIRE_PG_TESTS=1`, `STN_REQUIRE_REDIS_TESTS=1`); repo checks pass; workflow check passes; Bicep 0.49.2 build and lint pass; headless Chrome CSP check passes. CI on GitHub has **not** run on this branch yet.

## 5. External dependencies blocking Stage 1 completion

| Dependency | Needed for | Owner | Work that continues without it |
|---|---|---|---|
| Push access for the agent session to this repository | Pushing this branch and opening the PR | Owner | Branch delivered as a git bundle and patch |
| Registered clinical lead | D-SAFE-01 to 06, tier approval, crisis wording | Owner to engage | Engineering of workflows, with placeholders clearly marked |
| Azure subscription (staging) | Restore test, Key Vault rotation, immutable storage (D-13, D-14, D-18) | Owner | Bicep authoring and local tests |
| Entra External ID tenant | Real IdP testing (D-06) | Owner | Token-claim tests with synthetic tokens |
| Decision on repository visibility | D-17 | Owner | None |
| Instrument licences (ASRS-5, DAST-10 and others) | Stage 5 | Owner | Licensing register |

## 6. Next actions (in order)

1. Owner: apply this branch, open the PR, let CI run, review, merge.
2. Owner: decide D-17 (public repository).
3. Port the release-gate engine (G01–G13) from PR #52 onto `main`.
4. Provision immutable audit-export and backup storage in Bicep (D-13, D-18), pending a cost decision.
5. Remove `'unsafe-inline'` from the prototypes' script policy by replacing inline handlers.
6. Clinical lead: decide D-SAFE-01 to 06.
