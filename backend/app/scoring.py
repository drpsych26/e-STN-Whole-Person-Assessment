"""Server-side scoring for licence-confirmed screening instruments (PHQ-9, GAD-7).

Rules
- Only instruments whose licence permits use are defined. PHQ-9 and GAD-7: "No permission required to
  reproduce, translate, display or distribute" (PHQ Screeners / Pfizer). Verified 2026-11-25.
- No item wording is stored here; items are identified by id only.
- Responses are integers 0-3 for every item. Anything else is refused.
- Totals and severity bands follow the published scoring: PHQ-9 cut points 5, 10, 15, 20
  (Kroenke, Spitzer & Williams 2001, J Gen Intern Med 16:606-613); GAD-7 cut points 5, 10, 15
  (Spitzer et al. 2006, Arch Intern Med 166:1092-1097).
- Missing items: STN rule, no total and no band if any item is missing (no prorating). This is a
  conservative engineering default pending clinical approval, not a published rule.
- PHQ-9 item 9 above 0 sets a "clinician_review_required" flag. It is not a risk classification.
- Results are screening scores, never a diagnosis. Each result says so.
- An instrument scores only when it is listed in STN_ACTIVE_INSTRUMENTS (comma-separated); activation
  is a clinical-governance decision (release gate G05). Default: none active (503).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

LIMITS = ("Screening result only. It is not a diagnosis and does not replace clinical assessment. "
          "Interpretation, formulation and any diagnosis are made by the responsible clinician.")


@dataclass(frozen=True)
class Instrument:
    id: str
    version: str
    items: tuple[str, ...]
    bands: tuple[tuple[int, str], ...]  # (minimum total, label), ascending
    citation: str
    licence: str
    licence_source: str
    review_items: tuple[str, ...] = ()


INSTRUMENTS: dict[str, Instrument] = {
    "phq9": Instrument(
        "phq9", "PHQ-9 (2001)", tuple(f"phq9_{i}" for i in range(1, 10)),
        ((0, "none-minimal"), (5, "mild"), (10, "moderate"), (15, "moderately severe"), (20, "severe")),
        "Kroenke K, Spitzer RL, Williams JBW. The PHQ-9: validity of a brief depression severity measure. "
        "J Gen Intern Med 2001;16:606-613.",
        "No permission required to reproduce, translate, display or distribute.",
        "https://www.phqscreeners.com", review_items=("phq9_9",)),
    "gad7": Instrument(
        "gad7", "GAD-7 (2006)", tuple(f"gad7_{i}" for i in range(1, 8)),
        ((0, "minimal"), (5, "mild"), (10, "moderate"), (15, "severe")),
        "Spitzer RL, Kroenke K, Williams JBW, Lowe B. A brief measure for assessing generalized anxiety "
        "disorder: the GAD-7. Arch Intern Med 2006;166:1092-1097.",
        "No permission required to reproduce, translate, display or distribute.",
        "https://www.phqscreeners.com"),
}

# Instruments considered for STN that are NOT implemented until their licence and permitted use are confirmed.
NOT_IMPLEMENTED = {
    "pcl5": "Licence and permitted use to be confirmed (US National Center for PTSD).",
    "asrs5": "Commercial-use terms to be confirmed.",
    "auditc": "Licence and NZ version to be confirmed.",
    "dast10": "Commercial-use terms to be confirmed.",
    "k10": "Licence and NZ norms to be confirmed.",
    "whodas2": "WHO permission required.",
    "cssrs": "Licence terms and training requirements to be confirmed.",
}


class ScoringError(ValueError):
    pass


class InstrumentNotActive(RuntimeError):
    pass


def active() -> set[str]:
    return {s.strip() for s in os.getenv("STN_ACTIVE_INSTRUMENTS", "").split(",") if s.strip() in INSTRUMENTS}


def score(instrument_id: str, responses: Any) -> dict[str, Any]:
    inst = INSTRUMENTS.get(instrument_id)
    if inst is None:
        raise ScoringError(f"Unknown or unlicensed instrument '{instrument_id}'.")
    if instrument_id not in active():
        raise InstrumentNotActive(f"{inst.version} is not activated for use (STN_ACTIVE_INSTRUMENTS).")
    if not isinstance(responses, dict):
        raise ScoringError("responses must be an object of item id to integer 0-3.")
    unknown = set(responses) - set(inst.items)
    if unknown:
        raise ScoringError(f"Unknown items: {', '.join(sorted(unknown))}.")
    for item, value in responses.items():
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3):
            raise ScoringError(f"{item}: responses must be integers 0-3.")
    missing = [i for i in inst.items if responses.get(i) is None]
    flags = [f"clinician_review_required:{i}" for i in inst.review_items if (responses.get(i) or 0) > 0]
    result: dict[str, Any] = {
        "instrument": inst.id, "version": inst.version, "complete": not missing, "missing_items": missing,
        "total": None, "severity_band": None, "flags": flags, "citation": inst.citation, "limitations": LIMITS,
    }
    if not missing:
        total = sum(responses[i] for i in inst.items)
        result["total"] = total
        result["severity_band"] = [label for minimum, label in inst.bands if total >= minimum][-1]
    return result


def register() -> dict[str, Any]:
    return {
        "implemented": {k: {"version": v.version, "items": len(v.items), "licence": v.licence,
                            "licence_source": v.licence_source, "citation": v.citation, "active": k in active()}
                        for k, v in INSTRUMENTS.items()},
        "not_implemented": NOT_IMPLEMENTED,
    }
