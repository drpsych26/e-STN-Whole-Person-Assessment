# STN Production Go-Live Gate

**Status: NOT APPROVED FOR IDENTIFIABLE CLIENT USE**

This document separates successful engineering builds from approval to operate a clinical service. Clinical validation is NOT treated as complete unless version-specific evidence, independent review and accountable sign-off are recorded. No such evidence is established by this document; technical, privacy, security, operational and release controls below remain separate mandatory gates.

## Verified engineering state (15 November 2026)

- Main verification workflow run 223 completed successfully: https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/43657621191
- Prototype JavaScript syntax and synthetic-data regression tests passed.
- Flutter source restoration, static analysis, automated tests and build completed successfully.
- Android APK build 4 was published as a controlled-testing asset: https://github.com/drpsych26/e-STN-Whole-Person-Assessment/releases/tag/stn-android-4
- APK asset: https://github.com/drpsych26/e-STN-Whole-Person-Assessment/releases/download/stn-android-4/app-release.apk
- APK release notes explicitly restrict this build to controlled testing. It is not the production-signed clinical release.
- Website Pages deployment completed successfully: https://github.com/drpsych26/STN-Website/actions/runs/43658020226

## Required release gates

### Android distribution
- [ ] Generate and protect the production Android signing keystore outside the repository.
- [ ] Configure GitHub Actions secrets for the keystore and signing credentials; never commit or send these secrets in chat.
- [ ] Add and verify a production-signing workflow and confirm the APK is signed with the intended release certificate.
- [ ] Verify package/application ID, version code/name, app icon, permissions, network security, backup policy and release build configuration.
- [ ] Test installation, upgrade, uninstall, offline behaviour and data handling on supported Android devices.
- [ ] Produce release checksum and retain the signed artifact and signing-certificate fingerprint in the controlled release record.

### Clinical service backend

> **Engineering evidence, 22–23 November 2026 (not gate approval).** PR #54 (`backend-clinician-review`, merged to `main` as `f706a9f` on 23 November 2026) implements server-side roles (clinician, reviewer, admin), MFA enforcement, encrypted assessment records, the human review and sign-off workflow with separation of duties, safety-flag acknowledgement gating, immutable signed-off records with versioned amendments, a hash-chained append-only audit, and a PostgreSQL store with migrations. CI on its merged head passed: API tests on SQLite and on a PostgreSQL 16 service container (130 passed, none skipped), static quality, verification and Flutter web validation.
>
> The hardening increment (branch `backend-hardening`, PR #55) adds organisation separation, consent records, a configurable retention policy with legal holds and two-person disposal, logged exports, a versioned keyring with re-encryption and a Key Vault provider stub, rate limiting, and a backup/restore drill that CI runs on synthetic data (206 API tests on SQLite and PostgreSQL locally before push; CI results are recorded on the PR).
>
> The review lifecycle increment (branch `backend-review-lifecycle`, PR #57, 24 November 2026) adds named reviewer assignment with a reassignment queue, a per-organisation clinician account registry (invited, active, suspended, deactivated; two-person reactivation; non-active subjects refused even with a valid token), an access-review report, client access and correction request tracking under information privacy principles 6 and 7 (configurable working-day due dates, access-response exports through the export log, amendments or encrypted statements of correction), and a Redis shared rate-limit store with its own CI job. The statutory response period is not set in code and has not been verified against the Act; the privacy officer must confirm it. CI results are recorded on the PR.
>
> None of this is deployed or configured against an approved identity provider, managed database or key vault, so no box below is ticked. Each item still needs production configuration, independent verification and sign-off.

- [ ] Replace staging/demo authentication with an approved OIDC/JWT verifier. *(Verifier code exists; identity provider not yet selected or approved.)*
- [ ] Replace in-memory demo storage with managed PostgreSQL or an equivalent approved clinical record store. *(PostgreSQL support in PR #54; no managed database provisioned.)*
- [ ] Implement authenticated clinician access, MFA and role-based access control. *(Engineering in PR #54, CI green; unverified in production. Reviewer assignment, the account status registry and the access-review report in PR #57; production must set the registry and assignment requirements and keep the identity provider in step.)*
- [ ] Implement encrypted transport and storage, secure secret management and controlled backups. *(Encrypted storage, keyring rotation and an untested-live Key Vault provider in engineering; TLS, managed keys and backups need Azure.)*
- [ ] Implement client/assessment persistence, server-side validation and scoring.
- [ ] Implement immutable audit events for access, edits, exports and sign-off. *(Access, edit, transition and sign-off events in PR #54; export, consent, hold, disposal and re-encryption events in the hardening PR; assignment, account status, refused-access and privacy-request events in PR #57.)*
- [ ] Implement consent, privacy notice, access/correction, retention and secure disposal workflows. *(Consent records, legal holds and two-person disposal in the hardening PR; retention period unset pending legal advice; privacy notice not implemented. Access and correction request tracking, access-response exports and statements of correction in PR #57; response period unset pending the privacy officer's confirmation; identity checks, withholding decisions and secure release are procedures still to be written.)*
- [ ] Test backup restoration, failure recovery and data migration. *(Synthetic dump/restore/verify drill in CI from the hardening PR; production backup, point-in-time recovery and disaster-recovery exercises not done.)*

### Safety, privacy and clinical operations
- [ ] Complete and approve the Privacy Impact Assessment and hosting/data-processing assessment.
- [ ] Confirm all instrument licences and written digital reproduction, scoring and reporting permissions.
- [ ] Document clinician scope, accountability, supervision and diagnostic sign-off.
- [ ] Implement human-owned crisis escalation, acknowledgement timeouts, fallback and incident recording.
- [ ] Complete security testing, vulnerability remediation and incident response procedures.
- [ ] Complete accessibility and UAT on phone, tablet and desktop.
- [ ] Approve operational support, monitoring, service continuity and change control.
- [ ] Map the owner-confirmed clinical validation evidence to the exact release version in the confidential evidence store.
- [ ] Obtain final authorised production release approval.

### Public website
- [ ] Open the published Pages URL on real devices and verify content, responsive layout, links and assets.
- [ ] Supply verified STN public contact details and privacy officer contact.
- [ ] Replace the privacy-notice draft with a reviewed and approved notice before collecting personal information.
- [ ] Confirm actual services, referral eligibility, operating regions and availability before advertising them.
- [ ] Review terms, accessibility and all public claims.
- [ ] Connect the registered custom domain only after the exact domain and DNS control are confirmed.

## Owner-only actions

These cannot be completed by engineering changes. Each needs the STN owner or an accountable third party.

1. **Android release signing:** generate the production keystore offline, store it under STN control, and add the `STN_ANDROID_KEYSTORE_BASE64` and `STN_ANDROID_KEYSTORE_PASSWORD` repository secrets. Never share them in chat or commit them.
2. **Website domain:** set `supportivetherapy.network` in the STN-Website Pages settings, add the GitHub Pages DNS records at the registrar, then enable Enforce HTTPS.
3. **Website content:** STN-Website PR #9 was merged and published on 23 November 2026 with the head office address and privacy officer shown as "To be confirmed". Confirm the public phone, email, head office address and privacy officer so the site can be updated.
4. **Azure:** create the STN-owned tenant and production subscription (New Zealand North), Azure Database for PostgreSQL, Key Vault and App Service, following `docs/infrastructure/AZURE-PRODUCTION-SUBSCRIPTION-AND-DEPLOYMENT.md`.
5. **Identity provider:** register the API and app in the STN tenant, define the app roles, and enforce MFA through Conditional Access.
6. **Privacy:** complete and approve the Privacy Impact Assessment, appoint a privacy officer, and publish an approved privacy notice.
7. **Instrument licences:** obtain written digital reproduction, scoring and reporting permissions for every instrument.
8. **Security:** commission an independent penetration test and remediate its findings.
9. **Clinical safety:** approve the clinical safety case, the hazard log, the safety-flag acknowledgement and escalation SOP, and clinician scope and sign-off authority.
10. **Insurance:** professional indemnity, cyber and public liability cover appropriate to the service.
11. **Repository visibility:** `drpsych26/e-STN-Whole-Person-Assessment` is currently **public**, while repository records state it should remain private. Decide whether to make it private.
12. **Retention period:** obtain legal advice on the minimum retention period and how it is counted (Health (Retention of Health Information) Regulations 1996 and any other obligation) before `STN_RETENTION_PERIOD_DAYS` is set or any record is disposed of.
13. **Organisation model:** decide how organisations are represented in the identity provider (claim `stn_org` or one tenant per organisation via `tid`) and the access-review process for membership.
14. **Final release approval:** formal go-live sign-off for the exact release version.

## Data-use restriction

Until all applicable gates are signed off, use synthetic test data only. Do not enter identifiable client information or use the APK/site as a live clinical record system. A successful workflow, deployed static website or installable APK is not evidence that a clinical backend, secure records system or operational crisis response exists.

## Release decision

**Current decision: controlled testing / public informational website only. No identifiable clinical production use.**
