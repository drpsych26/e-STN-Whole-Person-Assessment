# Immutable audit retention and backup storage (D-18, D-13)

**Status (25 Nov 2026): infrastructure code and export job IMPLEMENTED; NOT DEPLOYED; NOT VERIFIED against Azure.** External immutable retention isn't operational until the steps in section 3 have been carried out and checked.

## 1. What exists

| Piece | Where | Verified |
|---|---|---|
| Write-once storage account: `audit-exports` (append allowed, no rewrite) and `db-dumps` containers, time-based retention, no shared keys, no public network, private endpoint, TLS 1.2+, infrastructure encryption, versioning, soft delete, diagnostics to Log Analytics | `infra/azure/modules/evidence-storage.bicep`, wired in `main.bicep` behind `deployEvidenceStorage` (default **false**) | Bicep 0.49.2 build and lint; conditional deployment checked in the compiled template |
| Export job: verifies the whole hash chain, exports only new events, checks continuity with the previous export, writes create-only, reads back and compares SHA-256, records the export (append-only `audit_exports`) | `backend/app/audit_export.py`, migration 007 | 9 tests on SQLite and PostgreSQL with a local write-once sink: normal export, continuity across three exports, **tampered chain refused**, corrupted read-back refused and not recorded, overwrite refused, append-only register |
| Logical-dump upload with `.sha256` sidecar and read-back check | `python -m app.audit_export --sink azure --store-dump FILE` | Local sink only |
| Azure sink (Blob REST, Entra token, `If-None-Match: *`) | `AzureBlobSink` | Request construction unit-tested; **never run against real storage** |

Retention defaults: audit exports **3650 days** (10 years; the privacy officer must confirm against the Health (Retention of Health Information) Regulations 1996 and STN's retention policy); database dumps **35 days**.

## 2. Failure handling

- Broken chain: nothing is exported or recorded, the job exits 1 and names the first broken event. Treat this as a security incident (incident response plan).
- Write, read-back or continuity failure: nothing is recorded, the job exits 1, and the next run retries the same range. An object left behind by a half-finished run makes the retry fail with "cannot be overwritten" until an operator confirms the object matches and records it. That is deliberate: no silent rewrite.
- Run it on a schedule (for example, daily) and alert on a non-zero exit. **Not scheduled yet**: there's no job runner in the infrastructure.

## 3. Owner and operations steps (blocked on the Azure subscription and cost approval)

1. Approve the cost of a small Standard_ZRS storage account plus a private endpoint (confirm the current price in the Azure pricing calculator for New Zealand North).
2. Set `deployEvidenceStorage = true` (staging first) and run the staging deploy workflow.
3. From the migrate identity, run `python -m app.audit_export --sink azure` against the staging database. Then try to overwrite and delete the exported blob, and confirm both are refused.
4. Run the restore drill, upload the dump with `--store-dump`, then download it and restore from the uploaded copy.
5. **Only after 3–4 pass, and with the privacy officer's agreement on the periods, lock both policies** (Azure portal → storage account → container → Access policy → Lock). **Locking is irreversible:** the period can't be shortened, the policy can't be removed, and the account can't be deleted while retained blobs exist.
6. Record the evidence for release gate G10/G11 (`release/evidence/`).

## 4. Restore procedure from the dump store

1. Download `db-dumps/<yyyy/mm/dd>/<file>` and its `.sha256`; check the digest.
2. Restore into a scratch database (`backend/scripts/backup_restore_drill.sh` steps).
3. Verify: row counts, `python -m app.verify_chain`, `python -m app.rekey --verify-decrypt`.
4. Compare the restored chain's last hash with the latest `audit_exports.last_hash` and the matching exported object. Everything after the dump is recoverable from the audit exports; disposals executed after the restore point must be re-executed (see the backup and restore runbook).
