# Crisis panel and safety escalation

**Status:** Backend escalation workflow built and tested (synthetic data). Crisis panel content register built. The on-screen panel is **not built** in this pass. Clinical review of the content and pathway is **not done**. Release status is unchanged: NOT CLINICALLY SIGNED OFF; NOT CLIENT READY.
**Register items:** D-015 (crisis panel absent from builds), D-016 (escalation display-only).

## 1. Principle

A telephone number on a screen is not a safety pathway (reviewer finding E). The pathway has four parts, and all four must work before any client-facing assessment is authorised:

1. **Immediate resources** that show whether or not the person is signed in, and whether or not the API is reachable.
2. **A recorded escalation** that a clinician owns, acknowledges and resolves.
3. **Visibility** so that unresolved escalations are seen by clinical staff, with an overdue flag.
4. **Documented resolution** that cites a real client record and a coded outcome.

## 2. Immediate resources (crisis panel)

- Content lives in `backend/app/crisis_resources.py`. Each entry has a verified contact, hours, and an hours note where sources conflict.
- Served by `GET /v1/safety/crisis-resources`, which is public and unauthenticated.
- The on-screen panel must embed the same content in the release build, not fetch it, so that a display never depends on the API. This is a requirement for the panel build; it is not yet implemented.
- Numbers verified against the Mental Health Foundation helplines directory (updated June 2026) and corroborating government and agency pages on 21 November 2026:
  - 111 emergency services
  - 1737 Need to talk? (call or text, 24/7)
  - Lifeline 0800 543 354, text 4357
  - Suicide Crisis Helpline 0508 828 865, text 0508 TAUTOKO. **Hours unresolved**: sources list both 24/7 and 7am to midnight.
  - Samaritans 0800 726 666 (24/7)
  - Healthline 0800 611 116 (24/7)
- Lifeline's hours also conflict between sources (7am to midnight in one listing, 24/7 in another). Both are marked unresolved and must be confirmed with the service before release.
- `PANEL_STATUS.clinically_reviewed` is `False`. The panel must not be released with that flag set to `False`.

## 3. Escalation record

Table `safety_escalations` (migration `0005`). Append-only: rows cannot be deleted, and the opening facts (subject, source, severity, opened_at, opened_by) cannot change.

| Field | Meaning |
|---|---|
| `status` | `open` → `acknowledged` → `resolved` |
| `source` | `crisis_panel`, `assessment_item`, `clinician_report`, `manual` |
| `severity` | `urgent`, `high`, `routine` |
| `opened_at`, `opened_by` | Who raised it and when. A person may open one about themselves. |
| `acknowledged_at`, `acknowledged_by` | The clinician who took ownership. Only clinical roles may acknowledge. |
| `resolved_at`, `resolved_by` | Only the acknowledging clinician may resolve. |
| `resolution_code` | One of five coded outcomes. Free text is not accepted. |
| `documentation_record` | A client record the resolving clinician owns. |

## 4. Ownership and roles

- Opening: a person about themselves, or clinical staff about anyone. Opening is not blocked by provisional registration.
- Acknowledging and resolving: clinical roles only (`authorised_clinician`, `clinical_supervisor`, `clinical_director`).
- The acknowledging clinician owns the escalation. A different clinician cannot resolve it.
- **Gap:** there is no allocation of an escalation to a named clinician at opening. Assignment from the subject's team is not built, so an unacknowledged escalation has no named owner until someone takes it. This is open (D-024).

## 5. Unresolved-case visibility

- `GET /v1/safety/escalations/unresolved` lists unresolved escalations for clinical staff only, oldest first.
- An escalation still `open` after **15 minutes** (`OVERDUE_MINUTES`) is flagged `overdue`.
- The threshold is a provisional engineering value. It must be set by the clinical reviewer.
- **Gap:** no push, SMS or email notification to on-call staff exists. Visibility depends on staff polling the list. This is open (D-025) and must be solved before client-facing release.

## 6. Audit

Every open, acknowledge, resolve and refused attempt is written to the hash-chained audit trail with allow-listed detail (source, severity, resolution code). No free text and no client content is audited.

## 7. What is not built

- The on-screen crisis panel in any build (D-015).
- Notification of on-call staff (D-025).
- Automatic assignment of an escalation to a clinician (D-024).
- A clinical policy on what counts as a safety concern from an assessment item. This comes from Stage 2 and requires the clinical reviewer.
- Clinical review of the resource list, the overdue threshold and the escalation pathway.
- Testing with live staff and live telephone services.

## 8. Limitations stated plainly

- The API cannot check on the person, call anyone, or contact emergency services. The panel and the escalation record support human action; they do not replace it.
- If the database is unavailable, the escalation cannot be recorded. The panel must still show the resources. Failure to record is therefore a serious operational risk, and it is open until an alerting path exists.

## 9. Acceptance criteria before any client-facing assessment

1. Clinical reviewer approves every resource entry, the hours status and the overdue threshold.
2. Panel content is embedded in the release build and displays with the API stopped (tested).
3. Notification to on-call staff is implemented and tested end to end.
4. A tabletop exercise with clinical staff walks through an urgent escalation from opening to documented resolution.
5. Each resource is confirmed by the owning service in writing or by its published contact channel.
