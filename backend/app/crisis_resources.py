"""Crisis-resource register for the client-facing crisis panel (D-15).

The single source of truth is app/data/crisis_resources.json. The browser component
(frontend/crisis-panel/) bundles an identical copy so the panel never waits on this API; a test
fails if the two drift apart. GET /v1/public/crisis-resources serves it without authentication.

The register is validated on load. It refuses to describe Lifeline or the Suicide Crisis Helpline
as 24/7 (they are 7am to midnight since 2025), requires every phone action to have hours, and
keeps the approval status visible: content stays "provisional" until STN's clinical lead approves
the wording and tiers (D-SAFE-01). Regional crisis-team numbers are transcribed from the Mental
Health Foundation June 2026 directory and must be checked against it by a person before release.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response

PATH = Path(__file__).parent / "data" / "crisis_resources.json"
TIER_ORDER = ("immediate_danger", "urgent_crisis", "distress", "routine_support")
NOT_24_7 = ("0800543354", "0508828865")  # Lifeline and the Suicide Crisis Helpline


class RegisterInvalid(ValueError):
    pass


def validate(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema") != "stn-crisis-resources/1":
        raise RegisterInvalid("Unknown register schema.")
    tiers = data.get("tiers") or []
    if tuple(t["id"] for t in sorted(tiers, key=lambda t: t["order"])) != TIER_ORDER:
        raise RegisterInvalid("Tiers must be immediate_danger, urgent_crisis, distress, routine_support in that order.")
    if tiers[0]["actions"][0].get("tel") != "111":
        raise RegisterInvalid("The immediate-danger tier must lead with 111.")
    for tier in tiers:
        for action in tier["actions"]:
            if not action.get("hours"):
                raise RegisterInvalid(f"{action['label']}: hours are required.")
            if action.get("tel") in NOT_24_7 and "24" in action["hours"]:
                raise RegisterInvalid(f"{action['label']} is not a 24/7 service.")
            if action.get("tel") and not action["tel"].isdigit():
                raise RegisterInvalid(f"{action['label']}: tel must be digits only.")
    for region in data.get("regions") or []:
        if region["status"] not in {"transcribed_pending_check", "checked", "see_source"}:
            raise RegisterInvalid(f"{region['id']}: unknown status.")
        if region["status"] == "see_source" and region["teams"]:
            raise RegisterInvalid(f"{region['id']}: see_source regions must not list numbers.")
        for team in region["teams"]:
            if not team["tel"].isdigit() or team["tel"] != "".join(c for c in team["phone"] if c.isdigit()):
                raise RegisterInvalid(f"{region['id']}: phone and tel disagree.")
    approval = data.get("approval") or {}
    if approval.get("clinically_approved") is not True and approval.get("status") != "provisional":
        raise RegisterInvalid("Unapproved content must be marked provisional.")
    return data


@lru_cache(maxsize=1)
def register() -> dict[str, Any]:
    return validate(json.loads(PATH.read_text(encoding="utf-8")))


def for_region(region_id: str | None) -> dict[str, Any]:
    data = dict(register())
    if region_id is not None:
        match = [r for r in data["regions"] if r["id"] == region_id]
        if not match:
            raise KeyError(region_id)
        data["selected_region"] = match[0]
    return data


router = APIRouter(prefix="/v1/public", tags=["public"])


@router.get("/crisis-resources")
def crisis_resources(response: Response, region: str | None = Query(None, pattern="^[a-z_]{2,40}$")) -> dict:
    """Public, unauthenticated. Crisis contacts by tier, optionally with one region's crisis team."""
    try:
        data = for_region(region)
    except KeyError as exc:
        raise HTTPException(404, "Unknown region.") from exc
    response.headers["Cache-Control"] = "public, max-age=3600"
    return data
