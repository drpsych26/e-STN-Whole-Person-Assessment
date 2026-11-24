# Safety escalation matrix and crisis contact register

**Status: DRAFT, PENDING CLINICAL APPROVAL.** Nothing in this file is clinically approved. The tiers, acknowledgement windows and resolution codes below are engineering placeholders that make the workflow testable. A registered clinician must review and approve them (record the approval in `docs/clinical/CLINICAL-SIGNOFF-FORM.md`) before any client-facing use.

Implementation: `backend/app/safety_escalations.py`, routes under `/v1/safety-escalations`, schema `backend/app/migrations/*/004_safety_escalations.sql`, tests `backend/tests/test_safety_escalations.py`.

## 1. Tiers

| Tier (code) | Meaning (draft) | Acknowledgement window (placeholder) | Expected response (to be set clinically) |
|---|---|---|---|
| `immediate_emergency` | Immediate danger to life | 5 minutes | Client is told to call 111. STN does not provide an emergency response. Clinician records the action taken. |
| `urgent_assessment` | Needs same-day clinical assessment | 60 minutes | To be defined |
| `increased_concern` | Needs earlier review than planned | 24 hours | To be defined |
| `routine_monitoring` | Monitor at the next planned contact | 7 days | To be defined |

Windows are configurable per deployment with `STN_SAFETY_ACK_MINUTES` (for example `immediate_emergency=5,urgent_assessment=60`). An escalation that is still unacknowledged past its window is shown as **overdue** at the top of the queue.

## 2. Rules the software enforces

1. A positive screening response is not a risk classification. The tier is chosen and recorded by a clinician.
2. Clinicians and reviewers open, acknowledge (take ownership), hand over, and resolve. Admins can see the queue but cannot act on it.
3. Severity is fixed once opened. If concern rises, a new escalation is opened at the higher tier; the earlier one stays on record.
4. Resolution needs a coded outcome and a documentation reference (an assessment of the same client). Free text is not stored.
5. Escalations cannot be deleted, and resolved escalations cannot be reopened or edited (database triggers).
6. Every action, including refused ones, is written to the hash-chained audit log.

## 3. What the software does not do

- **Notifications (engineering only, not live):** opening an escalation queues a content-free notice (no client identity, no clinical detail) to the client record's owning clinician and to any subjects in `STN_SAFETY_NOTIFY_SUBJECTS`. An overdue notice goes out once per escalation. **No provider is approved or configured, so nothing is sent** (`STN_NOTIFY_PROVIDER=disabled`). There is still no paging or phone call, and a sent message doesn't mean anyone has read it. Who is notified, and how fast, is part of D-SAFE-01.
- It does **not** imply that anyone is monitoring the queue. Client-facing text must not say or suggest that STN staff monitor clients continuously unless a staffed roster exists.
- It does **not** cover the period when no clinician is on duty. **Open decision D-SAFE-01:** the owner and the clinical lead must define the out-of-hours pathway (for example, client-facing instruction to call 111 or 1737, plus next-business-day review of anything opened out of hours).

## 4. Open clinical decisions

| ID | Decision needed | Owner |
|---|---|---|
| D-SAFE-01 | Out-of-hours pathway and the client-facing wording for it | Owner + clinical lead |
| D-SAFE-02 | Approve or change the four tiers and their acknowledgement windows | Clinical lead |
| D-SAFE-03 | Approve or change the resolution codes | Clinical lead |
| D-SAFE-04 | Whether the clinician who opened an urgent or emergency escalation may also resolve it alone, or a second clinician must review | Clinical lead |
| D-SAFE-05 | Which assessment items or safety-flag codes should prompt a clinician to open an escalation, and at which tier | Clinical lead |
| D-SAFE-06 | Confirm that client-record disposal stays blocked while an escalation is unresolved (enforced from 25 Nov 2026 as a safe default; the privacy officer and clinical lead may change it) | Privacy officer + clinical lead |

## 5. New Zealand crisis contacts (verified 25 November 2026)

The machine-readable register used by the client crisis panel is `backend/app/data/crisis_resources.json` (component: `frontend/crisis-panel/`). It also lists regional crisis-team numbers transcribed from the Mental Health Foundation directory (June 2026), which a person must check against the PDF before release.

Checked against the Mental Health Foundation helplines directory, Lifeline Aotearoa's own notice of 6 November 2025, and the Health New Zealand HealthEd helplines resource. Re-verify before any release and at least every quarter: these services have changed hours recently.

| Service | Contact | Hours | Notes |
|---|---|---|---|
| Emergency services | 111 | 24/7 | Immediate danger to life |
| 1737 Need to talk? | Call or text 1737 | 24/7 | Trained counsellors |
| Samaritans | 0800 726 666 | 24/7 | One secondary source lists a different number; use the Mental Health Foundation listing |
| Healthline | 0800 611 116 | 24/7 | Health advice |
| Lifeline | 0800 543 354, or text 4357 | **7am to midnight** | **Not 24/7.** Lifeline reduced its hours in 2025 for funding reasons. Many third-party pages still say 24/7. |
| Suicide Crisis Helpline | 0508 828 865 (0508 TAUTOKO) | **7am to midnight** | **Not 24/7.** Run by Lifeline. |

Do not show Lifeline or the Suicide Crisis Helpline as 24/7 services. Overnight, the 24/7 options are 111, 1737, Samaritans and Healthline.

Sources:
- Mental Health Foundation, National helplines: https://mentalhealth.org.nz/get-help-support/helplines-support/national-helplines/
- Lifeline Aotearoa, "Lifeline Aotearoa reduces operating hours due to funding constraints" (6 Nov 2025): https://www.lifeline.org.nz/about-us/news/lifeline-aotearoa-reduces-operating-hours-due-to-funding-constraints
- Health New Zealand HealthEd, Helplines and local mental health services (HE2546): https://healthed.govt.nz/products/helplines-and-mental-health-services
