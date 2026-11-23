# STN secure backend foundation — architecture decision

**Status: proposed engineering baseline; non-live; synthetic data only.**  
**Purpose:** define the smallest safe integration foundation for the STN website and Flutter app. This document is not a privacy, legal, clinical, security, or production approval.

## 1. Decision and boundaries

Build a versioned HTTPS API in front of a managed PostgreSQL data store. Use an established OpenID Connect (OIDC) identity provider; the API validates access tokens and enforces permissions server-side. The website and Flutter client are API consumers. Neither browser storage nor device-local encrypted storage is the clinical system of record.

Do not select a hosting vendor, region, identity vendor, or production data processor until STN has documented hosting location, subprocessors, cross-border processing, contractual terms, backup location, support access, and NZ privacy review. Do not enable production deployment or real-client data in this foundation.

## 2. Logical components

- Public website: public information and non-sensitive enquiry routing only. No clinical form, symptom questionnaire, health file upload, or health details in URL/query strings, analytics, or email.
- Flutter app: authenticated clinician interface in the intended clinical workflow; offline drafts remain explicitly non-authoritative until server reconciliation and must not bypass authorisation.
- API: TLS only; OIDC JWT verification (issuer, audience, signature, expiry, not-before); strict schema validation; rate limiting; request size limits; idempotency for create/finalise actions; correlation IDs that contain no client identifiers.
- PostgreSQL: managed service, encrypted storage, private networking where supported, encrypted backups, tested restore, migrations, least-privilege database roles.
- Identity: MFA policy, account lifecycle, short-lived sessions, revocation, staff offboarding, recovery and periodic access review handled by an approved provider and documented process.
- Audit: append-only/tamper-evident events for reads, writes, exports, finalisation, corrections, role changes and administrative actions. Never log assessment answers, tokens, secrets, or unnecessary identifiers.

## 3. Authorisation model

Deny by default. Every API operation must verify the authenticated subject, active account, organisation membership, role, action permission, and record scope on the server. UI hiding is not authorisation.

Initial roles to validate with STN governance:
- Clinician: access only to assigned/authorised client records and permitted clinical actions.
- Clinical supervisor: defined oversight and review permissions, not blanket administrator access.
- Operations administrator: account/configuration administration; no automatic clinical-content access.
- Auditor: read-only access to approved audit metadata; no unrestricted assessment content.
- Client/patient portal role: not enabled in the first backend increment.

Enforce organisation and record-level isolation in API services and database policy. Test cross-organisation and cross-client access denial, including guessed UUIDs, exports, background jobs and direct database paths.

## 4. Initial data model (logical)

- organisations: stable UUID, legal/display name, status, created timestamp.
- user_identities: OIDC issuer + subject (unique pair), organisation UUID, status, last-authenticated timestamp; no local password storage.
- role_assignments: user, organisation, role, scope, granted/revoked timestamps, grantor and reason.
- client_records: random UUID, organisation UUID, pseudonymous display code, status, created/updated metadata. Names/contact details are excluded from the first engineering schema until the collection purpose, lawful authority, access process and retention are approved.
- assessments: UUID, client UUID, assessment type/version, source/instrument version, state (draft, submitted, under_review, finalised, withdrawn), author, timestamps, finalisation metadata.
- assessment_responses: assessment UUID, item identifier/version, response status (answered, declined, uncertain, not_present), response value, sequence/version. Preserve original submitted values; corrections create attributed amendments rather than overwrite.
- clinical_reviews: assessment UUID, reviewer identity, review status, decision notes reference, timestamps and sign-off metadata. Do not implement diagnostic automation.
- consent_records: client UUID, notice version, purpose, status, recorded-by, timestamp, withdrawal metadata. Final wording and lawful basis require qualified review.
- audit_events: append-only event UUID, actor subject, organisation, action, object type/UUID, timestamp, outcome, correlation ID, reason. Avoid storing sensitive payloads in audit metadata.

All tables require organisation scope where applicable, foreign keys, restrictive deletion, timestamps, and migration-controlled schema changes. Define retention and deletion/archival rules before production.

## 5. Initial API surface (versioned /v1)

- GET /v1/me — verified identity and effective roles (no client data).
- GET /v1/clients — paginated, scoped client index; disabled until client-data governance is approved.
- POST /v1/clients — create pseudonymous test record in non-live environment only.
- GET /v1/clients/{client_id}/assessments — scoped assessment list.
- POST /v1/assessments — create draft with explicit schema and instrument version.
- GET /v1/assessments/{assessment_id} — scoped read with state and version.
- PUT /v1/assessments/{assessment_id}/responses — validated draft response update with optimistic concurrency.
- POST /v1/assessments/{assessment_id}/submit — submit immutable response snapshot for review.
- POST /v1/assessments/{assessment_id}/reviews — authorised human review event.
- POST /v1/assessments/{assessment_id}/finalise — authorised human sign-off; immutable final record.
- POST /v1/assessments/{assessment_id}/amendments — attributed correction/addendum with reason; never silent overwrite.
- GET /v1/audit — restricted, paginated audit metadata.
- No public unauthenticated endpoints for clinical records, no AI diagnosis endpoint, and no automated crisis disposition endpoint.

Every route requires explicit request/response schemas, permission mapping, validation, audit behaviour, error contract, rate limit and automated positive/negative tests before implementation.

## 6. Safety and clinical workflow constraints

- A questionnaire score must never be the sole basis for risk classification, diagnosis, crisis disposition, or service eligibility.
- Positive, uncertain, declined, missing, contradictory or stale safety responses must not silently become negative responses.
- Human ownership, acknowledgement, timeout, fallback, coverage hours, incident recording and escalation SOP must be approved before any live safety workflow exists.
- AI may not autonomously diagnose, triage emergencies, or make crisis decisions.
- The API must preserve the distinction between source responses, deterministic calculations, and clinician interpretation.

## 7. Security and privacy acceptance criteria

Before any production data:
1. Approved data-flow map, threat model, privacy impact assessment and qualified NZ privacy/legal review.
2. Approved purpose, collection notice, consent/authority, access/correction, retention/disposal, disclosure, breach response and cross-border processing.
3. Hosting region, subprocessors, support access, backups and disaster recovery documented and accepted.
4. OIDC configuration, MFA, session expiry/revocation, role/record-scope tests and staff offboarding tested.
5. TLS, encryption at rest, managed key lifecycle, secret rotation, dependency scanning, vulnerability remediation and independent penetration test.
6. Append-only audit verification, immutable finalisation/addenda, export controls and access review.
7. Successful backup restore and incident-response exercise.
8. Clinical instrument permissions, source traceability, independent validation, human escalation SOP and accountable sign-off for the exact release version.
9. Accessibility, cultural safety, supervised UAT, support ownership and change-control approval.

## 8. Delivery sequence

1. **Foundation (non-live):** approve vendor/hosting decision; create API skeleton, migrations, CI security checks and synthetic fixtures.
2. **Identity:** integrate OIDC in a test tenant; prove server-side RBAC and cross-record denial.
3. **Records:** implement draft and submitted assessment persistence with immutable versions and audit.
4. **Client integration:** connect Flutter test build to staging API; website remains public-only and does not collect health data.
5. **Safety and review:** implement only after clinical owner approves the workflow and operating procedures.
6. **Assurance:** privacy/security review, independent tests, restore drill, UAT and formal go/no-go.
7. **Production:** separately authorised deployment after every applicable gate passes.

## 9. Explicit non-goals for this increment

No live hosting, real-client data, public intake, production credentials, patient portal, autonomous diagnosis, clinical risk scoring, crisis response automation, or claim of regulatory compliance. Use synthetic data only.

## 10. Implementation status — clinician sign-in and review increment (November 2026)

**Status: implemented on branch `backend-clinician-review` for engineering review; non-live; synthetic data only.** Details and configuration: `backend/README.md`. This section records what exists in code. It does not tick any production gate.

Implemented (with automated tests running on SQLite and PostgreSQL):
- OIDC RS256 verification (existing), plus server-side roles from a configurable claim with provider-to-STN mapping. Missing roles fail closed.
- MFA enforcement, on by default, via configurable `amr` / `acr` / `acrs` evidence.
- Encrypted, author-bound assessment records against owner-scoped client records, with optimistic concurrency (`revision`).
- Human review workflow with separation of duties: an author cannot start review of, or sign off, their own work. Sign-off quotes the reviewed content hash, signed-off rows are immutable (application rule plus database trigger), and corrections are new versions (`parent_id`).
- Safety flags that must each be acknowledged by a named clinician or reviewer before review starts. They carry no automated disposition.
- Hash-chained, append-only audit events (UPDATE/DELETE/TRUNCATE blocked by triggers) with admin-only chain verification. No payloads appear in audit rows.
- PostgreSQL store behind the same interface as the SQLite test store, versioned migrations, a local `docker-compose.yml`, and a CI PostgreSQL service job.

Deviations from sections 3–5, recorded for governance acceptance:
- State names are `draft, submitted, in_review, returned, signed_off` (section 4 proposed `under_review, finalised, withdrawn`). `signed_off` corresponds to `finalised`. `withdrawn` is not implemented.
- Endpoints are `start-review`, `return` and `sign-off` rather than a single `reviews` endpoint plus `finalise`.
- The `admin` role covers audit-metadata access. There is no separate auditor role yet. The operations administrator gets no clinical content access, as section 3 requires.
- Organisation scope and multi-tenant isolation, reviewer assignment policy, consent records and the client index endpoint are **not** implemented yet. The increment is single-organisation and owner-scoped.
- Any reviewer may see queue metadata for submitted work and acknowledge its safety flags. Payload access is limited to the reviewer who started the review. Clinical governance must confirm this model and the safety-flag acknowledgement SOP before live use.
