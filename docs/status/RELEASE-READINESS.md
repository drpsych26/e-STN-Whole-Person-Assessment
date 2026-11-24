# Release readiness

Updated 25 Nov 2026. The authoritative, evidence-derived dashboard comes from the release-gate engine (PR #60): `cd backend && python -m app.release_gates --commit <sha> --evidence ../release/evidence/current.json --format markdown`. The evidence file is empty, so **every gate is BLOCKED**. That is correct.

| Gate | Domain | State | What's missing |
|---|---|---|---|
| G01 Backend complete | Technical | Blocked | Release candidate not chosen; CI run + test report as evidence |
| G02 Customer onboarding verified | Technical | Blocked | Client UI; UAT with a live IdP |
| G03 Auth and permissions verified | Security | Blocked | Live Entra tenant; security-lead approval |
| G04 Clinical workflows validated | Clinical | Blocked | Clinician UAT; clinical-lead approval |
| G05 Assessment scoring verified | Clinical | Blocked | Instrument activation and approval (PHQ-9/GAD-7 engine ready) |
| G06 Safety escalation verified | Clinical | Blocked | D-SAFE-01..05; notification provider |
| G07 Privacy review | Privacy | Blocked | Privacy impact assessment; privacy officer |
| G08 Independent pen test | Security | Blocked | Independent tester |
| G09 Critical/high defects closed | Security | Blocked | See defect register (O-1, O-2, D-06, D-13, D-18) |
| G10 Backup and restore verified | Deployment | Blocked | Real staging restore |
| G11 Production infrastructure validated | Deployment | Blocked | Azure subscription; deployment |
| G12 Clinical governance approval | Clinical | Blocked | Clinical lead |
| G13 Final release authorisation | Release | Blocked | G01–G12; owner |

**Technical readiness doesn't imply clinical readiness.** The public website is separate and stays live regardless.
