# Development handover

Session of 25 Nov 2026 (04:56–06:10 NZDT). Next session: start here.

## Start-of-session checks

1. `git fetch`; compare each PR head in `PROJECT-STATUS.md` §2 with GitHub. Merged PRs retarget their children automatically. If a base was squash-merged, rebase each child onto `main` with `git rebase --onto origin/main <old-base-head>`.
2. Test environment: PostgreSQL 16 and Redis locally. Run `STN_TEST_DATABASE_URL=… STN_REQUIRE_PG_TESTS=1 STN_TEST_REDIS_URL=… STN_REQUIRE_REDIS_TESTS=1 python -m pytest` from `backend/`. Expected at the top of the stack: **500 passed, 4 skipped**.
3. Repo checks: `node tests/*.test.js`, `python tools/static_quality_check.py`, `python tools/check_workflow_security.py`, `python tools/prototype_strict_csp.py --check`, `python tools/export_crisis_resources.py --check`, Bicep build and lint.

## Migrations by PR (apply in order)

004 safety escalations (#59) → 005 identity/onboarding (#63) → 006 notifications (#64) → 007 audit exports (#68).

## Next engineering steps (in order)

1. After the owner merges: rebase any remaining stacked PRs, re-run the full suite on `main`, close #52 as superseded.
2. Done in #72: pip-audit and Bandit in CI. Keep `bandit-baseline.json` for reviewed findings only.
3. Client portal UI (web): sign-in, invitation claim, onboarding checklist, acknowledgements, own assessments, crisis panel embed, notification preferences. Uses the #63/#64/#66 APIs.
4. Clinician and admin web UI for safety escalations, client-account activation, registration attestation and the notification dead-letter view.
5. Flutter: port the crisis panel to a widget (needs a Flutter toolchain), wire client sign-in.
6. Assessments: persist instrument scores against assessments (currently stateless) once activation is approved.
7. Notification provider adapter (Azure Communication Services) once a provider and sender domain are approved; schedule `python -m app.notifications --dispatch --scan-overdue` and `python -m app.audit_export --sink azure`.
8. Identity-event relay (Azure Function + custom authentication extension) or the token-claim alternative, once Entra decisions are made.

## Environment limitations this session

- No Flutter/Android SDK: the Android workflow change (#62) was checked statically only.
- GitHub settings APIs (Pages, repo visibility) are blocked through this session's proxy, and visibility changes are refused by session policy.
- No Azure or Entra access: all cloud integration is code, IaC and tests with synthetic fixtures.
