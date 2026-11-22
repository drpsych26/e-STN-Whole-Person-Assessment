# STN API — clinician sign-in, review workflow and audit (non-live)

**Status: engineering increment, synthetic data only.** This API is not deployed, is not connected to a production identity provider or database, and is **not approved for clinical use or real client data**. Passing tests are software evidence only. They are not clinical validation, a privacy assessment, a security test or production approval. See `docs/release/PRODUCTION-GO-LIVE-GATE.md`.

## What is implemented

- **Clinician sign-in (OIDC).** RS256 bearer tokens verified for signature, issuer, audience, expiry and subject. Fail closed: protected routes return 503 until `STN_OIDC_ISSUER`, `STN_OIDC_AUDIENCE` and `STN_OIDC_JWKS_URL` are set.
- **Server-side roles.** `clinician`, `reviewer` (supervising clinician) and `admin`, taken only from verified token claims. No role means 403. Admins get audit metadata only, with no access to clinical payloads.
- **MFA enforcement.** On by default. Role-protected routes accept a token only if its `amr`, `acr` or `acrs` claim shows a configured strong-authentication value.
- **Encrypted records.** Client and assessment payloads are stored as AES-256-GCM ciphertext bound to the record id and author, so copied or swapped ciphertext fails verification. Payloads are generic JSON. This increment adds no clinical questions, scales, scoring, routing, diagnosis or risk logic.
- **Human review workflow.** `draft → submitted → in_review → returned | signed_off`, plus `returned → draft` (reopen). No other transitions exist.
  - Only the author edits, submits and reopens, and edits must quote the current `revision`.
  - Only a reviewer who is not the author can start review. Only that reviewer can return the work (a reason is required and stored encrypted) or sign it off.
  - Sign-off requires the reviewer to quote the SHA-256 `content_hash` they reviewed. It records reviewer, time and hash.
  - Signed-off records are immutable in the API and in the database (trigger). Corrections are new versions linked by `parent_id`.
- **Safety flags.** Flag codes submitted with an assessment must each be acknowledged by a named clinician or reviewer before review can start. Acknowledgement records who and when. It is not a risk disposition, and nothing is triggered automatically. Flags reset on each resubmission.
- **Audit.** Hash-chained, append-only events (database triggers block UPDATE/DELETE) for create, read, edit, list, submit, flag raise and acknowledge, review start, return, sign-off, amend and every denial. Events hold no payloads or notes. Admins can list events and verify the chain.
- **Storage.** PostgreSQL via `STN_DATABASE_URL` (production target: Azure Database for PostgreSQL, New Zealand North), or SQLite via `STN_DATA_DB` for tests and local synthetic runs. The schema is applied from versioned files in `app/migrations/`. Without a configured store, storage is unavailable (503), and a PostgreSQL URL without its driver also fails closed.

## Endpoints (`/v1`)

| Method and path | Role | Purpose |
|---|---|---|
| `GET /health/live` | none | Liveness |
| `GET /v1/me` | any verified token | Token subject |
| `GET /v1/me/access` | any verified token | Effective roles and MFA status |
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
| `GET /v1/audit`, `GET /v1/audit/verify` | admin | Audit metadata and chain verification |

Status codes: 401 for an invalid token; 403 for a missing role, missing MFA or self-review; 404 for a missing or not-visible record (same response, so ids cannot be enumerated); 409 for a workflow conflict or stale revision; 422 for invalid input; 503 when storage or the identity provider is not configured.

The generated OpenAPI document is `openapi.json`. Regenerate it after route changes with `python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json`.

## Configuration

| Variable | Purpose |
|---|---|
| `STN_OIDC_ISSUER`, `STN_OIDC_AUDIENCE`, `STN_OIDC_JWKS_URL` | Identity provider (for example a Microsoft Entra ID app registration) |
| `STN_OIDC_ROLES_CLAIM` | Claim holding roles (default `roles`) |
| `STN_OIDC_ROLE_MAP` | Provider-to-STN role map, e.g. `STN.Clinician=clinician,STN.Reviewer=reviewer,STN.Admin=admin` |
| `STN_REQUIRE_MFA` | Default on. Only `false`, `0`, `no` or `off` disable it, and that is for non-production use only |
| `STN_MFA_AMR_VALUES`, `STN_MFA_ACR_VALUES`, `STN_MFA_ACRS_VALUES` | Accepted MFA evidence (default `amr` contains `mfa`). On Entra ID, require MFA through Conditional Access and map an authentication context to `acrs` |
| `STN_DATABASE_URL` | PostgreSQL URL (takes precedence) |
| `STN_DATA_DB` | SQLite path for tests and local runs |
| `STN_DATA_KEY` | urlsafe-base64 of 32 random bytes. Generate it with `python -c "import base64,secrets;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`, keep it in a secrets manager (Azure Key Vault in production), and never commit it |

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

CI runs both passes. The PostgreSQL job fails rather than skips if the database is unavailable.

## Not in this increment (required before any real client data)

- Organisation and multi-tenant isolation, reviewer assignment rules, account lifecycle and access review.
- Connection pooling, rate limiting, idempotency keys and a correlation-id policy.
- Key rotation and envelope encryption through Key Vault, plus backup, restore and disaster-recovery drills.
- An approved clinical field schema, retention and disposal rules, consent records, and access/correction workflows.
- The clinical safety SOP: who acknowledges flags, coverage hours, timeouts, escalation and incident recording, all approved by clinical governance.
- Privacy impact assessment, threat model, independent penetration test, and production go-live approval.
