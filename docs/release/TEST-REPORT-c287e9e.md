# Test report: commit c287e9e (second review response)

**Branch:** `feature/stage1-corrections` (draft PR #52; not merged)
**Command:** `cd backend && python -m pytest -o addopts=""`
**Result:** 172 passed, 0 failed (Python 3.13, pytest 8, FastAPI, cryptography, PyJWT)
**Data:** Synthetic identities, synthetic payloads, synthetic signing keys and throwaway database keys only.

**Important:** These are backend tests. They are not production validation, not clinical validation, and not penetration testing. They do not show that the identity provider, the telephone resources or the crisis pathway work in practice.

## Results by file

| File | Passed | What it covers |
|---|---|---|
| `test_api.py` | 3 | Health and public routes |
| `test_audit_transactions.py` | 11 | Denied read and update durability; missing-record parity; integrity failure recorded; exception after denial; atomicity on audit failure; schema refusal |
| `test_auth_tokens.py` | 9 | RS256 bearer validation |
| `test_clients.py` | 14 | Client record CRUD, owner scoping, fail-closed without key or store |
| `test_migrations_and_export.py` | 8 | Migration discovery and order (0001–0005), idempotence, checksum enforcement, rollback, audit export verification |
| `test_onboarding_controls.py` | 60 | Signed verification events, versioned acknowledgements, separation of duties, platform-record attestations, provisional restriction, fail-closed routes |
| `test_platform_core.py` | 14 | RBAC, audit chain integrity and append-only triggers |
| `test_prototype_csp.py` | 10 | CSP present and restrictive on all three prototype pages; no eval, wildcards or external scripts |
| `test_ratelimit.py` | 7 | Sliding-window behaviour; 429 with Retry-After; limits after authentication; per-address verification limit |
| `test_release_gates.py` | 16 | Gate evaluation; fail when any gate missing or failed; CLI exit codes |
| `test_safety.py` | 20 | Escalation ownership; acknowledgement; resolution with owned documentation; unresolved visibility and overdue flag; append-only rows; audit; public crisis resources |

## Verification performed on the workflow (static, local)

- All six workflow files parse as YAML.
- All 20 `uses:` references are pinned to 40-character commit SHAs.
- No `${{ }}` expression appears inside a `run:` block.
- Input patterns refuse a shell-injection commit string and a path-traversal evidence path (checked with the same regular expressions the workflow uses).
- Gate CLI on the empty evidence file: all 13 gates BLOCKED, exit code 1.

## Not verified in this pass

- The GitHub Actions gate workflow was not dispatched on GitHub. The PR-triggered backend job runs on the draft PR; see the CI status recorded below.
- No live Entra External ID tenant (D-004, D-023).
- No write-once storage (D-009).
- No restore test (D-020, gate G10).
- No penetration test (gate G08).
- No browser test of the prototypes under the CSP. The CSP tests read the HTML; they do not run the page.
- No test of the crisis panel: it is not built.
- No clinical review of the crisis resource list, the overdue threshold or the escalation pathway.
- Telephone numbers were verified against published directories, not by calling services. Two sets of hours remain unresolved (D-035).

## CI status on the draft PR

Recorded from the GitHub REST API at the time of writing. Each check is listed as reported by GitHub for the head commit. Anything not yet complete is shown as such.

