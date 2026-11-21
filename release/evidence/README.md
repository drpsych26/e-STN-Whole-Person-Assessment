# Release gate evidence

Each file is a JSON list of evidence records, one per gate result, for a single release commit:

```json
[
  {"gate_id": "G01", "commit": "<40-char sha>", "artifact_ref": "<URI of the report>",
   "outcome": "pass", "recorded_by": "<tester>", "recorded_on": "YYYY-MM-DD"}
]
```

`outcome` must be `pass` or `fail`. A gate passes only with a passing record for the exact release
commit. Evidence is not created by the platform's own build: each record must point to an independent
artifact (test report, penetration-test certificate, clinical sign-off, and so on).

`empty.json` is an empty list. It is the input for the workflow's dry run, which must report every gate
as BLOCKED until real evidence is committed.
