# STN human safety escalation and handover — requirements

**Status:** Design specification; not implemented or clinically approved. Do not use as a live crisis protocol.

## Non-negotiable principles

- A total symptom score must never clear or downgrade a safety concern.
- Missing, declined, unclear, contradictory or technically unavailable safety information is not a negative response.
- A software flag is not a clinical risk assessment and cannot determine crisis disposition.
- Urgent actions require an accountable human; the system must not imply that a notification was delivered or accepted unless delivery/acknowledgement is confirmed.
- If a clinician is unavailable or the service is offline, the system must display approved local emergency/support instructions and record that operational handover is unresolved. STN must verify those instructions before activation.

## Required status model

For each designated safety item, persist the response state separately from any clinical interpretation:

- positive
- negative
- uncertain
- declined
- missing
- not_present_in_this_instrument
- not_yet_reviewed

Do not collapse these values into a single boolean. Preserve raw answer, item/instrument version, timestamp, respondent, and clinician clarification.

## Required event lifecycle

1. **Trigger:** designated safety response is positive, uncertain, declined or missing; conflicting answers; or a clinician manually raises a concern.
2. **Create case:** create a uniquely identified review event linked to the assessment version. Record trigger source and timestamp.
3. **Assign owner:** assign to an authenticated, authorised clinician/role according to an approved roster and service operating hours.
4. **Notify:** deliver through an approved channel. Record attempt, delivery result and timestamp. A failed or unconfirmed delivery must not count as handover.
5. **Acknowledge:** clinician authenticates and explicitly accepts ownership. Record identity, timestamp and status.
6. **Assess and act:** clinician conducts the approved assessment, documents contact attempts, findings, actions, rationale and disposition within scope.
7. **Escalate:** if acknowledgement or action deadline expires, route to the approved alternate/on-call owner. If all routes fail, trigger the documented operational fallback and clearly show unresolved status.
8. **Handover:** outgoing and incoming accountable people, time, accepted responsibility, outstanding actions and confirmation are recorded.
9. **Close:** only an authorised clinician can close the event with rationale and completed required fields. Original trigger and events remain auditable.
10. **Review:** incident/near-miss and failed notification events are reviewed under clinical governance.

## Minimum data and controls

- event ID; client/assessment reference; instrument/version/item ID; response state; trigger rule version
- assigned clinician/role; assignment time; notification attempts/results; acknowledgement; escalation steps
- contact attempts; clinician assessment/action/disposition; handover acceptance; closure author/time/reason
- append-only audit events; access control; time synchronisation; alert delivery monitoring
- outage mode and safe fallback; retries/idempotency; duplicate alert prevention without suppressing meaningful events

## Required tests

- positive, uncertain, declined and missing response; contradictory responses; manual clinician concern
- high total symptom score with negative safety item and low total score with positive safety item
- unavailable assigned clinician, no acknowledgement, failed notification, expired session and reassignment
- network outage, offline entry, delayed sync, duplicate submission, concurrent edits and recovery
- unauthorised user attempts to view, acknowledge, reassign or close a case
- incomplete handover, rejected handover, unresolved event and audit history tampering attempt

## Release gate

This specification is not an operational crisis protocol. Before use, STN's clinical governance lead must approve clinical thresholds and response times, staffing coverage, escalation contacts, service hours, after-hours coverage, emergency wording, training, incident management and the fallback procedure. A security engineer must test identity, authorisation, delivery, audit integrity and resilience. An independent clinical reviewer must sign the acceptance record.