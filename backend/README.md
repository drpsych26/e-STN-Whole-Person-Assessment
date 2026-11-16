# STN API foundation — non-live

This is an engineering skeleton only. It is not connected to the website or Flutter app, has no database, and is not approved for clinical use.

## Included

- FastAPI service with a liveness endpoint.
- Protected `GET /v1/me` route using OIDC JWT verification.
- Fail-closed configuration: protected routes return unavailable until issuer, audience and JWKS URL are configured.
- RS256 signature, issuer, audience, expiry and subject validation.
- No client-record or assessment endpoints.

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
