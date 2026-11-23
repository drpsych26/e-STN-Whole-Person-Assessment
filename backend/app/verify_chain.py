"""Command-line audit-chain verification: `python -m app.verify_chain`.

Uses the configured database (STN_DATABASE_URL or STN_DATA_DB). Prints the result
as JSON and exits 1 when the chain is broken. Used by the backup/restore drill.
"""
from __future__ import annotations

import json

from .audit import verify_chain


def main() -> int:
    result = verify_chain()
    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
