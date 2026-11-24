#!/usr/bin/env python3
"""Supply-chain and injection guard rails for every GitHub Actions workflow.

Rules (each failure prints one line; exit status 1 if any rule fails):
1. Every `uses:` reference is pinned to a full 40-character commit SHA, first-party
   `actions/*` included. A tag such as @v7 can be moved by whoever controls the action
   repository; android-apk.yml runs actions in the same job as the release keystore and
   a contents: write token.
2. No `run:` script interpolates untrusted expressions directly (`${{ github.event.* }}`,
   `${{ inputs.* }}`, `${{ github.head_ref }}`). Pass them through `env:` and quote them.
3. No workflow uses the `pull_request_target` trigger.
4. Least privilege for repository writes: top-level permissions never grant `contents: write`,
   and a job that holds `contents: write` runs no checkout and no action other than
   actions/download-artifact (it may only act on artifacts that a read-only job produced).

Dependabot (.github/dependabot.yml) keeps the pinned SHAs current.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
SHA_PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
WRITE_JOB_ACTIONS = ("actions/download-artifact@",)
UNTRUSTED = re.compile(r"\$\{\{\s*(github\.event\.|inputs\.|github\.head_ref|github\.event_name)")


def check(path: Path) -> list[str]:
    failures: list[str] = []
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    triggers = doc.get("on", doc.get(True))
    if (isinstance(triggers, dict) and "pull_request_target" in triggers) or triggers == "pull_request_target":
        failures.append(f"{path.name}: pull_request_target is not allowed")
    top = doc.get("permissions")
    if top == "write-all" or (isinstance(top, dict) and top.get("contents") == "write"):
        failures.append(f"{path.name}: top-level permissions must not grant contents: write; grant it to one job")
    for job_name, job in (doc.get("jobs") or {}).items():
        perms = job.get("permissions")
        if perms == "write-all" or (isinstance(perms, dict) and perms.get("contents") == "write"):
            for step in job.get("steps") or []:
                uses = step.get("uses") or ""
                if uses and not uses.startswith(WRITE_JOB_ACTIONS):
                    failures.append(f"{path.name}: job {job_name} holds contents: write and must not use {uses}")
        if isinstance(job.get("uses"), str) and not job["uses"].startswith("./") and not SHA_PINNED.match(job["uses"]):
            failures.append(f"{path.name}: job {job_name}: {job['uses']} must be pinned to a full commit SHA")
        for index, step in enumerate(job.get("steps") or []):
            uses = step.get("uses")
            if uses and not uses.startswith("./") and not SHA_PINNED.match(uses):
                failures.append(f"{path.name}: job {job_name} step {index}: {uses} must be pinned to a full commit SHA")
            run = step.get("run")
            if isinstance(run, str) and UNTRUSTED.search(run):
                failures.append(
                    f"{path.name}: job {job_name} step {index}: run script interpolates an untrusted expression; "
                    "pass it through env: instead"
                )
    return failures


def main() -> int:
    files = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    failures = [line for path in files for line in check(path)]
    for line in failures:
        print(f"FAIL {line}")
    if not failures:
        print(f"{len(files)} workflows: every action SHA-pinned, no untrusted interpolation in run scripts")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
