# STN project status (authoritative)

**Updated:** 25 November 2026, 06:00 NZDT · **Release status:** not clinically signed off, not client ready, production clinical release NOT AUTHORISED.

Companion registers in this folder: `DEFECT-REGISTER.md`, `SECURITY-REGISTER.md`, `CLINICAL-DEPENDENCIES.md`, `RELEASE-READINESS.md`, `DEVELOPMENT-HANDOVER.md`. The Stage 1 audit record is `docs/security/STAGE-1-AUDIT-2026-11-25.md`.

## 1. Platform surfaces

| Surface | State | Evidence |
|---|---|---|
| Public website (supportivetherapy.network) | **Live over HTTP.** HTTPS presents a `*.github.io` certificate and HTTP isn't redirected (owner action). Live site still shows Lifeline as 24/7 and serves an unapproved draft privacy notice until website #14/#15 merge | HTTP 200 checked 25 Nov; axe 0 violations on the #15 branch |
| App repository | **Public** (owner action O-1 to make private) | GitHub API |
| Client portal | API only: invitation, claim, onboarding status, acknowledgements, own assessment metadata (#63). No UI. Crisis panel component ready (#66) | 18 + 9 tests |
| Clinician portal | API: client records, assessments, review/sign-off, safety flags and escalations, registration self-submission, scoring (#70). Flutter app has optional clinician sign-in (off by default). No web UI | Backend suite |
| Administrator portal | API: account registry, reviewer assignment, legal holds, disposal, client-account status, registration attestation, notification outbox. No UI | Backend suite |
| Assessment engine | Clinician prototypes (HTML, strict CSP #67). Server-side PHQ-9/GAD-7 scoring, inactive by default (#70) | 32 tests; browser run |
| Crisis panel | Component and public register built, **provisional** (#66) | Node + browser + axe |
| Backend | FastAPI, PostgreSQL 16 / SQLite (tests), Redis rate limits, audit chain, export, request ids | **500 passed, 4 skipped** at #70 head |
| Notifications | Outbox and retries built; **no provider; nothing is sent** (#64) | 20 tests |
| Infrastructure | Bicep for staging/production; evidence storage behind a flag (off). **Nothing deployed; no Azure subscription in use** | Bicep build + lint |

## 2. Open pull requests (merge order)

App repository (`drpsych26/e-STN-Whole-Person-Assessment`). Stacked PRs retarget automatically as their base merges.

| Order | PR | Branch | Content | CI |
|---|---|---|---|---|
| 1 | #59 | `fix/stage1-audit-remediation` | Stage 1: action pinning, workflow guard, hosted-DB guard, safety escalations, prototype CSP, API headers, disposal block | 11/11 |
| 2 | #62 | `fix/android-release-least-privilege` (on #59) | A-03 Android workflow least privilege | 5/5 |
| 2 | #67 | `fix/prototype-strict-csp` (on #59) | D-11 no inline handlers, hash-pinned script-src | 5/5 |
| 2 | #63 | `feature/identity-onboarding` (on #59) | D-07/D-08 identity events, client accounts, registration attestation | 11/11 |
| 3 | #64 | `feature/notifications` (on #63) | Notification outbox, escalation notices | 9/9 |
| 4 | #66 | `feature/crisis-panel` (on #64) | D-15 crisis panel (provisional) | 9/9 |
| 5 | #68 | `feature/immutable-audit-retention` (on #66) | D-18/D-13 evidence storage (off) and export job | 11/11 |
| 6 | #69 | `feature/observability` (on #68) | Request ids, structured logs | 9/9 |
| 7 | #70 | `feature/server-side-scoring` (on #69) | PHQ-9/GAD-7 scoring (inactive) | see PR |
| 8 | this PR | `docs/status-registers` (on #70) | These registers | — |
| any | #60 (draft) | `feature/release-gates` (on main) | G01–G13 engine and dashboard | 10 + 1 skipped |
| — | #61 | `docs/status-update-2026-11-25` | Another session's go-live-gate note | not reviewed here |
| never | #52 | `feature/stage1-corrections` | Reference only. **Do not merge.** Close after this stack lands | — |

Website repository (`drpsych26/STN-Website`): **#14** (helpline hours; safety-critical) then **#15** (publish only public files, SEO, 404, PR validation). Both green.

## 3. Status scale

Not started · In progress · Implemented · Verified (tests executed in this environment) · Blocked · Requires owner action · Requires clinical approval · Requires external dependency. "Verified" never means clinically approved or deployed.
