#!/bin/sh
# STN API container entrypoint.
#   STN_PROCESS_ROLE=api (default)  serve the API (app.main)
#   STN_PROCESS_ROLE=migrate        apply migrations and runtime-role grants (app.migrate), exit
#                                   non-zero on failure, then serve only /healthz and /readyz
set -eu
role="${STN_PROCESS_ROLE:-api}"
port="${PORT:-8000}"
case "$role" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port "$port" --no-server-header --no-proxy-headers
    ;;
  migrate)
    python -m app.migrate
    exec uvicorn app.migrate_server:app --host 0.0.0.0 --port "$port" --no-server-header --no-proxy-headers
    ;;
  *)
    echo "Unknown STN_PROCESS_ROLE; use 'api' or 'migrate'." >&2
    exit 64
    ;;
esac
