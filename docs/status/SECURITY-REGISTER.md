# Security register (private: keep the repository private)

Updated 25 Nov 2026. Controls in place, residual risks, and verification. Findings are tracked by id in `DEFECT-REGISTER.md`.

## Controls implemented and tested

| Area | Control | Where | Evidence |
|---|---|---|---|
| Authentication | RS256 OIDC tokens, issuer/audience/exp checked, failures rate-limited per IP | `auth.py` | `test_auth_tokens.py` |
| Authorisation | Roles only from verified claims; organisation required; client role can't combine with staff roles; admin is not clinical authority; verified registration required for clinical routes when enforced | `rbac.py`, `clinician_registry.py` | `test_rbac_mfa.py`, `test_clinician_registry.py`, `test_client_accounts.py` |
| MFA | Required by default (amr/acr/acrs) | `rbac.py` | `test_rbac_mfa.py` |
| Tenant isolation | Every query scoped by organisation; other orgs' records indistinguishable from missing (404) | all modules | `test_org_separation.py` plus per-module cross-org tests |
| IDOR | Client routes take no ids; staff id routes closed to clients | `onboarding_routes.py` | `test_client_accounts.py::test_clients_only_see_their_own_records` |
| Identity events | Signed events, dedicated audience, freshness, replay refusal | `identity_events.py` | `test_identity_events.py` (38) |
| Secrets in transit/at rest | TLS-only PostgreSQL in hosted envs; payload encryption with key ids; Key Vault provider | `db.py`, `crypto.py` | `test_hosted_environment.py`, `test_keys.py` |
| Audit | Hash chain, append-only triggers, advisory lock, verified export, tampered chain never exported | `audit.py`, `audit_export.py` | `test_audit_export.py` |
| Logging | Route templates only; no ids, bodies or tokens; request ids; content-free 500s | `observability.py` | `test_observability.py` |
| Headers | HSTS, nosniff, DENY framing, no-referrer, COOP/CORP, strict API CSP, no-store | `main.py` | `test_security_headers.py` |
| Browser | Prototypes: no inline handlers, script-src by hash. Crisis panel: script-src 'self' | `prototype/`, `frontend/` | headless Chrome runs |
| Supply chain | All actions SHA-pinned; no untrusted interpolation; no pull_request_target; contents: write only in artifact-only jobs | workflows | `check_workflow_security.py` in CI |
| Android signing | Keystore written only after tests; removed always; release job separate and opt-in | `android-apk.yml` | static check (no Flutter here) |
| Notifications | Ids/codes only in parameters; no client identity in templates; memory provider refused in hosted envs | `notifications.py` | `test_notifications.py` |
| Data minimisation | No email or phone stored for clients; invitation codes stored as SHA-256 | `client_accounts.py` | tests |

## Outstanding

| Risk | Severity | Treatment |
|---|---|---|
| Repository is public (code, governance docs) | High | O-1: make private. Website unaffected (checked) |
| Website HTTPS misconfigured | High | O-2: Pages custom domain + Enforce HTTPS |
| No penetration test | High | Gate G08: independent tester before release |
| No live IdP, Key Vault, storage, or restore test | High | Azure + Entra (external dependencies) |
| `style-src 'unsafe-inline'` in prototypes | Low | Move style attributes to classes when the prototypes are replaced |
| Dependency scanning beyond Dependabot (pip-audit, SAST) | Medium | Next session: add pip-audit and Bandit to CI |
| Prototype `localStorage` | Medium | Synthetic UAT only; never identifiable data |
