# Clinical sign-off record — STN Whole Person Assessment

Status until completed: **NOT CLINICALLY SIGNED OFF. NOT CLIENT READY.**

Record status (updated 19 November 2026): a clinical sign-off is reported as held privately under a reference ID (CR-01), available on written request. The decision values for items C05, H02, M07 and C06 have NOT been received in this repository. Until those values are recorded here, no clinical item is closed and the assessment remains not client ready.

Complete one decision per item. Attach the signed copy to the repository record. Registration details and signature are kept in the private governance file, not in public documents.

Clinician name / role / registration body and number: ____________________________
Scope of review (instruments, modules, routes reviewed): ____________________________
Date: ____________

| Ref | Item | Decision (Approve / Amend / Reject) | Required change, if any | Clinician initials |
|---|---|---|---|---|
| C03 | C-SSRS: always ask Questions 1 and 2 | | | |
| C04 | Q1 = Yes, Q2 = No returns LOW | | | |
| C05 | HIGH risk response timing and on-call procedure | | | |
| H02 | PCL-5 severity mapping and provisional cut-off | | | |
| M07 | AUDIT-C cut-offs (sex-specific) | | | |
| C06 | Instrument licence and permission status | | | |
| H10 | Crisis resources panel in every build | | | |
| H09 | Thresholds (8/18/28) applied to 9–10 item scales | | | |

Clinical conditions for release (if any): ____________________________

Signature: ____________________   Date: ____________

---

## Record of governance decisions

**Senior management sign-off for clinical rollout and deployment:** reference ID270993, dated 19 November 2026, 21:24 (NZ time). Recorded as provided by the owner-operator.

**What this record is:** management approval to proceed with rollout and deployment.

**What this record is not:** clinical sign-off. It does not close any item in the table above. The clinical items (C03, C04, C05, H02, M07, C06, H10, H09) remain open until a registered clinician records a decision for each item.

**Current status:** NOT CLINICALLY SIGNED OFF. NOT CLIENT READY.

---

## Clinician-recorded decisions (pending independent review)

Recorded 21 November 2026 from a clinician's completed form (form dated 20 November 2026 as written). These decisions are the clinician's own. They are not independently reviewed and do not change the release status.

**Release status: NOT CLINICALLY SIGNED OFF. NOT CLIENT READY.** This section does not close any item in the decision table above until an independent clinical reviewer has reviewed it, as required by `docs/release/PRODUCTION-GO-LIVE-GATE.md`.

| Ref | Item | Clinician decision (as recorded) | Status |
|---|---|---|---|
| C03 | C-SSRS: always ask Questions 1 and 2 | Approve | Pending independent review |
| C04 | Q1 = Yes, Q2 = No returns LOW | Approve | Pending independent review |
| C05 | HIGH risk response timing and on-call procedure | Approve | Pending independent review; the escalation route is not yet tested (see `reference/SAFETY-ESCALATION-HANDOVER-REQUIREMENTS.md`) |
| H02 | PCL-5 severity mapping and provisional cut-off | Approve | Pending independent review |
| M07 | AUDIT-C cut-offs (sex-specific) | Approve | Pending independent review |
| C06 | Instrument licence and permission status | Approve | **Open: written licence confirmation for each instrument has not been provided** |
| H10 | Crisis resources panel in every build | Approve | Pending independent review |
| H09 | Thresholds (8/18/28) applied to 9-10 item scales | Approve | Pending independent review |

Other details as recorded on the form:

- **Scope:** recorded as "latest instruments, modules, routes reviewed". This is not specific enough to identify what was approved. The scope must list each instrument, module and route by name.
- **Version:** recorded as "latest version". A commit hash or tag is required before this can be relied on.
- **Use:** public release ticked by the clinician. This is recorded as the clinician's stated choice, not as an approval of release.
- **Clinical conditions for release:** none recorded.
- **Clinician registration and signature:** held in the private governance file, not in this repository.

**Still required before any item can be closed:**

1. Independent clinical review of each decision, recorded on the reviewer form.
2. Written licence confirmation for each instrument (C06).
3. A specific scope and version identifier.
4. The non-clinical gates in the production go-live gate: clinician sign-in, a tested HIGH-risk escalation route, NZ privacy review (Health Information Privacy Code 2020, Privacy Act 2020), and independent penetration testing.
