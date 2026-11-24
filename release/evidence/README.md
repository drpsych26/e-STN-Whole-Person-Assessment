# Release gate evidence (G01–G13)

`current.json` holds the evidence for the next release candidate. It is a JSON list; each record is one piece of evidence for one gate and one exact commit:

```json
{
  "gate_id": "G10",
  "kind": "restore_drill_report",
  "commit": "<40-character release commit SHA>",
  "artifact": "release/evidence/artifacts/2026-12-01-staging-restore.pdf",
  "artifact_sha256": "<sha256 of that file>",
  "outcome": "pass",
  "recorded_by": "<person who recorded it>",
  "recorded_on": "YYYY-MM-DD",
  "approver": {"name": "...", "role": "operations_lead", "organisation": "...", "registration_id": "clinical approvals only"}
}
```

Rules the engine enforces (`backend/app/release_gates.py`):

- Each gate needs specific evidence kinds and approval roles; see the gate table in the generated dashboard.
- Evidence lives on `main`, never in the candidate commit (a commit cannot name its own hash). The candidate must already be on `main`.
- An artifact in the repository must exist in the `main` checkout that holds the evidence and match `artifact_sha256`. An external artifact must be an `https://` URL with the document's SHA-256; the engine reports that it could not verify it.
- An approval names the approver, their role and organisation, and points to the signed record as its artifact. The approver cannot be the person who recorded it. Clinical approvals need a professional registration identifier, which a person must check on the public register.
- G08 must be performed by an organisation independent of STN. G13 stays blocked until G01–G12 pass.
- A `fail` record for the commit fails the gate.
- Synthetic CI runs and self-declared "done" statements are not release evidence for G04–G13. Evidence for those gates comes from the accountable people and environments named in each gate.

Do not put identifiable client information in artifacts. Store confidential documents (signed sign-offs, penetration-test reports) in the controlled evidence store and record them here by `https://` URL and SHA-256.

Run: `cd backend && python -m app.release_gates --commit <sha> --evidence ../release/evidence/current.json --format markdown`
