# STN Whole-Person Assessment Platform

**Supportive Therapy Network Limited (STN)**  
A whole-person assessment and clinical support platform designed to connect intake, safety screening, diagnostic assessment, clinical review, care planning and ongoing support.

This repository is the public engineering source for the STN digital assessment platform.

## Product pathway

Dashboard → New Client → Whole Person Initial Assessment → Safety Gate → Adaptive Routing → Selected Assessments → Integrated Results → Clinical Review → Diagnostic Decision Support → Whole-Person Care Plan → Finalise → Report.

### Stage 1 — Whole Person Initial Assessment

A broad intake covering presenting concerns, personal and developmental context, social circumstances, physical health, medications, substance use, mental health screening, safety, strengths and protective factors.

### Stage 2 — Comprehensive Diagnostic Assessment

A structured clinician-led assessment covering symptom patterns, duration, severity, functional impairment, relevant history, mental status, differential diagnosis, comorbidity and clinical formulation. Diagnostic conclusions require practitioner review and approval; screening scores alone do not establish a diagnosis.

Both stages are intended to share a single client record and minimise repeated data entry.

## Verified build and deployment status — 15 November 2026

- Main verification workflow run 223 passed: https://github.com/drpsych26/e-STN-Whole-Person-Assessment/actions/runs/43657621191
- Prototype JavaScript checks and synthetic-data regression tests passed.
- Flutter source restoration, static analysis, automated tests and build completed successfully.
- Android APK build 4 is available for controlled testing: https://github.com/drpsych26/e-STN-Whole-Person-Assessment/releases/tag/stn-android-4
- Direct APK download: https://github.com/drpsych26/e-STN-Whole-Person-Assessment/releases/download/stn-android-4/app-release.apk
- Public STN website deployment succeeded: https://github.com/drpsych26/STN-Website/actions/runs/43658020226
- Website URL: https://drpsych26.github.io/STN-Website/

**Important:** APK build 4 is an installable controlled-testing build, not a production-signed clinical release. A successful build or static website deployment does not establish that a secure clinical record backend or live clinical service is operational.

## Clinical and technical principles

- Human clinical oversight and accountable diagnostic decisions.
- Traceability from approved source material to assessment items and scoring.
- Clear distinction between screening, decision support and diagnosis.
- Role-based access and least-privilege permissions.
- Privacy, confidentiality and secure handling of health information.
- Auditable clinical actions and safety-event workflows.
- Accessible, responsive design for phones, tablets and desktop.
- Resilient operation for low-bandwidth settings, with offline capability subject to safe synchronisation controls.
- Transparent scoring, limitations and decision-support rationale.

## Technology and repository structure

The mobile application is built with Flutter. The repository includes application source, browser-based assessment work, implementation patches, automated checks, source references and release documentation.

- `flutter/` — Flutter application source and source archives.
- `prototype/` — browser assessment experience and prototypes.
- `implementation-patches/` — tracked Flutter implementation changes.
- `reference/` — product, clinical, privacy and deployment requirements.
- `docs/` — governance, release and supporting documentation.
- `tests/` — regression tests and assessment traceability material.
- `.github/workflows/` — automated build and verification workflows.

## Production release gate

The project owner confirms that clinical validation has been completed. That confirmation is separate from the remaining production controls. The exact release must still be mapped to the confidential validation evidence, and the technical, instrument-permission, privacy, security, safety-operations, practitioner-governance and release-approval gates must be completed.

See [Production Go-Live Gate](docs/release/PRODUCTION-GO-LIVE-GATE.md) for the current itemised release checklist.

Until all applicable gates are approved, use synthetic test data only. Do not use the APK or website to collect, store or process identifiable client health information.

## New Zealand operating context

The platform is being developed for a New Zealand service context. Applicable privacy, health-information, professional, consumer and safety obligations must be assessed for the actual service model and deployment. Project documentation provides engineering and governance requirements; it is not legal advice or evidence of completed regulatory approval.

## Security and intellectual property

The public repository must not store client records, identifiable health information, passwords, API keys, signing keys or other secrets. Do not submit confidential clinical information through public issues or discussions.

STN-owned material is subject to the repository's copyright and licensing notices. Third-party packages, instruments, scales, fonts and other materials remain subject to their respective licences and permissions. Review `LICENSE`, `COPYRIGHT.md` and the intellectual-property register before reuse or redistribution.

Do not disclose vulnerabilities publicly. Follow `SECURITY.md` for responsible security reporting. Changes affecting clinical content, risk pathways, scoring, diagnostic logic or safety workflows require documented clinical review in addition to engineering review.

---

**Supportive Therapy Network Limited**  
STN Whole-Person Assessment Platform
