# STN crisis panel (D-15): provisional

A dependency-free web component, `<stn-crisis-panel>`, for the client portal and any client-facing page. It shows four tiers: immediate danger (111), urgent mental-health crisis (local crisis team by region), distress (1737, Samaritans, Suicide Crisis Helpline, Lifeline) and routine support.

**Status: provisional, not clinically approved.** The wording and tiers need approval from STN's clinical lead (D-SAFE-01). Regional crisis-team numbers were transcribed from the Mental Health Foundation directory (June 2026) and must be checked against that PDF by a person before release. Northland, Auckland and Tairāwhiti show no number, because the source table was ambiguous; they point to the directory and 111 instead.

## Use

```html
<link rel="stylesheet" href="crisis-panel.css">
<stn-crisis-panel region="canterbury"></stn-crisis-panel>
<script src="crisis-resources.js"></script>
<script src="crisis-panel-model.js"></script>
<script src="stn-crisis-panel.js"></script>
```

- Works under `script-src 'self'` (no inline scripts or handlers, no `innerHTML`). See `index.html`.
- The data is bundled, so the panel never waits on the API. It remembers only the chosen **region** in this browser; nothing personal is stored.
- It says plainly that STN is not an emergency service, that messages are not monitored around the clock, and that sending one does not contact emergency services.

## Changing contact details

1. Edit `backend/app/data/crisis_resources.json` (the single source of truth; the API serves it at `GET /v1/public/crisis-resources`).
2. Run `python tools/export_crisis_resources.py` to regenerate `crisis-resources.js`.
3. Run `node tests/crisis-panel.test.js` and the backend tests. The validator refuses to list Lifeline or the Suicide Crisis Helpline as 24/7, requires hours on every contact, and requires 111 first.
4. Update `verified_on` only after actually checking each source.

## Verification done (25 Nov 2026)

- Node scenario tests (`tests/crisis-panel.test.js`) and backend tests (`test_crisis_resources.py`).
- Headless Chrome at 1280px and 390px: correct tier order, `tel:111` first, region switching and recall, no CSP violations, no console errors, no horizontal overflow, **axe-core WCAG 2.1 A/AA: 0 violations**.

Not done: a Flutter version for the Android app (Flutter isn't available in this build environment), and clinical approval.
