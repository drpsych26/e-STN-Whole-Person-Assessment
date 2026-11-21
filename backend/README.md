# STN API foundation — non-live

This is an engineering foundation only. It is not connected to the website or Flutter app and is not approved for clinical use or real client data.

## Included

- FastAPI service with a liveness endpoint.
- Protected `GET /v1/me` route using OIDC JWT verification.
- Fail-closed configuration: protected routes return unavailable until issuer, audience and JWKS URL are configured.
- RS256 signature, issuer, audience, expiry and subject validation.
- Encrypted client-record store (AES-256-GCM, owner-scoped, audit log without payloads):
  - `POST /v1/clients`, `GET /v1/clients/{id}`, `PUT /v1/clients/{id}`, all requiring a verified token.
  - Records are visible only to the clinician who created them; other callers get 404.
  - Fails closed (503) when `STN_DATA_DB` or `STN_DATA_KEY` is missing or malformed.
  - Ciphertext is bound to its record id and owner, so copy or swap attempts fail verification.
- No assessment, scoring, decision-support or crisis endpoints yet.

## Client-data configuration

- `STN_DATA_DB`: path to the SQLite file. In any deployed environment this must be on encrypted storage or replaced by an approved managed database.
- `STN_DATA_KEY`: urlsafe-base64 of 32 random bytes. Generate with `python -c "import base64,secrets;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`. Store it in a secrets manager, never in the repository.

## Not yet approved

The payload schema is generic. Real client data must not be entered until the clinical field definitions, retention rules, NZ Health Information Privacy Code 2020 and Privacy Act 2020 review, and penetration test are complete.

## Local synthetic-only run

From this directory:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Liveness: `GET /health/live`.

Protected identity: `GET /v1/me` requires an access token from an approved test OIDC tenant and these environment variables:

- `STN_OIDC_ISSUER`
- `STN_OIDC_AUDIENCE`
- `STN_OIDC_JWKS_URL`

Do not put tokens or secrets in source control, chat, test fixtures or logs. Do not configure production identity or real-client data until hosting, data processing, privacy, security and clinical governance approvals are complete.

## Deliberate omissions

No database, client records, assessment storage, role claims, organisation scoping, consent workflow, audit persistence, clinical scoring, crisis escalation or public intake. The identity response proves token validation only; it does not establish clinician authorisation. A subsequent increment must implement server-side RBAC and record scoping before any record route is added.
