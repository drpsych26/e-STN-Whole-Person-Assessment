# Security and clinical safety

## Rules for this repository

- Never use real identifiable client data in this repository, its tests, CI or any prototype. Synthetic data only.
- Do not store secrets in source control. Signing keys and deployment credentials live in GitHub environment secrets or Azure Key Vault.
- **Keep this repository private** while the content and clinical governance remain under review. Visibility is an owner setting (Settings → General → Danger Zone). The public website is a separate repository (`STN-Website`) and does not depend on this one.
- Prototype scoring and safety flags are demonstrative only and are not validated clinical rules. Server-side scoring is disabled until clinical approval (`STN_ACTIVE_INSTRUMENTS`).
- Licensed questionnaire wording must not be published without confirmed permission (see `docs/clinical/INSTRUMENT-REGISTER.md` once merged).
- Production deployment requires formal clinical governance, instrument licensing review, privacy/security assessment, penetration testing, backup/recovery planning and clinician-approved escalation procedures.

## Reporting a vulnerability

Please report security issues **privately**: either through GitHub's private vulnerability reporting for this repository (if enabled) or by email to privacy@supportivetherapy.network with "Security" in the subject. Do not open a public issue, and do not include real personal or health information in the report.

We will acknowledge reports as soon as practicable. This is a pre-release, non-live codebase: there is no production system holding client data.

## Known exposure (25 November 2026)

- The repository is currently **public**, contrary to the rule above. Owner action: make it private.
- `reference/source-html/` (5 files) contains question wording from instruments whose licences are not yet confirmed for STN (ASRS-5, PCL-5, DAST-10, C-SSRS). Making the repository private is the effective remedy: deleting the files now would not remove them from public history. Decide whether they stay in the repository once private and once licences are confirmed.
- Automated checks: no secrets, key files, real client identifiers, real email addresses or phone numbers were found on `main` or the open PR branches on 25 November 2026.
