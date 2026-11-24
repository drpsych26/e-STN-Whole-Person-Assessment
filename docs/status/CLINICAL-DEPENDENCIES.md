# Clinical dependencies (decisions engineering must not make)

Updated 25 Nov 2026. Each item needs an appropriately registered New Zealand clinical lead (and, where noted, the privacy officer). Engineering has built the controls with clearly marked placeholders; none of these is approved.

| ID | Decision | Where the placeholder lives | Default until decided |
|---|---|---|---|
| D-SAFE-01 | Out-of-hours pathway; who is notified of escalations and how fast; client-facing crisis wording | `SAFETY-ESCALATION-MATRIX.md`, `crisis_resources.json`, `STN_SAFETY_NOTIFY_SUBJECTS` | Owning clinician + configured roster; panel marked provisional |
| D-SAFE-02 | Escalation tiers and acknowledgement windows | `STN_SAFETY_ACK_MINUTES` | 5 min / 60 min / 24 h / 7 days (placeholders) |
| D-SAFE-03 | Resolution codes | `safety_escalations.py` | 6 draft codes |
| D-SAFE-04 | Whether the opener may resolve an urgent/emergency escalation alone | — | Allowed |
| D-SAFE-05 | Which assessment answers prompt an escalation and at which tier | — | Clinician judgement only |
| D-SAFE-06 | Disposal blocked during unresolved escalation (privacy officer too) | `governance.py` | Blocked |
| C-01 | Activate PHQ-9 / GAD-7 scoring for clinical use (gate G05) | `STN_ACTIVE_INSTRUMENTS` | None active |
| C-02 | Missing-item rule for scored instruments | `scoring.py` | No total if any item missing |
| C-03 | PHQ-9 item 9 handling beyond "clinician review required" | `scoring.py` | Flag only |
| C-04 | Licences for PCL-5, ASRS-5, AUDIT-C, DAST-10, K10, WHODAS 2.0, C-SSRS | `INSTRUMENT-REGISTER.md` | Not implemented |
| C-05 | Human check of regional crisis-team numbers against the MHF June 2026 PDF; confirm Northland, Auckland and Tairāwhiti numbers | `crisis_resources.json` | Marked "check before relying" / not shown |
| C-06 | Approve the Whole Person Initial Assessment content version and paper-pilot outcome | clinical docs | Prototype only |
| C-07 | Clinical governance approval for any release (gates G04, G05, G06, G12) | `release/evidence/` | Blocked |
