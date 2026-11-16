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
- [ ] Replace staging/demo authentication with an approved OIDC/JWT verifier.
- [ ] Replace in-memory demo storage with managed PostgreSQL or an equivalent approved clinical record store.
- [ ] Implement authenticated clinician access, MFA and role-based access control.
- [ ] Implement encrypted transport and storage, secure secret management and controlled backups.
- [ ] Implement client/assessment persistence, server-side validation and scoring.
- [ ] Implement immutable audit events for access, edits, exports and sign-off.
- [ ] Implement consent, privacy notice, access/correction, retention and secure disposal workflows.
- [ ] Test backup restoration, failure recovery and data migration.

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

## Data-use restriction

Until all applicable gates are signed off, use synthetic test data only. Do not enter identifiable client information or use the APK/site as a live clinical record system. A successful workflow, deployed static website or installable APK is not evidence that a clinical backend, secure records system or operational crisis response exists.

## Release decision

**Current decision: controlled testing / public informational website only. No identifiable clinical production use.**
