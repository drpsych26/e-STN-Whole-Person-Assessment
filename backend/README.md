# STN API — clinician sign-in, review workflow and audit (non-live)

**Status: engineering increment, synthetic data only.** This API is not deployed, is not connected to a production identity provider or database, and is **not approved for clinical use or real client data**. Passing tests are software evidence only. They are not clinical validation, a privacy assessment, a security test or production approval. See `docs/release/PRODUCTION-GO-LIVE-GATE.md`.

## What is implemented

- **Clinician sign-in (OIDC).** RS256 bearer tokens verified for signature, issuer, audience, expiry and subject. Fail closed: protected routes return 503 until `STN_OIDC_ISSUER`, `STN_OIDC_AUDIENCE` and `STN_OIDC_JWKS_URL` are set.
- **Server-side roles.** `clinician`, `reviewer` (supervising clinician) and `admin`, taken only from verified token claims. No role means 403. Admins get audit and governance metadata only, with no access to clinical payloads.
- **Organisation separation.** Every role-protected route needs an organisation id from a token claim (`STN_OIDC_ORG_CLAIM`, default `stn_org`; use `tid` for one organisation per Entra tenant). No valid organisation means 403. Client records, assessments, consents, legal holds, disposals, exports and audit events are all stored with their organisation, and every query is scoped to it. Another organisation's record behaves exactly like a missing one (404) and the attempt is audited in the caller's organisation.
- **MFA enforcement.** On by default. Role-protected routes accept a token only if its `amr`, `acr` or `acrs` claim shows a configured strong-authentication value.
- **Encrypted records with key rotation.** Client and assessment payloads are stored as AES-256-GCM ciphertext bound to the record id and author, so copied or swapped ciphertext fails verification. Each ciphertext carries the id of the key that encrypted it (authenticated header); new writes use the active key and reads use whichever key the record names. Reads of submitted, in-review, returned and signed-off assessments re-check the recorded content hash, so an older ciphertext replayed into a row is detected. Keys come from a `KeyProvider`: environment variables, or an Azure Key Vault provider that fails closed unless configured (see "Key rotation"). Payloads are generic JSON. No clinical questions, scales, scoring, routing, diagnosis or risk logic are added.
- **Human review workflow.** `draft → submitted → in_review → returned | signed_off`, plus `returned → draft` (reopen). No other transitions exist.
  - Only the author edits, submits and reopens, and edits must quote the current `revision`.
  - Only a reviewer who is not the author can start review. Only that reviewer can return the work (a reason is required and stored encrypted) or sign it off.
  - **Reviewer assignment** (required by default, `STN_REVIEW_ASSIGNMENT_REQUIRED`). An admin assigns a named reviewer to each submission, and only that reviewer can start its review. Self-assignment, assigning the author and assigning an account that is not active in the organisation are refused. Reassignment ends the earlier assignment (kept as history). Resubmission and deactivating the reviewer end assignments. Admins see a reassignment queue of unassigned and stale submissions (`STN_REVIEW_ASSIGNMENT_STALE_HOURS`, default 48). Setting the variable to `false` allows an open review pool for unassigned work; an assignment, once made, is still enforced.
  - Sign-off requires the reviewer to quote the SHA-256 `content_hash` they reviewed. It records reviewer, time and hash.
  - Signed-off records are immutable in the API and in the database (trigger). Corrections are new versions linked by `parent_id`.
- **Safety flags.** Flag codes submitted with an assessment must each be acknowledged by a named clinician or reviewer before review can start. Acknowledgement records who and when. It is not a risk disposition, and nothing is triggered automatically. Flags reset on each resubmission.
- **Consent records.** The owning clinician records each consent (a `scope` code and a `consent_text_ref` naming the version of the consent text) and can record one withdrawal. Rows cannot be deleted or rewritten (database triggers).
- **Retention, legal holds and disposal.** The retention period comes only from `STN_RETENTION_PERIOD_DAYS`; with no valid value, disposal is refused (503). **The period is not set in code and must be confirmed by the organisation's legal adviser** under the Health (Retention of Health Information) Regulations 1996 and any other obligation. Admins place and release legal holds. Disposal is two-person: an admin requests it, and a different admin or reviewer approves it. Approval re-checks that the period has elapsed, no hold is active and no assessment is submitted or in review, then empties every payload (client record, all assessment versions, notes) and the safety-flag codes. Metadata rows stay as tombstones with `disposed_at`; the database rejects any later change. Disposed records return 410.
- **Logged export.** A signed-off assessment can be exported as a JSON document by its author or the reviewer who signed it off, with a `reason_code`. The export log and the audit event record the document's SHA-256 and the reason, never the payload.
- **Clinician account registry.** Tokens stay the source of identity and roles; the registry adds each organisation's status for a subject: `invited → active → suspended → deactivated`. Admins invite, activate, suspend (reason required), reinstate and deactivate (reason required); an admin cannot change their own account. Reactivating a deactivated account needs a request by one admin and approval by a different admin. Every role-protected request checks the registry after the role, MFA and organisation checks: invited, suspended and deactivated subjects are refused (403, audited) even with a valid token. With `STN_ACCOUNT_REGISTRY_REQUIRED=true` (recommended for production), unregistered subjects are refused too; bootstrap the first admin with `python -m app.accounts register --org <org> --subject <sub> --activate`. The access-review report lists each registered subject's status, the roles they last presented, last activity and pending reactivations, and flags active accounts unused for `STN_ACCESS_REVIEW_STALE_DAYS` (default 90).
- **Client access and correction requests** (Privacy Act 2020, information privacy principles 6 and 7). An admin logs a request against a client with the date received; the due date is the configured number of working days after receipt (`STN_PRIVACY_RESPONSE_WORKING_DAYS`, with weekends, `STN_PRIVACY_NON_WORKING_DATES` and optionally 25 December–15 January skipped). **No period is set in code; the privacy officer must confirm the period and working-day rules against the Act**, and without them requests are logged with no due date. The client's owning clinician prepares the response: an access-response export (client record, signed-off assessments, unfinalised versions listed without content, and any statements of correction), logged in the export log and audit by its SHA-256; or a correction, either a new assessment version through the amendment workflow, an update to the client record, or, when declined, the client's statement of correction, stored encrypted and attached to the client. Admins close requests (`completed` needs a recorded response; also `refused`, `transferred`, `withdrawn`) and see metadata only, with overdue flags. Closed requests are final. Disposal and key rotation cover statements of correction.
- **Rate limiting.** Per-IP request limit on `/v1`, per-subject write limit, and a per-IP limit on rejected tokens (429 with `Retry-After`). The store is in-process by default (single instance) or Redis (`STN_RATE_LIMIT_BACKEND=redis`, `STN_REDIS_URL`), shared by every instance, with window arithmetic on Redis server time in one atomic script. A misconfigured store stops the API from starting, and an unreachable Redis gives 503, never an unlimited pass.
- **Audit.** Hash-chained, append-only events (database triggers block UPDATE/DELETE) for create, read, edit, list, submit, flag raise and acknowledge, review start, return, sign-off, amend, export, consent, hold, disposal, re-encryption and every denial. Events carry the organisation and, for exports, the document hash; they hold no payloads or notes. Admins list their organisation's events; chain verification covers the whole platform.
- **Storage.** PostgreSQL via `STN_DATABASE_URL` (production target: Azure Database for PostgreSQL, New Zealand North), or SQLite via `STN_DATA_DB` for tests and local synthetic runs. The schema is applied from versioned files in `app/migrations/`. Without a configured store, storage is unavailable (503), and a PostgreSQL URL without its driver also fails closed.

## Endpoints (`/v1`)

| Method and path | Role | Purpose |
|---|---|---|
| `GET /health/live` | none | Liveness |
| `GET /v1/me` | any verified token | Token subject |
| `GET /v1/me/access` | any verified token | Effective roles, organisation and MFA status |
| `POST /v1/clients`, `GET/PUT /v1/clients/{id}` | clinician | Owner-scoped encrypted client record |
| `GET /v1/clients/{id}/assessments` | clinician (owner) | Assessment versions for a client (metadata) |
| `POST /v1/assessments` | clinician (client owner) | Create a draft (`client_id`, `form_id`, `form_version`, `payload`) |
| `GET /v1/assessments/{id}` | author, or the assigned reviewer | Read payload, note and current safety flags |
| `PUT /v1/assessments/{id}` | author | Edit a draft (`payload`, `revision`) |
| `POST /v1/assessments/{id}/submit` | author | Submit (`safety_flags`: list of codes) |
| `GET /v1/assessments/{id}/safety-flags` | author or reviewer | Flag metadata |
| `POST /v1/assessments/{id}/safety-flags/{flag_id}/acknowledge` | author or reviewer | Human acknowledgement |
| `GET /v1/review-queue` | reviewer | Submitted work by others plus held reviews (metadata only) |
| `POST /v1/assessments/{id}/start-review` | the assigned reviewer (not author) | Take the review |
| `POST /v1/assessments/{id}/return` | assigned reviewer | Return with `reason` |
| `POST /v1/assessments/{id}/sign-off` | assigned reviewer (not author) | Sign off with `content_hash` |
| `POST /v1/assessments/{id}/reopen` | author | Returned → draft |
| `POST /v1/assessments/{id}/amendments` | author | New version of a signed-off record (`payload`, `reason`) |
| `POST /v1/assessments/{id}/export` | author, or the signing reviewer | Export a signed-off record (`reason_code`); returns the document and `export_hash` |
| `POST/GET /v1/clients/{id}/consents` | clinician (owner) | Record (`scope`, `consent_text_ref`) or list consents |
| `POST /v1/clients/{id}/consents/{consent_id}/withdraw` | clinician (owner) | Record a withdrawal (once) |
| `GET /v1/admin/retention/policy`, `GET /v1/admin/retention/due` | admin | Configured period; clients now eligible (metadata) |
| `POST/GET /v1/admin/legal-holds`, `POST /v1/admin/legal-holds/{id}/release` | admin | Place (`client_id`, `reason_code`), list, release |
| `POST/GET /v1/admin/disposals` | admin | Request (`client_id`, `reason_code`) or list disposals |
| `POST /v1/admin/disposals/{id}/approve` | admin or reviewer, not the requester | Second-person approval; executes the disposal |
| `POST /v1/admin/disposals/{id}/cancel` | admin | Cancel a pending request |
| `GET /v1/admin/keys/status`, `POST /v1/admin/keys/re-encrypt` | admin | Key ids in use; move records to the active key |
| `POST /v1/admin/assessments/{id}/reviewer` | admin | Assign or reassign the reviewer (`reviewer_sub`) |
| `GET /v1/admin/assessments/{id}/reviewer-history`, `GET /v1/admin/review-assignments` | admin | Assignment history; reassignment queue (`older_than_hours`) |
| `POST/GET /v1/admin/accounts` | admin | Invite (`subject`, optional `reason_code`) or list (`status`) registered subjects |
| `POST /v1/admin/accounts/{subject}/activate`, `/suspend`, `/deactivate` | admin (not on their own account) | Status changes; suspend and deactivate need `reason_code` |
| `GET /v1/admin/accounts/{subject}/history` | admin | Status history |
| `POST /v1/admin/accounts/{subject}/reactivation-requests` | admin | Request reactivation of a deactivated account (`reason_code`) |
| `POST /v1/admin/account-reactivations/{id}/approve`, `/cancel` | admin; approval by a different admin | Two-person reactivation |
| `GET /v1/admin/access-review` | admin | Access-review report (`inactive_after_days`) |
| `GET /v1/admin/privacy-requests/policy` | admin | Configured response period and working-day rules |
| `POST/GET /v1/admin/privacy-requests`, `POST /v1/admin/privacy-requests/{id}/close` | admin | Log (`client_id`, `kind`, `received_on`), list (`state`), close (`outcome_code`) |
| `POST /v1/privacy-requests/{id}/access-response` | clinician (client owner) | Access-response export; returns the document and `export_hash` |
| `POST /v1/privacy-requests/{id}/correction-response` | clinician (client owner) | `action`: `amended` (+ `assessment_id`), `client_record_corrected`, or `declined` (+ `statement`) |
| `GET /v1/clients/{id}/privacy-requests`, `GET /v1/clients/{id}/correction-statements` | clinician (owner) | Requests for a client; attached statements of correction |
| `GET /v1/audit`, `GET /v1/audit/verify` | admin | Audit metadata (own organisation) and whole-chain verification |

Status codes: 401 for an invalid token; 403 for a missing role, organisation or MFA, an account that is not active in the organisation, self-review, self-assignment, a review assigned to someone else, a change to one's own account, or same-person disposal or reactivation approval; 404 for a missing, not-visible or other-organisation record (same response, so ids cannot be enumerated); 409 for a workflow conflict, stale revision, a disposal that is not eligible, an unassigned review when assignment is required, or an inactive reviewer; 410 for a disposed record; 422 for invalid input; 429 when a rate limit is reached; 503 when storage, the data keys, the retention policy, the identity provider, a required account registry or the shared rate-limit store is not available.

The generated OpenAPI document is `openapi.json`. Regenerate it after route changes with `python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json`.

## Configuration

| Variable | Purpose |
|---|---|
| `STN_OIDC_ISSUER`, `STN_OIDC_AUDIENCE`, `STN_OIDC_JWKS_URL` | Identity provider (for example a Microsoft Entra ID app registration) |
| `STN_OIDC_ROLES_CLAIM` | Claim holding roles (default `roles`) |
| `STN_OIDC_ORG_CLAIM` | Claim holding the organisation id (default `stn_org`; `tid` for one organisation per Entra tenant). Values: 1-128 letters, digits, `_ . : -` |
| `STN_OIDC_ROLE_MAP` | Provider-to-STN role map, e.g. `STN.Clinician=clinician,STN.Reviewer=reviewer,STN.Admin=admin` |
| `STN_REQUIRE_MFA` | Default on. Only `false`, `0`, `no` or `off` disable it, and that is for non-production use only |
| `STN_MFA_AMR_VALUES`, `STN_MFA_ACR_VALUES`, `STN_MFA_ACRS_VALUES` | Accepted MFA evidence (default `amr` contains `mfa`). On Entra ID, require MFA through Conditional Access and map an authentication context to `acrs` |
| `STN_DATABASE_URL` | PostgreSQL URL (takes precedence) |
| `STN_DATA_DB` | SQLite path for tests and local runs |
| `STN_KEY_PROVIDER` | `env` (default) or `azure-keyvault` |
| `STN_DATA_KEYS`, `STN_DATA_ACTIVE_KEY_ID` | Keyring for the `env` provider: `<key-id>:<urlsafe-base64 32 bytes>,...` and the id used for new writes |
| `STN_DATA_KEY` | Single-key setting, still accepted as key id `legacy` (active when it is the only key). Generate keys with `python -c "import base64,secrets;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`, keep them in a secrets manager, and never commit them |
| `STN_KEYVAULT_URL`, `STN_KEYVAULT_KEY_IDS` | Key Vault provider: vault URL and secret names (each name is the key id). Needs the `azure` pip extra (`azure-identity`, `azure-keyvault-secrets`; included in the container image); without it the provider fails closed. Uses the managed identity named by `AZURE_CLIENT_ID` |
| `STN_RETENTION_PERIOD_DAYS` | Minimum retention period before disposal. Unset or invalid means disposal is refused. Set only the value confirmed by legal advice |
| `STN_RATE_LIMIT_IP_PER_MINUTE`, `STN_RATE_LIMIT_WRITES_PER_MINUTE`, `STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE` | Limits (defaults 600, 120, 20). `STN_RATE_LIMIT_ENABLED=false` disables them for local debugging only |
| `STN_TRUST_FORWARDED_FOR` | Use the first `X-Forwarded-For` address as the client IP. Enable only behind a proxy that overwrites that header |
| `STN_RATE_LIMIT_BACKEND`, `STN_REDIS_URL`, `STN_REDIS_KEY_PREFIX` | `memory` (default, single instance) or `redis` (shared; needs the URL, `rediss://` for TLS, and the `redis` pip extra). Prefix default `stn:rl:` |
| `STN_REVIEW_ASSIGNMENT_REQUIRED` | Default on. `false` allows any non-author reviewer to take unassigned work (open pool) |
| `STN_REVIEW_ASSIGNMENT_STALE_HOURS` | Age after which an assignment whose review has not started appears in the reassignment queue (default 48) |
| `STN_ACCOUNT_REGISTRY_REQUIRED` | `true` refuses subjects not registered in the organisation (recommended for production). Default `false`: unregistered subjects act on their token roles; registered subjects must be active |
| `STN_ACCESS_REVIEW_STALE_DAYS` | Active accounts unused for this many days are flagged in the access review (default 90) |
| `STN_PRIVACY_RESPONSE_WORKING_DAYS` | Working days after receipt for the due date of access and correction requests. Unset means no due dates. Set only the value the privacy officer has confirmed |
| `STN_PRIVACY_NON_WORKING_DATES`, `STN_PRIVACY_EXCLUDE_SUMMER_PERIOD` | Comma-separated `YYYY-MM-DD` dates (public holidays) that do not count; `true` also skips 25 December to 15 January. Both need the privacy officer's confirmation |
| `STN_DATABASE_AUTH` | `password` (default: credentials in the URL, or none) or `azure-managed-identity` (a Microsoft Entra token for the managed identity named by `AZURE_CLIENT_ID` is used as the PostgreSQL password; needs the `azure` extra; fails closed with 503 if no token is available) |
| `STN_DATABASE_AUTO_MIGRATE` | Default on (migrations are applied on first use). Set `false` in deployed API instances: migrations then run only in the separate migration step, and the API reports not ready until the schema matches its build |
| `STN_BUILD_ID` | Build identifier shown by `/healthz` and `/readyz` (the image sets it to the commit). Only `[A-Za-z0-9._-]{1,64}` is shown; anything else reads `unknown` |
| `STN_READINESS_CACHE_SECONDS` | How long a `/readyz` result is reused (default 5; 0 disables) |
| `STN_PROCESS_ROLE` | Container only: `api` (default) or `migrate` (see "Container image") |
| `STN_DB_RUNTIME_ROLE`, `STN_DB_CREATE_ENTRA_PRINCIPAL` | Migration step only: the API's database role to grant data privileges to, and whether to create it first as a Microsoft Entra principal |
| `STN_BOOTSTRAP_ADMIN_ORG`, `STN_BOOTSTRAP_ADMIN_SUBJECT` | Migration step only: register and activate this subject in the account registry if it has never been registered (an existing account is never changed) |

## Local synthetic-only run

```sh
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e '.[test,postgres]'
pytest                                   # SQLite pass; PostgreSQL cases skip
docker compose up -d postgres            # optional local PostgreSQL
STN_TEST_DATABASE_URL=postgresql://stn_local:stn_local_only@127.0.0.1:5432/stn_local \
  STN_REQUIRE_PG_TESTS=1 pytest          # both passes (wipes that database)
```

Redis tests (the shared rate-limit store) run when `STN_TEST_REDIS_URL` is set, for example against `docker compose up -d redis` with `STN_TEST_REDIS_URL=redis://127.0.0.1:6379/1`. To run the whole suite on the Redis store, also set `STN_RATE_LIMIT_BACKEND=redis` and `STN_REDIS_URL`.

CI runs three passes: SQLite, PostgreSQL (fails rather than skips if the database is unavailable, then runs the backup/restore drill below), and SQLite with the Redis rate-limit store (fails rather than skips if Redis is unavailable).

## Health, readiness and the migration step

- `GET /healthz` (liveness): `{"status": "alive", "build": "<id>"}`. No dependencies, no authentication. `GET /health/live` remains for older probes.
- `GET /readyz` (readiness): 200 `{"status": "ready", "build": "<id>"}` only when the database schema exactly matches this build, the active data key is available and the shared rate-limit store answers (when enabled); otherwise 503 `{"status": "not_ready", "build": "<id>"}`. It never says which check failed; the server log records the check name and exception class only.
- `python -m app.migrate` applies migrations as a separate step (idempotent, advisory-locked on PostgreSQL), prints the schema version, and can create the API's Entra database principal, grant it data privileges only (no CREATE, ALTER or ownership) and bootstrap the first registry account. `--status` reports without changing anything. Exit 0 success, 1 failure, 2 configuration error.

## Container image

`backend/Dockerfile` builds a two-stage image from a digest-pinned `python:3.12-slim-bookworm`, installs `requirements.lock` (hash-pinned, generated with `uv pip compile --extra postgres --extra redis --extra azure --generate-hashes`) with `--require-hashes`, and runs as user 10001 with the application read-only, so it also runs with a read-only root filesystem (`--read-only --tmpfs /tmp`). No secrets are baked in; configuration comes from the environment. `STN_PROCESS_ROLE=api` serves the API; `STN_PROCESS_ROLE=migrate` runs `python -m app.migrate` and, if it succeeds, serves only `/healthz` and `/readyz` (`app.migrate_server`). CI builds the image, runs both roles against PostgreSQL 16 with a least-privilege runtime role, checks the probes, the non-root user and the read-only application, and scans the image with Trivy (fails on fixable HIGH or CRITICAL findings).

```sh
cd backend
docker build --build-arg STN_BUILD_ID=local -t stn-api:local .
docker run --rm --read-only --tmpfs /tmp -p 8000:8000 -e STN_DATA_DB=/tmp/stn.sqlite3 stn-api:local
```

Deployment to Azure (Bicep templates in `infra/azure/`, manual staging workflow): `docs/operations/DEPLOYMENT-RUNBOOK.md`.

## Key rotation

1. Generate a new key and add it to the keyring next to the current one (`STN_DATA_KEYS`, or a new Key Vault secret listed in `STN_KEYVAULT_KEY_IDS`).
2. Set `STN_DATA_ACTIVE_KEY_ID` to the new id and restart. New writes use it; existing records still decrypt with their own key.
3. Move stored records: `POST /v1/admin/keys/re-encrypt` per organisation, or `python -m app.rekey` as the platform operator, until `remaining` is 0. Records that fail verification are skipped and audited, never rewritten. `GET /v1/admin/keys/status` (or `python -m app.rekey --status-only`) shows key ids in use; key material is never returned.
4. Only then remove the old key from the keyring.

## Backup and restore drill

`scripts/backup_restore_drill.sh` dumps the database named by `STN_DATABASE_URL`, restores it into a scratch database, compares row counts for every table, recomputes the audit chain on the restored copy and, when a data key is configured, decrypts every record (`python -m app.rekey --verify-decrypt`). Client tools must match the server's major version; the script checks this and stops on a mismatch. Set `STN_PG_CLIENT_IMAGE=postgres:16` to run them from the server image (CI does this), or `STN_PG_BIN` to a local install. CI seeds synthetic data (`scripts/seed_synthetic_data.py --reset`, which refuses to run without `STN_ALLOW_SCHEMA_RESET=1`) and runs the drill on every change. The production procedure is in `docs/operations/BACKUP-AND-RESTORE-RUNBOOK.md`.

## Not in this increment (required before any real client data)

- An operator procedure for moving pre-v2 rows out of organisation `unassigned`; joiner/mover/leaver procedures that keep the account registry and the identity provider's role assignments in step.
- Connection pooling, idempotency keys and a correlation-id policy. Azure Managed Redis (private endpoint, TLS) is defined in `infra/azure/` but not provisioned.
- A live Key Vault integration test (managed identity, secret permissions, rotation in the staging subscription) and a decision on per-record envelope keys; point-in-time recovery and disaster-recovery exercises in Azure. The deploy kit defines these resources; none has been deployed.
- An approved clinical field schema; the legally confirmed retention period and anchor; the approved consent text and its versions; the privacy officer's confirmed response period, working-day rules and access-request procedure (identity checks, withholding grounds, secure release to the client, transfers).
- The clinical safety SOP: who acknowledges flags, coverage hours, timeouts, escalation and incident recording, all approved by clinical governance.
- Privacy impact assessment, threat model, independent penetration test, and production go-live approval.
