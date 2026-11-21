# Test report: commit 3d6d541

**Branch:** `feature/stage1-corrections`
**Command:** `cd backend && python -m pytest -o addopts=""`
**Result:** 115 passed in 2.12s
**Environment:** Python 3.13.18, FastAPI, PyJWT, cryptography, pytest 8. Synthetic data and throwaway keys only.

## Results by file
- \`test_api.py\`: 3 passed
- \`test_auth_tokens.py\`: 9 passed
- \`test_clients.py\`: 14 passed
- \`test_migrations_and_export.py\`: 8 passed
- \`test_onboarding_controls.py\`: 51 passed
- \`test_platform_core.py\`: 14 passed
- \`test_release_gates.py\`: 16 passed
- **Total passed:** 115; failed: 0

## Not covered by this run (reviewer to note)
- No end-to-end test with a live Entra External ID tenant (D-004).
- No restore test (D-020, gate G10).
- No penetration test (gate G08). No prototype or Flutter test is part of this run.
- Garbage-token tests accept 401 or 503 (D-011).
- The CI workflow `release-gates.yml` was validated as YAML and dry-run locally. It has not been run on GitHub Actions.

## Defects found and fixed during this cycle
See `docs/security/DEFECT-AND-REMEDIATION-REGISTER.md` (D-001 to D-007, D-017).
