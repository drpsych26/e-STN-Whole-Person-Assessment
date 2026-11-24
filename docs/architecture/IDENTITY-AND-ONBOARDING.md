# Identity, onboarding and attestation

**Status (25 Nov 2026): IMPLEMENTED and tested with synthetic keys only.** No live identity-provider integration has been performed. Nothing here is approved for clinical use.

Code: `backend/app/identity_events.py`, `client_accounts.py`, `clinician_registry.py`, `onboarding_routes.py`, `rbac.py`; schema `migrations/*/005_identity_onboarding.sql`; tests `test_identity_events.py` (38), `test_client_accounts.py` (18), `test_clinician_registry.py` (14), each run on SQLite and PostgreSQL 16.

## 1. Roles

| Role | Who | Notes |
|---|---|---|
| `clinician` | Treating clinicians | Clinical routes need a **verified registration** when enforcement is on |
| `reviewer` | Clinical reviewers | Same registration rule |
| `admin` | Operations | No clinical authority: cannot activate clients, open escalations or read clinical content |
| `client` | Clients | Can't be combined with any staff role in one token (403). Never reaches staff routes |

Roles come only from the verified token (`STN_OIDC_ROLE_MAP`). Nothing a browser or app sends can grant a role.

## 2. Identity-provider verification events (D-07)

`POST /v1/identity/events` with body `{"event": "<JWT>"}`. Authenticated only by the signature. Accepted only if every check passes:

| Check | Rule |
|---|---|
| Signature | RS256 against `STN_IDP_EVENT_JWKS_URL` (default `STN_OIDC_JWKS_URL`). `none` and HS256 refused |
| Issuer | `STN_IDP_EVENT_ISSUER` (default `STN_OIDC_ISSUER`) |
| Audience | `STN_IDP_EVENT_AUDIENCE`, which **must differ** from the API audience, so an access token can't be replayed as an event and an event can't be used as an access token. Missing or equal: 503 |
| Times | `exp` future; `iat` required, ≤60 s in the future, ≤`STN_IDP_EVENT_MAX_AGE_SECONDS` old (default 600); `nbf` honoured |
| Subject / event id | `sub` and `jti` required and well formed |
| Kind | `event` ∈ `email_verified`, `phone_verified`, `mfa_enrolled`, with `verified: true` (boolean) |
| Replay | `(issuer, jti)` unique; a repeat is refused and audited |

Only identifiers and codes are stored. Email addresses and phone numbers are never stored. Rows are append-only (database triggers).

## 3. Client onboarding

```
invited --claim--> provisional --activate (owning clinician)--> active <--suspend / reactivate (admin)--> suspended
any state except deactivated --deactivate (admin)--> deactivated (final)
```

1. The owning clinician calls `POST /v1/clients/{id}/client-account/invitation`. A one-time code is returned **once**; only its SHA-256 is stored. Reissuing invalidates the earlier code. Expiry is `STN_CLIENT_INVITE_HOURS` (default 168).
2. The client signs in (role `client`) and calls `POST /v1/me/client-invitation/claim`. The code is single use and bound to the issuing organisation. One client account per sign-in per organisation.
3. While **provisional**, the client can only read their onboarding status (`GET /v1/me/client-account`) and record acknowledgements (`POST /v1/me/client-acknowledgements`) for the **current** versions of the terms, privacy notice and consent (`STN_TERMS_VERSION`, `STN_PRIVACY_NOTICE_VERSION`, `STN_CONSENT_VERSION`). No clinical information is visible.
4. The owning clinician activates the account. That works only when the IdP has recorded every kind in `STN_CLIENT_REQUIRED_VERIFICATIONS` (default `email,mfa`) and every current version is acknowledged. Missing version configuration fails closed (503). A new terms version means the client must acknowledge again.
5. Active clients read **their own** assessment metadata (`GET /v1/me/client-assessments`): no answers, no notes. No client route takes a client id; the client is resolved from the token subject and organisation, so identifier manipulation has nothing to work with. Tests confirm that every id-bearing staff route returns 403 to the client role.

## 4. Clinician registration and attestation (D-08)

- The clinician submits their own registration details (`POST /v1/me/clinician-registration`): authority code, number, scope code and expiry. **A submission grants nothing.**
- An admin who is **not** that clinician attests that they checked it against the public register (`POST /v1/admin/clinician-registrations/{id}/attest`). The attestation's reference is validated: the record must exist, be in the same organisation, be the clinician's latest submission, be unexpired and not already attested. `source_url` must be https, and its host must be in `STN_REGISTER_HOSTS` when that is set. `checked_on` must be in the last `STN_ATTESTATION_MAX_AGE_DAYS` (default 30) and not in the future. Self-attestation is refused by the code and by a database `CHECK`.
- Verified = latest registration + unrevoked attestation + unexpired. Revocation (`POST /v1/admin/attestations/{id}/revoke`) and expiry remove clinical access straight away.
- Enforcement: `STN_REQUIRE_VERIFIED_REGISTRATION` (Bicep sets `true` for staging and production; the default is true whenever `STN_ENVIRONMENT` is staging or production, and false locally). It applies to every route reached through the clinician or reviewer role, except the clinician's own registration routes.
- **Limitation:** the platform records what an admin says they checked. It does not query any register itself.

## 5. Live configuration still required (owner/IT: blocked on the Entra tenant)

| Item | What to configure | Setting |
|---|---|---|
| API app registration | Expose an API; access tokens v2 | `STN_OIDC_AUDIENCE`, `STN_OIDC_ISSUER`, `STN_OIDC_JWKS_URL` |
| App roles | `STN.Clinician`, `STN.Reviewer`, `STN.Admin`, `STN.Client`; assign staff and client users | `STN_OIDC_ROLE_MAP=STN.Clinician=clinician,STN.Reviewer=reviewer,STN.Admin=admin,STN.Client=client` |
| Organisation claim | Custom claim (directory extension or claims-mapping policy) carrying the STN organisation id, or `tid` for one org per tenant | `STN_OIDC_ORG_CLAIM` |
| MFA | Conditional Access requiring MFA for both audiences, with an authentication context | `STN_MFA_ACRS_VALUES` (or `amr` `mfa`) |
| Client sign-up | External ID user flow with email verification and MFA enrolment | — |
| **Verification events** | **Decision needed:** Entra doesn't natively post signed verification events to an external webhook. Options: **(A)** a small relay (for example an Azure Function behind an Entra custom authentication extension) that signs events with its own key and publishes a JWKS; or **(B)** change `identity_events` to accept verification facts from verified token claims. A is implemented against this contract; B would be a small code change | `STN_IDP_EVENT_AUDIENCE`, optionally `STN_IDP_EVENT_ISSUER` / `STN_IDP_EVENT_JWKS_URL` |
| Document versions | Publish the approved terms, privacy notice and consent; set their version ids | `STN_TERMS_VERSION`, `STN_PRIVACY_NOTICE_VERSION`, `STN_CONSENT_VERSION` |
| Registers | Host names of the public registers admins check | `STN_REGISTER_HOSTS` |

All of these are wired from GitHub `staging` environment variables through `deploy-staging.yml` into App Service settings (`infra/azure/main.bicep`).

## 6. Not built yet

- Client-facing screens (the portal UI). The API is ready for them.
- Invitation delivery by email or SMS. This waits on the notification service and an approved provider; until then the clinician hands the code over directly.
- Password recovery and session-expiry policy are the identity provider's job (Entra). The API validates `exp` on every request.
- Client data-access and correction requests through the client role. The staff-side Privacy Act IPP 6/7 workflow exists (`privacy_requests.py`).
