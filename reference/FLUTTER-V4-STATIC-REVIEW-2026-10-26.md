# Flutter v4 source review — release-blocking findings

**Review type:** static source inspection of the supplied `STN_Diagnostic_Tool_Flutter_MVP_Pack_v4.zip` on 26 October 2026.  
**Result: FAIL for clinical production readiness.** This is not a full compile, runtime test, penetration test, or clinical validation.

## Scope inspected
- `pubspec.yaml`
- `lib/main.dart`
- `lib/storage/secure_hive.dart`
- `lib/logic/scoring_engine.dart`

## Findings

### F-01 — Local-only profiles are not authentication or access control (BLOCKER)
The v4 README describes basic client and clinician profiles. The inspected application starts directly at `HomeScreen` and the storage class keeps a single `active_client` and `active_clinician`. No authentication, session verification, role enforcement, account lifecycle, or server-side authorisation is demonstrated by these files. A profile record must not be treated as proof of the identity or authority of the person using the app.

**Required closure:** implement and test an approved identity/session model and server-side role enforcement for any multi-user clinical service. Until then, do not use identifiable client information.

### F-02 — Generic severity sum and thresholds are not a validated instrument score (BLOCKER)
`ScoringEngine.score` converts each answer severity to a number, sums all provided answers, then applies generic total-score bands (8/18/28). The inspected code does not establish that these thresholds belong to any specific validated instrument or authorised version. Missing answers are not explicitly handled in the score path shown.

**Required closure:** remove generic diagnostic-seeming thresholds unless each one is traced to an authorised instrument and validated scoring rule. Add explicit completeness/missingness handling and golden tests based on approved Clinical Core v2 sources. Preserve raw responses separately from computed scores and clinician interpretation.

### F-03 — Safety flags are hard-coded to question IDs and severity bands (BLOCKER)
`_riskRules` maps a small set of question IDs to severity thresholds, returns `false` for other module IDs, and returns a boolean only. The inspected function does not itself initiate or verify human escalation, record acknowledgement, handle uncertain/missing responses, or define unavailable-clinician behavior. A false result must not be presented as proof of safety.

**Required closure:** map every safety item and response against the approved safety protocol; model positive, uncertain, declined and missing responses distinctly; require a human action/acknowledgement workflow; test interruption, offline and unavailable-clinician scenarios. Never infer risk status from the overall score.

### F-04 — Non-MDD criteria gating defaults to true (BLOCKER)
`_criteriaGating` returns `true` for every module except MDD. That value can be mistaken for criteria having been met even though module-specific criteria have not been evaluated.

**Required closure:** return an explicit status such as `not_assessed` or `not_implemented` for unsupported modules; do not treat an unimplemented gate as positive evidence. Add module-by-module acceptance tests.

### F-05 — Device-local encryption is not a complete clinical-record security design (BLOCKER)
The storage class uses Hive encryption with a key kept in platform secure storage. This is useful device-side protection, but does not by itself provide authenticated users, server-side permissions, shared-record integrity, audit events, controlled exports, revocation, retention/disposal, backup/recovery, or an approved clinical system of record.

**Required closure:** define and threat-model the intended deployment; implement the full record lifecycle and security controls; test key lifecycle, logout/device sharing, backup/restore and export controls. Obtain qualified security and privacy review.

### F-06 — Build and automated tests are not evidenced (OPEN)
The supplied archive has a `pubspec.yaml` and Flutter source, but this review did not run `flutter pub get`, `flutter analyze`, tests, or a device/browser build because Flutter/Dart SDKs were not available in the execution environment.

**Required closure:** run those commands in pinned CI; attach logs and artifacts. Static source inspection is not a build pass.

## Release disposition
**HOLD — private development and synthetic data only.** The findings above must be fixed and independently retested. Clinical scoring, instrument permissions, source traceability, privacy impact assessment, NZ clinical governance, security testing and release approval remain separate required gates. Do not represent this MVP as a validated diagnostic tool or use it for real-client assessment.