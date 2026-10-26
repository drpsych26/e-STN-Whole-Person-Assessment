# Verification attempt record — 26 October 2026

**Disposition: NOT RELEASE-READY. Private development only. Do not use with real clients.**

This record captures checks actually executed in the available runtime. It deliberately separates passing static checks from tests that could not be run.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Safety-reviewed Flutter ZIP archive integrity | PASS | `unzip -t STN_Diagnostic_Tool_Flutter_MVP_Pack_v4_SAFETY_REVIEWED.zip` reported no errors. |
| Flutter project manifest presence | PASS | Extracted package contains `pubspec.yaml`; project name `supportive_therapy_network`, SDK constraint `>=3.3.0 <4.0.0`. |
| Dart source inventory | OBSERVED | 16 Dart files and 1 `*_test.dart` file in the extracted package. Inventory is not compilation. |
| Inline JavaScript syntax in local HTML references | PASS | Node v22.16.0 `node --check` passed for 4 non-empty inline scripts across v2.5, v2.6, paper pilot and the two named Whole Person Assessment HTML variants. The paper pilot contained no inline script to check. |
| Flutter/Dart formatter, analyzer, dependency resolution, unit tests and build | NOT RUN / BLOCKED | `flutter` and `dart` executables are not available in this runtime. No successful Flutter CI run or build artifact was verified. |
| Clinical Core v2 item/rule traceability | BLOCKED | Complete approved canonical source and independent row-by-row mapping are not evidenced. |
| Safety escalation/handover end-to-end test | BLOCKED | No operational escalation service, acknowledged handover, delivery receipt, timeout/fallback integration or clinician-approved protocol has been verified. |
| Authentication and server-side RBAC | BLOCKED | A local profile and device-side encrypted storage do not establish production identity, server-side authorisation or multi-user clinical record security. |
| NZ privacy/licensing/clinical review | OPEN | The checklist exists; qualified sign-off and instrument-specific permissions are not evidenced. |
| Independent validation and supervised pilot approval | OPEN | No independent validation report or signed go/no-go approval is evidenced. |

## Reproducible local commands still required in a Flutter-enabled CI environment

Run from the Flutter project root using a pinned, supported Flutter SDK and record the exact SDK version and CI run URL:

```bash
flutter --version
dart format --output=none --set-exit-if-changed .
flutter pub get
flutter analyze
flutter test --reporter expanded
flutter build apk --debug
```

If iOS distribution is in scope, build and validate it on an appropriately configured macOS runner. A debug build is not a production release artifact. Before any release build, run dependency/licence and secret scans, security tests, signed-artifact checks, accessibility/usability checks, and the complete approved clinical test suite.

## Release decision

No public deployment or real-client use is authorised by this verification record. The user's permission to proceed does not substitute for objective build evidence, clinical governance approval, instrument permissions, privacy/security controls, or independent validation. Do not collect identifiable health information in the prototype.

**Overall: NOT COMPLETE — PRIVATE DEVELOPMENT ONLY — RELEASE HOLD.**
