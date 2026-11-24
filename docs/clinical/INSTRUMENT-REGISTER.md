# Assessment instrument register

**Status (25 Nov 2026):** server-side scoring is implemented for PHQ-9 and GAD-7 only. **No instrument is activated** (`STN_ACTIVE_INSTRUMENTS` is empty by default). Activation is a clinical-governance decision (release gate G05) and needs the clinical lead's approval.

| Instrument | Licence (verified 25 Nov 2026) | Scoring implemented | Notes |
|---|---|---|---|
| PHQ-9 | "No permission required to reproduce, translate, display or distribute" (PHQ Screeners) | Yes: total 0–27; bands at 5/10/15/20 (Kroenke, Spitzer & Williams 2001) | Item 9 above 0 → `clinician_review_required` flag (not a risk classification) |
| GAD-7 | Same statement (PHQ Screeners) | Yes: total 0–21; bands at 5/10/15 (Spitzer et al. 2006) | — |
| PCL-5 | To be confirmed (US National Center for PTSD) | No | — |
| ASRS-5 | Commercial-use terms to be confirmed | No | Flagged in STN's clinical principles |
| AUDIT-C | Licence and NZ version to be confirmed | No | The paper pilot found a shared-scale bug; each item needs its own options |
| DAST-10 | Commercial-use terms to be confirmed | No | Flagged in STN's clinical principles |
| K10 | Licence and NZ norms to be confirmed | No | — |
| WHODAS 2.0 | WHO permission required | No | — |
| C-SSRS | Licence and training requirements to be confirmed | No | — |

Engineering rules (`backend/app/scoring.py`, tests `test_scoring.py`):

- No item wording is stored in the scoring engine; items are ids only. Display text lives with the approved assessment content.
- Responses must be integers 0–3; anything else is refused.
- **Missing items: no total and no band** (no prorating). This is STN's conservative default, pending clinical approval, not a published rule.
- Every result carries the citation and the statement that it is a screening result, not a diagnosis.
- Scoring is stateless; each call writes an audit event (instrument and outcome only).

Tests check every band boundary against the published cut points (PHQ-9: 0, 4, 5, 9, 10, 14, 15, 19, 20, 27; GAD-7: 0, 4, 5, 9, 10, 14, 15, 21). These are synthetic worked examples, not a clinical validation study.
