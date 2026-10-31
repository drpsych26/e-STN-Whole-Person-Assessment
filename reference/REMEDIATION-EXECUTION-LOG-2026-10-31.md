# STN remediation execution log — 31 October 2026

## Repository and branch
- Repository: `drpsych26/e-STN-Whole-Person-Assessment`
- Repair branch: `fix/fail-closed-flutter-ci-gate`
- Pull request: #4 — Restore Flutter v4 source and enforce real CI verification
- Release state: private development only; release hold remains active.

## Confirmed defects repaired in this branch
1. The original Flutter CI silently skipped validation when the Flutter source was missing. The workflow now requires the source archive and fails closed.
2. The original Flutter archive is preserved as an encoded source asset and checked against its expected SHA-256 before extraction.
3. The generated Flutter widget test referenced `MyApp`, but the actual app widget is `STNApp`. The test suite now targets the real application.
4. The widget test attempted to find an off-screen save button without scrolling. It now scrolls the assessment list to the control.
5. Test imports now use the actual package name from the supplied `pubspec.yaml`.
6. The scoring engine previously applied generic severity bands and had unsafe default criteria behaviour. It now produces a descriptive response sum only, never claims diagnosis/criteria, rejects unknown/cross-module/duplicate questions and flags incomplete or designated review responses for clinician review.
7. The Flutter screen previously prevented incomplete assessments from being saved, making the incomplete-response safety rule unreachable through the UI. It now allows an explicitly flagged incomplete draft.
8. Secure-storage startup failures now disable assessment access instead of allowing the app to continue in an uncertain persistence state.
9. Stored encryption-key length and profile record shape are validated. Profile and result persistence/export errors are surfaced to the user.
10. Re-saving profiles previously generated new UUIDs. Existing client and clinician IDs are now preserved; required names and date format are checked.
11. Report export exceptions and corrupted profile data in result detail are handled without crashing the screen.
12. Flutter UI/report terminology now distinguishes descriptive response sums, unassessed diagnostic criteria and clinician-review flags from validated scores, diagnoses or risk dispositions.
13. The browser prototype now gates progression on saved client consent, complete screening, completed safety responses, clinician review and saved care plan. Unanswered safety items cannot be treated as negative.
14. Browser report fields are escaped, safety flags are restricted to known question IDs, downstream reviews are invalidated when upstream answers change, and storage failures are surfaced.
15. A Node-based synthetic-data browser workflow regression test has been added to CI.

## CI evidence
- Static-quality checks passed on commit `86dd504` and subsequent run at `b17ef05` is in progress.
- Prototype inline JavaScript syntax checks passed.
- Prototype synthetic workflow regression tests passed in GitHub Actions.
- The Flutter restore step succeeded.
- Earlier Flutter analysis runs exposed test-import and missing-`Scrollable` defects; those were corrected. A fresh CI run at the current head is required to establish the final analyzer, unit/widget test and build result.
- Android debug APK and web release build are not yet claimed as passing.

## Outstanding release blockers
- Full Whole Person Initial Assessment is not implemented by the Flutter v4 module MVP.
- Full source reconciliation across paper pilot, Clinical Core v2, HTML versions and Flutter modules.
- Approved instrument permissions and question-by-question clinical traceability.
- Clinician-approved safety event state machine, acknowledgement, escalation, fallback and operational handover.
- Production identity, role-based authorisation, multi-tenant separation, secure backend persistence, append-only audit, key lifecycle, backup and recovery.
- NZ privacy/security assessment, PIA, retention/disposal, access/correction, breach response and independent security testing.
- Independent clinical validation, accessibility, device/browser end-to-end testing, supervised UAT and signed governance approval.

## Release decision
**NOT APPROVED FOR CLINICAL OR PRODUCTION USE.** Use synthetic data only. No real client data and no public deployment. Passing software CI is necessary technical evidence, not clinical validity, safety, privacy compliance or production approval.
