# Stage 2 design: assessment engine

**Status:** design only. No implementation has started. Proposed for independent review before any code.

## 1. Scope
Server-side assessment definitions, scoring, missing-data handling, completion tracking, clinical review and an audit trail for every step. Covers the instruments named in the implementation directive: PHQ-9, GAD-7, PCL-5, ASRS-5, AUDIT-C, DAST-10, K10, WHODAS 2.0 and C-SSRS, plus the whole-person intake.

## 2. Instrument licensing (blocker)
- Each instrument has a licence record: owner, licence type, permitted uses (clinical, research, commercial), territory, expiry, and the written confirmation reference.
- An instrument cannot be activated for clinical use until its licence record is `confirmed` with a written reference. The application refuses to create an assessment session for an unlicensed instrument.
- Clinical item C06 (instrument licence and permission status) remains open until every instrument has a confirmed record. This design does not assume any licence.

## 3. Versioning
- Each definition is immutable once published: `instrument_code`, `version`, `items` (text, response options, reverse-scored flags), `scoring_rules`, `cutoffs`, `published_by`, `published_at`, `content_sha256`.
- A session records the exact definition version it was administered with. Changing a definition creates a new version; old sessions keep their version.
- Publication requires the clinical review step (section 6). Unpublished versions cannot be administered.

## 4. Scoring
- Scoring runs on the server, from stored item responses, using the rules in the definition. Client-side scores are never stored as results.
- Each scoring rule is a pure function with unit tests, including boundary values for every cut-off.
- Reverse-scored items and subscales are defined in the definition, not in code.
- Results are decision support only. They never produce a diagnosis (directive section 3.2).

## 5. Missing data and completion
- Each item has `answered`, `skipped` or `not_applicable`. Skipped items are never silently scored as zero.
- A rule per instrument states the minimum answered proportion for a total score. Below that, the score is `not_scorable` and the reason is recorded.
- C-SSRS and the safety items are never treated as missing: an unanswered safety item blocks completion and raises an escalation task.
- Completion tracking: `not_started`, `in_progress`, `completed`, `abandoned`, `escalated`. Transitions are audited. Partial sessions remain resumable within a stated window.

## 6. Clinical review
- Scores and definitions require review by a registered clinician who is not the author. The reviewer's decision is recorded per item: approve, amend or reject.
- Review outcome is a precondition for `published` (definitions) and `clinically_reviewed` (results).
- Diagnostic checklists remain decision support until a clinician records a diagnostic decision in the clinical record.

## 7. Safety interplay
- C-SSRS responses above the defined threshold create an escalation record in the safety module (Stage 3). The record needs acknowledgement and resolution with timestamps (D-016).
- Escalation is not a notification alone: the record is the source of truth and must be visible in the clinician queue.

## 8. Data model (new migration `0004`)
- `instruments` (code, name, licence_status, licence_reference, owner)
- `instrument_versions` (instrument_code, version, content_json, content_sha256, status, reviewed_by, published_at)
- `assessment_sessions` (id, client_record_id, instrument_code, instrument_version, status, started_at, completed_at, started_by)
- `item_responses` (session_id, item_code, response_code, state, recorded_at)
- `assessment_results` (session_id, scale, raw_score, scorable, reason, computed_at, computed_from_version)
- `clinical_reviews` (target_type, target_id, reviewer, decision, reference, recorded_at)

Client-content columns follow the client-record encryption pattern (AES-256-GCM, associated data bound to the record). Response values are encrypted; codes and states are not.

## 9. API (versioned, under `/v1/assessments`)
- `GET /v1/assessments/instruments`: list confirmed instruments only.
- `POST /v1/assessments/sessions`: start a session for an assessable client (owner or assigned clinician).
- `PUT /v1/assessments/sessions/{id}/responses`: record responses, server-side validation of codes and ranges.
- `POST /v1/assessments/sessions/{id}/complete`: compute results; refuses when mandatory items are unanswered.
- `GET /v1/assessments/sessions/{id}/results`: results with their definition version.
- `POST /v1/assessments/versions/{id}/review`: clinical review, not by the author.

## 10. Testing plan
- Unit: every scoring function with boundary and invalid inputs; reverse scoring; missing-data rules.
- Golden tests: scoring against published worked examples from each instrument's documentation, with the source cited in the test. Where the source is unavailable, the test is marked UNVERIFIED and cannot close a gate.
- Property tests: scores within the valid range for any response combination.
- Integration: session lifecycle, version pinning after a new version is published, licence refusal, review separation.
- Security: authorisation per route, encryption of response content, audit on each transition.

## 11. Acceptance for Stage 2
- Every implemented instrument has a confirmed licence record and a clinician-reviewed published version.
- Every scoring rule has golden tests with cited sources.
- No result is produced for an unlicensed or unreviewed instrument.
- Gates affected: G04 (clinical workflows), G05 (scoring verified). Neither closes without independent evidence.

## 12. Open questions for the reviewer
1. Who is the clinical reviewer for definitions, given the owner is also the developer? The independence requirement in the go-live gate applies.
2. Which instrument versions are licensed for the intended use (clinical, supervised pilot, public)?
3. Should the whole-person intake be versioned separately from the standardised instruments?
