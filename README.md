# STN Whole Person Assessment

**Product owner:** Supportive Therapy Network Limited (STN)  
**Repository:** Private development and release-candidate source  
**Current branch baseline:** `main` at `652341b81422e00658908e18a175a6ff4027d633` (4 November 2026)

## Release status

**Release preparation authorised by the owner on 4 November 2026. Production clinical deployment is not verified or enabled by this repository update.** This distinction is deliberate: build success does not establish clinical validity, instrument rights, regulatory status, privacy compliance, operational readiness or permission to process real patient data.

- Development and controlled synthetic-data testing may continue.
- Keep this repository private until a public-source, secret, IP and privacy review is complete.
- Do not use real client/patient information, production credentials or secrets in this repository or current prototype.
- Do not represent the browser prototype or current debug APK as a production clinical system.
- No production hosting, live integrations or real-client clinical workflow is enabled by this update.

## Current engineering evidence

The following GitHub Actions workflows passed on commit `652341b81422e00658908e18a175a6ff4027d633` on 3 November 2026:

- [STN verification](https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41721919121) — prototype static checks, Flutter source restore, Flutter analysis/tests and Android debug APK artifact.
- [Flutter web validation](https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41721919005) — dependency resolution, formatting, static analysis, tests and Flutter web release build.
- [Static quality checks](https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/41721919271) — static and regression checks.

These are successful engineering checks for the recorded commit. The Android output is a **debug APK**, not a signed production APK. The web artifact is a build bundle, not proof of a deployed, secured production service.

## Application scope and limitations

- Browser-based Whole Person Initial Assessment prototype with synthetic-data workflow and regression tests.
- Flutter v4 MVP with interim MDD, GAD, PTSD and ADHD modules and a partial 25-item Whole Person Core Intake.
- Core Intake safety-tagged unanswered or endorsed items require human review; the implementation does not assign clinical risk tiers or emergency disposition.
- The supplied paper pilot contains 208 items across 24 groups. The current digital Core Intake is partial; full source-to-code traceability, adaptive routing and the remaining items are not complete.
- Current browser storage is local demonstration storage, not a secure clinical record platform.
- Local encrypted Flutter storage is not a substitute for production identity, server-side authorisation, tenant isolation, audit, backup, retention and operational controls.

## Brand and presentation

The repository's current digital brand standard is documented in [STN Brand and Interface Standard](docs/brand/STN-BRAND-AND-INTERFACE-STANDARD.md).

- STN purple: `#AF2CFF`
- Near-black brand background: `#08070A`
- Charcoal clinical surfaces with white and grey typography.
- System-first sans-serif font stack for offline consistency; no external font download is required.
- Proposed digital SVG mark: `assets/brand/stn-mark.svg`.

**Logo provenance note:** the SVG is a newly added geometric digital mark for this implementation. It has not been verified as an exact reproduction of any previously approved or registered STN master logo. Replace it with the approved master artwork if different artwork exists before external publication.

## Copyright and third-party licensing

- `LICENSE` and `COPYRIGHT.md` state the proprietary position for STN-owned material only.
- Third-party packages, fonts, icons, artwork and assessment instruments retain their own licences and permissions.
- Do not copy, bundle, digitise, score or distribute protected assessment content without documented written permission.
- Record contributor provenance, IP assignments and third-party licences in the controlled IP register.
- Generate and review an SBOM and preserve dependency notices for each distribution build.

Copyright notices do not establish clinical validity, instrument permission, regulatory approval or privacy/security compliance.

## Required evidence before production clinical release

1. Confirm the written approval/authorisation reference, issuing body, exact product version, intended use, settings, conditions and exclusions.
2. Complete source-to-code traceability for every item, rule, branch, score, report and test.
3. Record written digital-use and scoring permissions for each assessment instrument.
4. Complete clinical validation, clinical safety case, hazard log and signed residual-risk acceptance.
5. Implement and test human safety escalation, acknowledgement, timeout, fallback and operational ownership.
6. Complete identity, MFA, role-based access, server-side authorisation, audit, multi-client isolation and secure clinical-record persistence.
7. Complete the NZ privacy impact assessment, collection notices, consent, access/correction, retention, disclosure and breach-response controls.
8. Complete secret scanning, dependency/SBOM and licence review, threat modelling, SAST/DAST and independent penetration testing.
9. Verify backup/restore, disaster recovery, monitoring, incident response, support and rollback.
10. Complete accessibility, supported-device testing, controlled UAT and independent clinical review.
11. Build and sign the Android release package using controlled signing keys; verify web deployment security headers, HTTPS, CSP and backend controls.
12. Record a signed go/no-go decision tied to exact commit and artifact hashes.

See `docs/governance/CLINICAL-RELEASE-DOSSIER.md`, `SECURITY.md`, `reference/PRODUCTION-NZ-REQUIREMENTS.md` and `reference/DEPLOYMENT-CHECKLIST.md`.

## Local prototype

Open `prototype/index.html` in a modern browser. GitHub's file viewer displays source rather than running the prototype. All test entries must be fictitious. The browser prototype uses local browser storage and is not suitable for real clinical records.

## Source archive and CI

The Flutter v4 source archive is retained under `flutter/source-archives/parts/`. CI reconstructs it, checks its SHA-256 and applies tracked patches under `implementation-patches/flutter-v4/`. Preserve original source archives and review patches before adoption.

## Copyright

© 2026 Supportive Therapy Network Limited. All rights reserved in STN-owned material. Third-party components remain subject to their own licence terms.
