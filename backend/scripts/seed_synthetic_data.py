"""Seed a throwaway database with synthetic STN data (CI and local drills only).

Usage (from backend/):
    STN_DATABASE_URL=postgresql://... STN_DATA_KEY=<throwaway> python scripts/seed_synthetic_data.py [--reset]

--reset drops and recreates the public schema first and needs STN_ALLOW_SCHEMA_RESET=1,
so it cannot wipe a real database by accident. Every value written is synthetic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from app import accounts, assessments, audit, db, governance, privacy_requests, review_assignment, store

ORGS = ("org-synthetic-drill-a", "org-synthetic-drill-b")
SEED_ACTOR = "operator:seed"
PAYLOAD = {"items": {"synthetic_item_1": "synthetic answer", "synthetic_item_2": "synthetic answer"}}


def _reset() -> None:
    if os.getenv("STN_ALLOW_SCHEMA_RESET") != "1":
        sys.exit("Refusing --reset without STN_ALLOW_SCHEMA_RESET=1.")
    import psycopg

    with psycopg.connect(os.environ[db.URL_ENV], autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        conn.execute("CREATE SCHEMA public")
    db.reset_migration_cache()


def seed(clients_per_org: int = 3) -> dict:
    digest = hashlib.sha256(json.dumps(PAYLOAD, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    created = 0
    today = datetime.now(timezone.utc).date().isoformat()
    for org in ORGS:
        author, reviewer, admin = f"{org}:clinician", f"{org}:reviewer", f"{org}:admin"
        for subject in (admin, author, reviewer):
            accounts.invite(SEED_ACTOR, org, subject, "synthetic_seed")
            accounts.change_status(SEED_ACTOR, org, subject, "activate", "synthetic_seed")
        for n in range(clients_per_org):
            cid = store.create_record(author, org, {"display_code": f"SYN-DRILL-{n:03d}"})
            governance.record_consent(author, org, cid, "assessment", "STN-CONSENT-SYNTHETIC-0.1")
            aid = assessments.create(author, org, cid, "whole_person_initial", "v2.6", PAYLOAD)["id"]
            assessments.submit(author, org, aid, ["synthetic_flag"] if n == 0 else [])
            for flag in assessments.list_flags(author, org, ("clinician",), aid):
                assessments.acknowledge_flag(author, org, ("clinician",), aid, flag["id"])
            review_assignment.assign(admin, org, aid, reviewer)
            assessments.start_review(reviewer, org, aid)
            if n % 2:
                assessments.return_for_changes(reviewer, org, aid, "Synthetic return note.")
            else:
                assessments.sign_off(reviewer, org, aid, digest)
            if n == 0:
                request = privacy_requests.log_request(admin, org, cid, "correction", today)
                privacy_requests.correction_response(author, org, request["id"], "declined",
                                                     statement="Synthetic statement of correction.")
            created += 1
    return {"organisations": len(ORGS), "clients": created, "audit": audit.verify_chain()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--clients-per-org", type=int, default=3)
    args = parser.parse_args()
    if args.reset:
        _reset()
    result = seed(args.clients_per_org)
    print(json.dumps(result))
    return 0 if result["audit"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
