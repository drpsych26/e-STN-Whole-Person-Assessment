# STN private HTML preview and release status

**Status: PRIVATE DEVELOPMENT PREVIEW ONLY — NOT APPROVED FOR REAL-CLIENT USE.**

A standalone interactive HTML preview is available for internal interface review. It uses synthetic demo content, has no network calls or persistent storage, and does not implement secure clinical record management. Its JavaScript syntax check passed in the available runtime; its ZIP package passed integrity verification.

## Not completed or approved
- Flutter formatter, dependency resolution, analyzer, unit/widget/integration tests and build are not verified; Flutter/Dart were unavailable in the execution runtime.
- Complete Clinical Core v2 source-to-code traceability is not evidenced.
- Human safety escalation and clinician handover are illustrative, not operational.
- Authentication, server-side role-based access and secure clinical-record backend are not implemented in the HTML preview.
- NZ privacy, clinical governance, instrument permissions and independent security review need qualified review and sign-off.
- Independent clinical validation and written supervised-pilot approval have not been obtained.
- Copyright ownership/assignment to STN Limited has not been verified; see the IP checklist.

## Release gates
1. Verify chain of title and execute required IP assignments/licences.
2. Confirm approved clinical source and instrument rights; complete 100% traceability.
3. Implement and test secure authentication, server-side authorisation, protected persistence and audit.
4. Implement and test clinician-led escalation, acknowledgement, timeout, alternate routing and outage behavior.
5. Run pinned Flutter CI: formatter, dependency resolution, analyzer, tests, builds, dependency/licence/secret scans and signed artifact checks.
6. Complete NZ privacy impact assessment, clinical governance and independent security review.
7. Obtain independent clinical validation and signed supervised-pilot go/no-go approval.
8. Review pilot outcomes before broader release.

No public deployment or real-client use is approved by this document.