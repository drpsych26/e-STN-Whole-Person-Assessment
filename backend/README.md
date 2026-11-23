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
  - Sign-off requires the reviewer to quote the SHA-256 `content_hash` they reviewed. It records reviewer, time and hash.
  - Signed-off records are immutable in the API and in the database (trigger). Corrections are new versions linked by `parent_id`.
- **Safety flags.** Flag codes submitted with an assessment must each be acknowledged by a named clinician or reviewer before review can start. Acknowledgement records who and when. It is not a risk disposition, and nothing is triggered automatically. Flags reset on each resubmission.
- **Consent records.** The owning clinician records each consent (a `scope` code and a `consent_text_ref` naming the version of the consent text) and can record one withdrawal. Rows cannot be deleted or rewritten (database triggers).
- **Retention, legal holds and disposal.** The retention period comes only from `STN_RETENTION_PERIOD_DAYS`; with no valid value, disposal is refused (503). **The period is not set in code and must be confirmed by the organisation's legal adviser** under the Health (Retention of Health Information) Regulations 1996 and any other obligation. Admins place and release legal holds. Disposal is two-person: an admin requests it, and a different admin or reviewer approves it. Approval re-checks that the period has elapsed, no hold is active and no assessment is submitted or in review, then empties every payload (client record, all assessment versions, notes) and the safety-flag codes. Metadata rows stay as tombstones with `disposed_at`; the database rejects any later change. Disposed records return 410.
- **Logged export.** A signed-off assessment can be exported as a JSON document by its author or the reviewer who signed it off, with a `reason_code`. The export log and the audit event record the document's SHA-256 and the reason, never the payload.
- **Rate limiting.** Per-IP request limit on `/v1`, per-subject write limit, and a per-IP limit on rejected tokens (429 with `Retry-After`). The default limiter is in-process; production needs a shared store or gateway limits (see `app/ratelimit.py`).
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
| `POST /v1/assessments/{id}/start-review` | reviewer (not author) | Take the review |
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
| `GET /v1/audit`, `GET /v1/audit/verify` | admin | Audit metadata (own organisation) and whole-chain verification |

Status codes: 401 for an invalid token; 403 for a missing role, organisation or MFA, self-review, or same-person disposal approval; 404 for a missing, not-visible or other-organisation record (same response, so ids cannot be enumerated); 409 for a workflow conflict, stale revision or a disposal that is not eligible; 410 for a disposed record; 422 for invalid input; 429 when a rate limit is reached; 503 when storage, the data keys, the retention policy or the identity provider is not configured.

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
| `STN_KEYVAULT_URL`, `STN_KEYVAULT_KEY_IDS` | Key Vault provider: vault URL and secret names (each name is the key id). Needs `azure-identity` and `azure-keyvault-secrets`, which are not dependencies yet; without them the provider fails closed |
| `STN_RETENTION_PERIOD_DAYS` | Minimum retention period before disposal. Unset or invalid means disposal is refused. Set only the value confirmed by legal advice |
| `STN_RATE_LIMIT_IP_PER_MINUTE`, `STN_RATE_LIMIT_WRITES_PER_MINUTE`, `STN_RATE_LIMIT_AUTH_FAILURES_PER_MINUTE` | Limits (defaults 600, 120, 20). `STN_RATE_LIMIT_ENABLED=false` disables them for local debugging only |
| `STN_TRUST_FORWARDED_FOR` | Use the first `X-Forwarded-For` address as the client IP. Enable only behind a proxy that overwrites that header |

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

CI runs both passes. The PostgreSQL job fails rather than skips if the database is unavailable, and then runs the backup/restore drill below.

## Key rotation

1. Generate a new key and add it to the keyring next to the current one (`STN_DATA_KEYS`, or a new Key Vault secret listed in `STN_KEYVAULT_KEY_IDS`).
2. Set `STN_DATA_ACTIVE_KEY_ID` to the new id and restart. New writes use it; existing records still decrypt with their own key.
3. Move stored records: `POST /v1/admin/keys/re-encrypt` per organisation, or `python -m app.rekey` as the platform operator, until `remaining` is 0. Records that fail verification are skipped and audited, never rewritten. `GET /v1/admin/keys/status` (or `python -m app.rekey --status-only`) shows key ids in use; key material is never returned.
4. Only then remove the old key from the keyring.

## Backup and restore drill

`scripts/backup_restore_drill.sh` dumps the database named by `STN_DATABASE_URL`, restores it into a scratch database, compares row counts for every table, recomputes the audit chain on the restored copy and, when a data key is configured, decrypts every record (`python -m app.rekey --verify-decrypt`). CI seeds synthetic data (`scripts/seed_synthetic_data.py --reset`, which refuses to run without `STN_ALLOW_SCHEMA_RESET=1`) and runs the drill on every change. The production procedure is in `docs/operations/BACKUP-AND-RESTORE-RUNBOOK.md`.

## Not in this increment (required before any real client data)

- Reviewer assignment rules, account lifecycle and access review; an operator procedure for moving pre-v2 rows out of organisation `unassigned`.
- Connection pooling, a shared rate-limit store or gateway limits, idempotency keys and a correlation-id policy.
- A live Key Vault integration test (managed identity, secret permissions, rotation in a staging subscription) and a decision on per-record envelope keys; point-in-time recovery and disaster-recovery exercises in Azure.
- An approved clinical field schema; the legally confirmed retention period and anchor; the approved consent text and its versions; client access and correction workflows.
- The clinical safety SOP: who acknowledges flags, coverage hours, timeouts, escalation and incident recording, all approved by clinical governance.
- Privacy impact assessment, threat model, independent penetration test, and production go-live approval.
