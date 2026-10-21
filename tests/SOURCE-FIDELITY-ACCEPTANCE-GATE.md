# Source-fidelity acceptance gate

This is a blocking checklist for the STN Whole Person Initial Assessment. A passing browser demo is not evidence that the approved source has been imported.

## Required source assets

- [ ] `reference/stn-whole-person-assessment-v2.6.html` — approved digital assessment source
- [ ] `reference/STN_Initial_Assessment_Paper_Pilot.html` — paper-pilot source
- [ ] `flutter/STN_Diagnostic_Tool_Flutter_MVP_Pack_v4.zip` — Flutter technical baseline
- [ ] `flutter/STN_Diagnostic_Tool_Flutter_MVP_Coding_Pack.zip` — coding pack
- [ ] Source hashes recorded and independently checked against the supplied originals

## Exact-match checks

- [ ] Compare source HTML bytes or SHA-256 hashes against the supplied originals.
- [ ] Confirm all clinical question text, response options, question order, scale definitions, scoring, cut-offs, safety flags and adaptive routing remain unchanged.
- [ ] Confirm the approved screenshots match the rendered phone and tablet layouts.
- [ ] Check all navigation paths, validation, save/resume behaviour, report generation and print/export.
- [ ] Check keyboard and screen-reader basics and responsive layout.
- [ ] Run automated tests and a manual clinical safety walkthrough; record results and defects.

## Release blockers

Do not label the app production-ready, clinically validated, or approved for live client data until every required gate has evidence and a named reviewer. A prototype demonstration is not clinical validation. Do not enter real client information into the demo.
