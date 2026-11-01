# STN v0.6.1+7 — Incoming Release Candidate Intake

**Recorded:** 1 November 2026  
**Package:** `STN_Whole_Person_Assessment_v0.6.1_RC.zip`  
**Package version:** `0.6.1+7`  
**Archive inventory:** 49 entries; 349,800 bytes  
**Status:** Incoming release candidate — not verified, not integrated, not live.

## Operating decision

- General development hold: **LIFTED**.
- Engineering and maintenance work: **ACTIVE**.
- Product/release state: **PRIVATE / NOT LIVE**.
- Production deployment, public launch, external beta, clinical use, identifiable client data and production credentials: **NOT AUTHORISED**.
- Synthetic test data only.

Lifting the development hold does not waive CI, peer-review, clinical, privacy, security or organisational approval gates.

## Package evidence

The supplied archive contains Flutter source, tests, release documentation and reference HTML. Its readiness record states that Flutter compilation, static analysis and tests were not run in its authoring environment. Treat it as an incoming candidate, not a verified release.

Do not relabel the current repository as v0.6.1. Preserve provenance and reconcile the archive against current repository history and newer pull-request work before importing or replacing files.

## Active actions

1. Reconcile the supplied archive with the current repository, preserving originals and newer implementation work.
2. Complete PR #7 and PR #9 checks; continue PR #12 as a draft until its required checks pass.
3. Complete Flutter source-to-spec traceability and scoring/routing golden tests.
4. Continue safety workflow, identity/RBAC, backend persistence, audit, privacy/security, backup/recovery and governance implementation.
5. Update changelog, verification records and release-gap register only when supported by commits and test evidence.
6. Keep builds and artifacts internal-only.

## Upload status

This intake record is committed to the repository. The binary ZIP archive itself is **not attached or committed by this record**; it must not be represented as uploaded until a repository asset or commit containing the archive is available.

## Related tracking

- Consolidated action and release-gate register: [Issue #1](https://github.com/drpsych26/e-STN-Whole-Person-Assessment/issues/1)
- Repository remains private. No release or deployment is initiated by this intake record.
