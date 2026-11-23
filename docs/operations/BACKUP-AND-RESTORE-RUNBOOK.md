# STN API — backup and restore runbook

**Status: draft procedure; non-live; synthetic data only.** This runbook covers the STN API PostgreSQL database. It is not evidence that production backups exist or that a production restore has been tested. Those are release gates in `docs/release/PRODUCTION-GO-LIVE-GATE.md`. Hosting assumptions follow `docs/infrastructure/AZURE-PRODUCTION-SUBSCRIPTION-AND-DEPLOYMENT.md`.

## 1. What must be recoverable

| Item | Where it lives | Notes |
|---|---|---|
| Records, workflow state, consents, holds, disposals, export log, audit chain | PostgreSQL (`STN_DATABASE_URL`) | One database; every table is in the `public` schema and created by `backend/app/migrations/postgres/` |
| Data keys | Key Vault secrets (`STN_KEYVAULT_KEY_IDS`) or the deployment's secret store | **A database backup is useless without the keys that encrypted it.** Key backup and soft-delete/purge protection are part of this runbook |
| Configuration | App Service settings / infrastructure as code | Identity provider, organisation claim, MFA evidence, retention period, rate limits |

The audit chain is platform-wide and hash-linked. A restore must bring back the whole `audit_events` table. Restoring part of it breaks verification, and that is the intended behaviour.

## 2. Backup layers (production, to be provisioned)

1. **Managed automated backups.** Azure Database for PostgreSQL Flexible Server automated backups with point-in-time restore, retention set by the approved schedule. New Zealand North is a non-paired region, so geo-redundant backup must not be assumed or enabled without privacy and legal approval of the data flow.
2. **Logical dumps.** A scheduled `pg_dump --format=custom` to storage in New Zealand North with immutability (time-based retention lock) and restricted access. This gives an independent, portable copy and is what the drill below verifies.
3. **Key backup.** Key Vault soft-delete and purge protection on; the key ids in use recorded in the change log at every rotation (`python -m app.rekey --status-only`). Old keys stay in the vault until no backup still within retention needs them.

RPO and RTO targets, backup retention, restore ownership and test frequency are owner decisions that are still open. Record them here once approved.

## 3. The restore drill (engineering check)

`backend/scripts/backup_restore_drill.sh` runs the same steps as a real restore, against a scratch database on the same server:

1. `pg_dump --format=custom` of the source database, and its SHA-256.
2. Create the scratch database and `pg_restore --exit-on-error` into it.
3. Compare row counts for every table in the source and the restored copy.
4. Recompute the audit chain on the restored copy (`python -m app.verify_chain`).
5. If a data key is configured, decrypt every stored payload and re-check every content hash (`python -m app.rekey --verify-decrypt`).
6. Drop the scratch database (set `STN_DRILL_KEEP=1` to keep it for inspection).

CI runs it on every backend change against synthetic data from `backend/scripts/seed_synthetic_data.py`.

```sh
cd backend
export STN_DATABASE_URL='postgresql://<user>:<password>@<host>:5432/<database>'
export STN_DATA_KEYS='<key-id>:<key>'  STN_DATA_ACTIVE_KEY_ID='<key-id>'   # optional: enables step 5
bash scripts/backup_restore_drill.sh
```

## 4. Production restore procedure (draft)

1. **Declare** the incident and record who authorised the restore, why, and the target point in time.
2. **Freeze writes:** stop the API instances or put them in maintenance mode so the source does not change during recovery.
3. **Restore to a new server** with point-in-time restore (or `pg_restore` from the logical dump) in New Zealand North. Never restore over the live server.
4. **Verify the restored server** before switching to it:
   - `python -m app.verify_chain` returns `"ok": true`;
   - `python -m app.rekey --verify-decrypt` returns `"failed": 0` with the production keyring;
   - row counts match the expected state, and the latest audit event time is at or before the target point.
5. **Switch** `STN_DATABASE_URL` (Key Vault reference) to the restored server and restart the API.
6. **Reconcile** anything written after the restore point: the audit log, export log and disposal records show what happened. Disposals executed after the restore point must be re-executed. A disposed record must not come back to life because of a restore.
7. **Record** the outcome in the incident log. Assess whether the Privacy Act 2020 notifiable privacy breach rules apply (for example, data loss or unauthorised access), with the privacy officer.

## 5. Drill schedule and evidence

- Engineering: every backend CI run (synthetic data).
- Staging: before go-live and after every schema migration, using a staging copy and the staging keyring.
- Production: at the approved frequency, restoring to a separate server. Keep the drill output (dump hash, row counts, chain and decrypt results), who ran it, and the date as release evidence.

## 6. Open items (owner decisions)

- RPO/RTO, backup retention and storage location, as approved by the privacy officer and legal adviser.
- Disaster-recovery design for a non-paired region (second New Zealand location or not).
- Who may request and authorise a restore, and how disposed records are protected from reappearing.
- Key escrow and the retention of old keys relative to backup retention.
