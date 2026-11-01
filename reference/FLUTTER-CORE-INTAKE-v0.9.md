# Flutter Whole Person Core Intake — v0.9

**Scope:** Part A — 25 Whole-Person Core Intake items from the supplied STN-INITIAL-1.0.0 paper pilot.  
**Environment:** Private development and synthetic-data testing only.  
**Status:** Initial Flutter implementation; CI verification required.

## Implemented

- 25 Part A item wordings copied from the supplied paper-pilot HTML and held in `lib/models/core_intake.dart`.
- Original five-point response scale and response labels.
- Explicit source-version tag: STN-INITIAL-1.0.0.
- Safety-tagged items preserved as items 14, 19, 20, 21, 22, 23 and 24.
- Missing or endorsed safety-tagged items remain visible for human review/clarification.
- No automatic diagnostic score, severity band, safety tier or crisis disposition.
- Interim conservative flag rule: any non-zero response or unanswered safety-tagged Part A item remains unresolved for human review. This is a software safeguard, not a source-approved risk threshold; clinical-owner approval is still required.
- No automatic adaptive routing; the screen explicitly states that routing is not yet implemented.
- Synthetic case IDs only; IDs not beginning with SYNTH- are rejected.
- Simulation acknowledgement required before saving.
- Draft save, reopen and delete using a dedicated encrypted local Hive box.
- No name, date of birth, NHI, contact details or other real patient identifiers are collected in this screen or the synthetic profile screen.
- The legacy profile screen is replaced with SYNTH- case IDs and TESTER- aliases; legacy non-synthetic client profiles are hidden and can be cleared.
- The core intake screen checks for legacy non-synthetic profile data and blocks draft saving until it is cleared.
- Existing MDD/GAD/PTSD/ADHD interim modules require a saved SYNTH- case/TESTER- alias profile, explicit synthetic-data acknowledgement and all module items answered before saving.
- Unit tests for item count, unique numbering, synthetic ID validation, completeness and safety-tag behaviour.
- CI workflows copy this new screen and test into the restored Flutter v4 project before analysis, tests and builds.

## Deliberate exclusions

- PHQ-9 and GAD-7 are not implemented in this screen because written digital-use permissions have not been verified.
- The remaining 183 paper-pilot items are not implemented here.
- Adaptive follow-up selection is not inferred from symptom scores.
- Green/yellow/orange/red/critical routing tiers are not calculated because approved thresholds and response procedures are not evidenced.
- No real patient record, server sync, clinician notification, acknowledged handover, authentication or role-based access is provided.
- The existing four Flutter modules remain separate interim modules and are not represented as the complete assessment.

## Acceptance checks

- [ ] Dart formatting passes.
- [ ] Flutter static analysis passes.
- [ ] Unit/widget tests pass.
- [ ] Android debug build passes.
- [ ] Web release build passes.
- [ ] Manual tablet usability review passes with synthetic data.
- [ ] Independent source fidelity review confirms all 25 items and response labels.
- [ ] Clinical content owner signs off the exact Part A source and safety-tag interpretation.

## Release boundary

This implementation is a private synthetic-data simulation, not an approved patient assessment product. Local encryption does not provide production identity, authorisation, audit, backup, retention or clinical record governance. Do not use it with real patient information or for clinical decisions.
