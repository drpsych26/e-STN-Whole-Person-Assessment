# STN Whole Person Assessment — production deployment checklist

## Required before real-client use
- [ ] Approved hosting environment and data-residency/processing position.
- [ ] Authenticated clinician access with MFA.
- [ ] Role-based access control.
- [ ] Managed database with encryption at rest.
- [ ] TLS in transit and secure secret management.
- [ ] Client record model and assessment persistence.
- [ ] Consent/privacy notice workflow.
- [ ] Immutable audit events for access, edits, exports and sign-off.
- [ ] Safety escalation to a human workflow.
- [ ] Server-side validation and scoring regression suite.
- [ ] Backup and restore testing.
- [ ] Retention/disposal workflow.
- [ ] Access/correction workflow.
- [ ] Security/penetration testing.
- [ ] Incident response plan.
- [ ] Instrument licensing/permission review.
- [ ] Clinical governance approval.
- [ ] UAT on desktop, tablet and mobile.

## Go-live gate
Do not enable identifiable clinical persistence merely because the web frontend works. Production activation occurs only after security, privacy, clinical governance and UAT gates are signed off.

## Prototype status
The current browser demo uses local browser storage and illustrative screening questions. It is not a production clinical record system and does not implement secure authentication, backend persistence, audit trails, or clinically validated scoring.
