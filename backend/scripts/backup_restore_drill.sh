#!/usr/bin/env bash
# STN backup/restore drill: pg_dump -> restore into a scratch database -> verify.
#
# Verifies, on the restored copy:
#   1. every public table has the same row count as the source;
#   2. the audit hash chain recomputes end to end (python -m app.verify_chain);
#   3. when a data key is configured, every stored payload decrypts and every
#      submitted/signed-off assessment still matches its content hash
#      (python -m app.rekey --verify-decrypt).
# The scratch database is dropped afterwards unless STN_DRILL_KEEP=1.
#
# Required:  STN_DATABASE_URL   source database (postgresql://user:pass@host:port/db)
# Optional:  STN_PG_BIN           directory holding pg_dump/pg_restore/psql. Default: the
#                                 /usr/lib/postgresql/<server major>/bin install when present,
#                                 otherwise PATH. Client and server major versions must match:
#                                 a newer pg_dump writes settings an older server rejects on restore.
#            STN_DRILL_SCRATCH_DB  scratch database name (default stn_restore_drill)
#            STN_DRILL_DUMP_DIR    where to write the dump (default: a temp dir, removed)
#            STN_DATA_KEY / STN_DATA_KEYS + STN_DATA_ACTIVE_KEY_ID  enable the decrypt check
# Run from backend/ with the API package installed (pip install -e ".[postgres]").
# Synthetic data only until the production gates are signed; see
# docs/operations/BACKUP-AND-RESTORE-RUNBOOK.md for the production procedure.
set -euo pipefail

: "${STN_DATABASE_URL:?STN_DATABASE_URL (source database) is required}"
SCRATCH_DB="${STN_DRILL_SCRATCH_DB:-stn_restore_drill}"
if [[ ! "$SCRATCH_DB" =~ ^[a-z_][a-z0-9_]{0,62}$ ]]; then
  echo "STN_DRILL_SCRATCH_DB must be a plain lower-case identifier" >&2
  exit 2
fi

url_with_db() {
  python3 -c 'import sys, urllib.parse as u; p = u.urlsplit(sys.argv[1]); print(u.urlunsplit(p._replace(path="/" + sys.argv[2])))' "$1" "$2"
}
SOURCE_DB="$(python3 -c 'import sys, urllib.parse as u; print(u.urlsplit(sys.argv[1]).path.lstrip("/"))' "$STN_DATABASE_URL")"
if [[ "$SOURCE_DB" == "$SCRATCH_DB" ]]; then
  echo "Scratch database must differ from the source database" >&2
  exit 2
fi
ADMIN_URL="$(url_with_db "$STN_DATABASE_URL" postgres)"
SCRATCH_URL="$(url_with_db "$STN_DATABASE_URL" "$SCRATCH_DB")"

WORK="${STN_DRILL_DUMP_DIR:-$(mktemp -d)}"
cleanup() {
  if [[ "${STN_DRILL_KEEP:-0}" != "1" ]]; then
    psql "$ADMIN_URL" -q -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $SCRATCH_DB" >/dev/null 2>&1 || true
  fi
  if [[ -z "${STN_DRILL_DUMP_DIR:-}" ]]; then rm -rf "$WORK"; fi
}
trap cleanup EXIT

echo "== tools"
server_num="$(psql "$STN_DATABASE_URL" -At -c "SHOW server_version_num")"
server_major=$((server_num / 10000))
if [[ -n "${STN_PG_BIN:-}" ]]; then
  PG_BIN="${STN_PG_BIN%/}/"
elif [[ -x "/usr/lib/postgresql/${server_major}/bin/pg_dump" ]]; then
  PG_BIN="/usr/lib/postgresql/${server_major}/bin/"
else
  PG_BIN=""
fi
client_major() { "${PG_BIN}$1" --version | sed -E 's/^[^0-9]*([0-9]+).*/\1/'; }
dump_major="$(client_major pg_dump)"
restore_major="$(client_major pg_restore)"
echo "server: PostgreSQL ${server_major} (${server_num})"
echo "pg_dump: $("${PG_BIN}pg_dump" --version)  [${PG_BIN:-PATH}]"
echo "pg_restore: $("${PG_BIN}pg_restore" --version)"
if [[ "$dump_major" != "$server_major" || "$restore_major" != "$server_major" ]]; then
  echo "Client/server major version mismatch: pg_dump ${dump_major}, pg_restore ${restore_major}, server ${server_major}." >&2
  echo "Install postgresql-client-${server_major} or set STN_PG_BIN to its bin directory." >&2
  exit 2
fi

echo "== 1/4 dump source (custom format)"
DUMP="$WORK/stn-$(date -u +%Y%m%dT%H%M%SZ).dump"
"${PG_BIN}pg_dump" --format=custom --no-owner --no-privileges --file "$DUMP" "$STN_DATABASE_URL"
sha256sum "$DUMP"

echo "== 2/4 restore into scratch database $SCRATCH_DB"
psql "$ADMIN_URL" -q -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $SCRATCH_DB" -c "CREATE DATABASE $SCRATCH_DB"
"${PG_BIN}pg_restore" --no-owner --no-privileges --exit-on-error --dbname "$SCRATCH_URL" "$DUMP"

echo "== 3/4 compare row counts"
mismatch=0
tables="$(psql "$STN_DATABASE_URL" -At -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")"
if [[ -z "$tables" ]]; then
  echo "Source database has no tables; nothing to verify" >&2
  exit 1
fi
for table in $tables; do
  src="$(psql "$STN_DATABASE_URL" -At -c "SELECT count(*) FROM \"$table\"")"
  dst="$(psql "$SCRATCH_URL" -At -c "SELECT count(*) FROM \"$table\"")"
  printf '%-22s source=%-6s restored=%-6s %s\n' "$table" "$src" "$dst" "$([[ "$src" == "$dst" ]] && echo ok || echo MISMATCH)"
  [[ "$src" == "$dst" ]] || mismatch=1
done
[[ "$mismatch" == "0" ]] || { echo "Row counts differ after restore" >&2; exit 1; }

echo "== 4/4 verify restored copy"
STN_DATABASE_URL="$SCRATCH_URL" python -m app.verify_chain
if [[ -n "${STN_DATA_KEY:-}${STN_DATA_KEYS:-}" ]]; then
  STN_DATABASE_URL="$SCRATCH_URL" python -m app.rekey --verify-decrypt
else
  echo "No data key configured: decrypt check skipped"
fi
echo "Backup/restore drill passed."
