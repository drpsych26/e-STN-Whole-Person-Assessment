# Review corrections — assessment-demo.REVIEW-CORRECTED.html

Derived from `assessment-demo.html` (zip 02_WEBSITE). Engineering-only changes:

1. Dependency clearing is recursive (defect STN-H01). Changing a parent answer clears all descendants, so withdrawn answers can no longer produce a crisis result.
2. Crisis screen no longer claims automatic webhook escalation (STN-C02). It instructs the user to contact a clinician or on-call person now.
3. Contrast of small brand text and primary button text raised to WCAG AA (STN-M02/M03). Brand tint `#c77dff` requires owner confirmation.
4. `role="main"` on `#app` (STN-M04). Two residual landmark findings remain.

NOT changed (clinical; require registered clinician sign-off): C-SSRS skip logic (C03), Q1 "Yes" → LOW (C04), HIGH risk timing (C05), PCL-5 severity mapping (H02), AUDIT-C cut-offs (M07), instrument licence status (C06), STN-H10 help-line panel.

Canonical v2.6 source is undetermined (STN-H04). This file is a review copy, not a canonical replacement.

## Update
- Help-line panel added to the top of the review copy (STN-H10 engineering part). Clinical sign-off on the crisis pathway is still required.
- INTERIM (unreviewed): C-SSRS floor raised so any Yes to Q1, Q2 or Q3 is at least MODERATE (previously Q1 Yes with Q2 No returned LOW). This is a safety-increasing interim measure. It is not clinical validation and must be confirmed or amended by a clinician on the sign-off form (item C04).
