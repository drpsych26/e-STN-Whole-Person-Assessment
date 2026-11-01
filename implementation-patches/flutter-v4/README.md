# Applying the Flutter v4 safety patch

This directory tracks the key source patch and tests separately from the full review ZIP supplied in the ChatGPT conversation.

## Files

- `lib/logic/scoring_engine.dart` — conservative replacement for the MVP scoring engine.
- `test/scoring_engine_test.dart` — unit tests for conservative behaviour and invalid inputs.
- Full review copy ZIP: `STN_Diagnostic_Tool_Flutter_MVP_Pack_v4_SAFETY_REVIEWED.zip` was generated in the project conversation; it also updates the module UI, results history, report language and README.

## Application

1. Preserve an untouched copy of the original v4 archive.
2. Extract the review ZIP and inspect the diff before adopting it.
3. Copy the replacement `lib/logic/scoring_engine.dart` and test file into the Flutter project. Ensure the test import package name matches `pubspec.yaml` if the package name changes.
4. Run `dart format .`, `flutter pub get`, `flutter analyze`, `flutter test`, and a clean build on a pinned Flutter SDK. Retain logs and artifact hashes.
5. Resolve all failures before considering the patch integrated.

## Critical caveat

These changes reduce unsupported claims; they do not make the app clinically valid or safe for client use. The question sets are not verified as licensed/validated instruments, and the full human safety escalation workflow, authentication, role-based access, backend record integrity, audit, privacy/security assessments and clinical approval remain outstanding. Flutter/Dart commands have not been run in the current execution environment. Release remains HOLD; synthetic data only.

## Whole Person Core Intake v0.9

- `lib/screens/whole_person_initial_assessment_screen.dart` — Part A's 25 source-worded core items, synthetic-only case ID guard, draft save/reopen/delete and human-review flags for the paper-pilot safety-tagged items.
- `test/whole_person_intake_rules_test.dart` — item count, synthetic ID, completeness and safety-tag regression tests.
- `lib/storage/secure_hive.dart` — dedicated encrypted local Hive box for synthetic core-intake drafts.
- `lib/screens/home_screen.dart` — adds the Whole Person Initial Assessment entry point.
- `lib/screens/profiles_screen.dart` — replaces name/DOB/contact fields with SYNTH- case IDs and TESTER- aliases; legacy profiles are not displayed and can be cleared.

Both GitHub Flutter verification workflows copy the new screen and tests into the restored v4 project. This is Part A only; the other 183 paper-pilot items, adaptive routing and all clinical/governance gates remain open. Synthetic data only.
