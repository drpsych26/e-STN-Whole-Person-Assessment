# STN post-merge engineering verification

**Verification date:** 31 October 2026  
**Repository:** `drpsych26/e-STN-Whole-Person-Assessment`  
**Default branch:** `main`  
**Verified merge commit:** `d201460086919f4a0fdf7a9bbb7584bb4f7069dd`  
**Release state:** Private development only — synthetic data only — release hold.

## Merge record

Repair PR #4 was merged into `main` on 31 October 2026:
https://github.com/drpsych26/e-STN-Whole-Person-Assessment/pull/4

## Post-merge GitHub Actions evidence

All jobs and steps completed successfully on the merge commit:

| Workflow | Run ID | Result |
|---|---:|---|
| STN verification | 41170645743 | PASS |
| STN Flutter web validation | 41170645724 | PASS |
| STN static quality checks | 41170645676 | PASS |

### Verified checks

- Prototype inline JavaScript syntax.
- Synthetic-data browser workflow regression tests.
- Follow-up assessment save/restore, report escaping and storage-failure tests.
- Flutter v4 source archive restoration and SHA-256 integrity.
- Flutter dependency resolution.
- Dart formatting.
- Flutter static analysis.
- Flutter unit and widget tests.
- Flutter web release build.
- Android debug APK build and artifact upload.

Flutter SDK configured by CI: 3.24.5.

## Android debug artifact

- Artifact name: `stn-flutter-v4-debug-d201460086919f4a0fdf7a9bbb7584bb4f7069dd`
- Artifact ID: `13031137407`
- Artifact digest: `sha256:c55b305f4a2734de531ce78cec640c5c70ad3a38c09c85dd82d067779b30813c`
- Contains: `app-debug.apk`
- Artifact size: approximately 89.9 MB (ZIP); APK approximately 90.8 MB.
- Created: 31 October 2026.
- Retention expiry: 7 November 2026.
- Intended use: internal synthetic-data testing only. It is not a signed production release.

## Defects addressed by the merged repair

1. Flutter CI no longer silently skips when the Flutter source archive is absent.
2. Original Flutter v4 archive is reconstructed and checked against its SHA-256 before extraction.
3. Widget tests now target the actual `STNApp` widget and scroll to off-screen controls.
4. Flutter package imports match the supplied package name.
5. Interim scoring no longer applies generic severity bands or claims diagnostic criteria.
6. Duplicate, unknown, cross-module and malformed question-set inputs are rejected.
7. Incomplete responses and designated review items remain clinician-review flags.
8. Incomplete drafts can be saved without treating unanswered items as negative.
9. Secure-storage initialisation failure blocks assessment access.
10. Stored encryption key and profile/result structures receive basic validation.
11. Profile identifiers are preserved when profiles are re-saved.
12. Persistence and report export errors are surfaced.
13. Browser prototype progression is gated by intake, consent, screening, safety, clinician review and care-plan completion.
14. Browser report output is escaped; stale downstream reviews are invalidated when upstream answers change.
15. Browser and follow-up smoke tests run in CI.

## Known warnings / maintenance follow-up

The successful CI logs include a non-fatal Flutter web icon-font warning referring to CupertinoIcons, and GitHub Actions warned that several workflow actions were still running on Node.js 20. A separate maintenance PR (#7) was opened to upgrade checkout, setup-node, setup-python and upload-artifact to Node.js 24-compatible releases. Do not merge that maintenance PR until its own CI checks pass.

## Scope limitations — not resolved by software CI

- The supplied HTML versions, paper-pilot sources and Flutter v2/v3 packs have not all been imported and reconciled in the repository.
- The Flutter v4 application remains a four-module MVP, not the complete Whole Person Initial Assessment workflow.
- Exact approved paper-pilot / Clinical Core v2 source authority and clinical-owner sign-off are outstanding.
- Instrument permissions and question-by-question clinical traceability are outstanding.
- The human safety event state machine, clinician assignment, notification delivery, explicit acknowledgement, escalation, fallback and audit process are specified but not implemented/approved as a live service.
- Production identity, server-side authorisation, tenant/client isolation, secure backend persistence, tamper-evident audit, key lifecycle, backup and recovery are outstanding.
- NZ privacy review, PIA, independent security review, clinical validation, accessibility/cultural safety review, supervised UAT and signed pilot approval are outstanding.

## Release decision

**NOT APPROVED FOR IDENTIFIABLE CLIENT DATA, CLINICAL USE, PILOT USE OR PUBLIC/PRODUCTION DEPLOYMENT.**

Use synthetic data only until every applicable clinical, privacy, security and organisational gate has documentary evidence and formal approval. A passing build proves only that the configured engineering checks passed on the identified commit; it does not prove clinical validity, legal compliance or production readiness.
