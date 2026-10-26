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
