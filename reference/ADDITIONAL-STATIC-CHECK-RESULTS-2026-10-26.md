# STN additional static checks — 26 October 2026

This report records checks actually performed in the working environment. It does not replace a browser/device run, Flutter build, or clinical acceptance test.

## Checks run

### HTML/JavaScript source syntax
Used Node.js `node --check` against every inline JavaScript block extracted from these local uploaded HTML files:
- `stn-whole-person-assessment-v2.5.html`
- `stn-whole-person-assessment-v2.6.html`
- `Supportive Therapy Network — Whole Person Initial Assessment.html`
- `Supportive Therapy Network — Whole Person Initial Assessment (2).html`

**Result:** all non-empty inline script blocks passed JavaScript syntax checking. The paper pilot contains no inline script blocks. This checks syntax only, not DOM behavior, calculations, routing, persistence or correctness.

### Browser execution attempt
Attempted to open the v2.6 HTML in the available headless Chromium environment. The execution environment returned an organisation-policy blocked page for both local file and localhost URLs. The assessment itself did not load; therefore no claim of browser runtime success is made.

### Flutter source inspection
Inspected the ZIP directory structures and Dart source-level feature markers in v2/v3/v4. Flutter and Dart SDK executables are not installed in the current environment, so `flutter pub get`, analyzer, unit tests, emulator launch and APK/web build could not be run. The v4 README identifies itself as an MVP scaffold and explicitly lists authentication, role-based access, audit trails, consent capture and instrument validation as production additions.

## Findings that block release

1. The private repository README confirms that the original supplied reference HTML and Flutter packs have not yet been imported to the repository.
2. The current repository browser demo is explicitly illustrative, uses browser `localStorage`, and is not secure clinical record storage.
3. The inspected browser demo's workflow is incomplete against Clinical Core v2: it does not demonstrate a complete adaptive-routing/selected-instrument flow or a governed diagnostic decision-support stage.
4. The inspected browser demo displays a finalised/draft status but the reviewed code does not expose a finalisation action that sets the finalised flag or provides immutable finalisation/addendum controls.
5. User-entered values are inserted into report/result markup through `innerHTML` without a general HTML-escaping function. This is an injection risk even for a prototype and must be corrected before the UI is used with any sensitive data.
6. In the inspected browser demo, client values are saved under properties such as `name`, while generic restore logic maps object keys directly to element IDs (e.g. `name` does not map to `clientName`). Client fields therefore may not restore correctly after reload. This requires a targeted persistence regression test and fix.
7. The v2.5/v2.6 HTML references `/runtime-config.js` and `manifest.webmanifest`; those runtime assets were not present in the local root inventory inspected. Behavior in the intended hosting environment remains unverified.
8. The Flutter v4 pack is a scaffold with dependencies that need SDK resolution and target-platform validation. Source-level marker checks cannot establish that the Dart project compiles or that encrypted storage is configured correctly.
9. Clinical Core v2 requires human-led safety follow-up and escalation for positive/uncertain safety answers; a screen that merely labels a response is not proof that an operational escalation workflow exists.

## Required test evidence before release

- [ ] Original source files imported with provenance and SHA-256 manifest.
- [ ] Browser and Flutter builds complete successfully in supported environments.
- [ ] Exact question wording, response options, item order, per-item scales, scoring, cutoffs and routing traced to approved sources and licensing reviewed.
- [ ] Tests cover all safety responses, uncertain/unanswered cases, protective factors, clinician acknowledgement, escalation documentation and return to assessment.
- [ ] Injection/XSS tests pass; user content rendered safely.
- [ ] Persistence tests pass across reload, offline operation, interrupted sync and conflict recovery.
- [ ] Role permissions, audit events, controlled amendments/addenda and finalisation immutability pass tests.
- [ ] Accessibility and phone/tablet usability checks complete.
- [ ] Privacy/security review, retention/disposal, incident response and backup/restore are approved.
- [ ] Clinical governance sign-off, supervised pilot and equity/adverse-impact review are documented.

## Current disposition

**HOLD — private development only.** Syntax checks passed for the local HTML scripts; runtime and clinical behavior remain unverified. Do not enter real or identifiable client data and do not publish or deploy this prototype.
