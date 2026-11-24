#!/usr/bin/env python3
"""Guard rails for the deployment workflow, run in CI by infra-validate.yml.

The staging deploy workflow must stay manual-only, use OIDC (no client secrets), pin
third-party actions to full commit SHAs, and check its configuration before it logs in.
Exit status 0 when every rule holds; 1 with one line per failure otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / ".github" / "workflows" / "deploy-staging.yml"
SHA_PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
FIRST_PARTY = ("actions/",)
SECRET_WORDS = re.compile(r"secrets\.|client-secret|AZURE_CLIENT_SECRET|creds:", re.IGNORECASE)


def main() -> int:
    failures: list[str] = []
    text = DEPLOY.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    triggers = doc.get("on", doc.get(True))  # PyYAML reads the bare key `on` as True
    if not isinstance(triggers, dict) or set(triggers) != {"workflow_dispatch"}:
        failures.append("deploy-staging.yml must be triggered by workflow_dispatch only")
    if SECRET_WORDS.search(text):
        failures.append("deploy-staging.yml must not reference secrets or client credentials")

    jobs = doc.get("jobs") or {}
    if len(jobs) != 1:
        failures.append("deploy-staging.yml must have exactly one job")
    for name, job in jobs.items():
        if job.get("environment") != "staging":
            failures.append(f"job {name}: environment must be 'staging'")
        perms = job.get("permissions") or {}
        if perms.get("id-token") != "write" or perms.get("contents") != "read" or len(perms) != 2:
            failures.append(f"job {name}: permissions must be exactly contents: read, id-token: write")
        steps = job.get("steps") or []
        login_index = None
        for index, step in enumerate(steps):
            uses = step.get("uses")
            if not uses:
                continue
            if uses.startswith("azure/login"):
                login_index = index
            if not uses.startswith(FIRST_PARTY) and not SHA_PINNED.match(uses):
                failures.append(f"job {name}: {uses} must be pinned to a full commit SHA")
        if login_index is None:
            failures.append(f"job {name}: azure/login step missing")
        else:
            login = steps[login_index].get("with") or {}
            for key in ("client-id", "tenant-id", "subscription-id"):
                if key not in login:
                    failures.append(f"job {name}: azure/login needs {key}")
            preflight = [s for s in steps[:login_index] if "run" in s and "::error" in s["run"]]
            if not preflight:
                failures.append(f"job {name}: a preflight step must check configuration before azure/login")
            if any("uses" in s and not s["uses"].startswith(FIRST_PARTY) for s in steps[:login_index]):
                failures.append(f"job {name}: no third-party action may run before azure/login")

    top_perms = doc.get("permissions") or {}
    if top_perms != {"contents": "read"}:
        failures.append("deploy-staging.yml top-level permissions must be contents: read")

    for line in failures:
        print(f"FAIL {line}")
    if not failures:
        print("deploy-staging.yml guard rails hold")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
