# STN Whole-Person Assessment Platform

**Supportive Therapy Network Limited (STN)**  
A whole-person assessment and clinical support platform designed to connect intake, safety screening, diagnostic assessment, clinical review, care planning and ongoing support.

This repository is the public engineering source for the STN digital assessment platform.

## Product vision

STN is building a connected pathway from initial client contact through comprehensive assessment and coordinated care. The platform is designed for use by clients and authorised practitioners, with clinical decisions remaining the responsibility of appropriately qualified professionals.

## Platform components

- Public STN website and service information.
- Client-facing assessment experience.
- Authorised clinician workspace.
- Whole Person Initial Assessment (Stage 1).
- Comprehensive Diagnostic Assessment (Stage 2).
- Safety screening, safeguarding and escalation workflows.
- Adaptive assessment pathways and approved screening instruments.
- Integrated clinical formulation and diagnostic decision support.
- Clinician review, care planning and reporting.
- Follow-up, outcome monitoring and care navigation.
- Android application and responsive web experience.

## Two-stage assessment pathway

### Stage 1 — Whole Person Initial Assessment

A broad intake covering presenting concerns, personal and developmental context, social circumstances, physical health, medications, substance use, mental health screening, safety, strengths and protective factors.

### Stage 2 — Comprehensive Diagnostic Assessment

A structured clinician-led assessment covering symptom patterns, duration, severity, functional impairment, relevant history, mental status, differential diagnosis, comorbidity and clinical formulation. Diagnostic conclusions require practitioner review and approval; screening scores alone do not establish a diagnosis.

Both stages are intended to share a single client record and minimise repeated data entry.

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

## Technology

The mobile application is built with Flutter. The repository includes application source, browser-based assessment work, implementation patches, automated checks, source references and release documentation.

Browse the repository:
- `flutter/` — Flutter application source and source archives.
- `prototype/` — browser assessment experience and prototypes.
- `implementation-patches/` — tracked Flutter implementation changes.
- `reference/` — product, clinical, privacy and deployment requirements.
- `docs/` — governance, release and supporting documentation.
- `tests/` — regression tests and assessment traceability material.
- `.github/workflows/` — automated build and verification workflows.

## Development and release status

The repository is public and development is directed toward the STN production release. Automated build and test results provide engineering evidence; they do not, by themselves, establish clinical validation or production readiness.

The public repository must not be used to store client records, identifiable health information, passwords, API keys, signing keys or other secrets. Do not submit confidential clinical information through public issues or discussions.

The project owner confirms that clinical validation has been completed. The controlled release dossier records that status; the validation record must be mapped to the exact release version without publishing confidential material. Real-client activation remains dependent on the separate technical, instrument-permission, privacy, security, safety-operations, practitioner-governance and release-approval controls. Until the exact production environment is approved, demonstrations and test environments must use synthetic data only.

## New Zealand operating context

The platform is being developed for a New Zealand service context. Applicable privacy, health-information, professional, consumer and safety obligations must be assessed for the actual service model and deployment. The project documentation includes working requirements and templates; these are not legal advice or evidence of completed regulatory approval.

## Build and verification

Use the workflow files in `.github/workflows/` for the supported automated checks and build processes. Consult the current workflow run and release notes for the exact status of each build. A successful build does not certify the application for clinical operation.

## Intellectual property and third-party material

STN-owned material is subject to the repository's copyright and licensing notices. Third-party packages, instruments, scales, fonts and other materials remain subject to their respective licences and permissions. Review `LICENSE`, `COPYRIGHT.md` and the intellectual-property register before reuse or redistribution.

## Contributions and security

Do not disclose vulnerabilities publicly. Follow `SECURITY.md` for responsible security reporting. Changes affecting clinical content, risk pathways, scoring, diagnostic logic or safety workflows require documented clinical review in addition to engineering review.

---

**Supportive Therapy Network Limited**  
STN Whole-Person Assessment Platform
