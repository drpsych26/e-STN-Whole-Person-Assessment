"""Server-side PHQ-9 and GAD-7 scoring against the published cut points. Synthetic responses only."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import scoring
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("STN_ACTIVE_INSTRUMENTS", "phq9,gad7")


def answers(prefix, n, total, item9=0):
    """Synthetic responses summing to total (item 9 of PHQ-9 set separately)."""
    values, remaining = [], total - item9
    for i in range(n - (1 if item9 is not None and prefix == "phq9" else 0)):
        v = min(3, remaining)
        values.append(v)
        remaining -= v
    assert remaining == 0
    if prefix == "phq9":
        values.append(item9)
    return {f"{prefix}_{i + 1}": v for i, v in enumerate(values)}


@pytest.mark.parametrize("total, band", [(0, "none-minimal"), (4, "none-minimal"), (5, "mild"), (9, "mild"),
                                         (10, "moderate"), (14, "moderate"), (15, "moderately severe"),
                                         (19, "moderately severe"), (20, "severe"), (27, "severe")])
def test_phq9_bands_follow_kroenke_2001(on, total, band):
    item9 = 3 if total == 27 else 0
    r = scoring.score("phq9", answers("phq9", 9, total, item9))
    assert (r["total"], r["severity_band"], r["complete"]) == (total, band, True)
    assert "not a diagnosis" in r["limitations"]


@pytest.mark.parametrize("total, band", [(0, "minimal"), (4, "minimal"), (5, "mild"), (9, "mild"),
                                         (10, "moderate"), (14, "moderate"), (15, "severe"), (21, "severe")])
def test_gad7_bands_follow_spitzer_2006(on, total, band):
    r = scoring.score("gad7", answers("gad7", 7, total))
    assert (r["total"], r["severity_band"]) == (total, band)


def test_phq9_item9_flags_clinician_review_only(on):
    r = scoring.score("phq9", answers("phq9", 9, 1, item9=1))
    assert r["flags"] == ["clinician_review_required:phq9_9"] and r["severity_band"] == "none-minimal"
    assert scoring.score("phq9", answers("phq9", 9, 0))["flags"] == []


def test_missing_items_give_no_total(on):
    resp = answers("phq9", 9, 12)
    del resp["phq9_4"]
    r = scoring.score("phq9", resp)
    assert r["complete"] is False and r["total"] is None and r["severity_band"] is None and r["missing_items"] == ["phq9_4"]


@pytest.mark.parametrize("bad", [{"phq9_1": 4}, {"phq9_1": -1}, {"phq9_1": "2"}, {"phq9_1": 1.5}, {"phq9_1": True},
                                 {"phq9_10": 0}, {"mood": 1}, [], "x"])
def test_invalid_responses_refused(on, bad):
    with pytest.raises(scoring.ScoringError):
        scoring.score("phq9", bad)


def test_inactive_unknown_and_unlicensed(monkeypatch):
    monkeypatch.delenv("STN_ACTIVE_INSTRUMENTS", raising=False)
    with pytest.raises(scoring.InstrumentNotActive):
        scoring.score("phq9", {})
    for name in ("asrs5", "dast10", "pcl5", "nonsense"):
        with pytest.raises(scoring.ScoringError):
            scoring.score(name, {})


def test_api_roles_activation_and_audit(backend, act, on, raw, monkeypatch):
    act("clin-sc", "clinician")
    r = client.post("/v1/scoring/phq9", json={"responses": answers("phq9", 9, 11)})
    assert r.status_code == 200 and r.json()["severity_band"] == "moderate"
    assert client.post("/v1/scoring/phq9", json={"responses": {"phq9_1": 9}}).status_code == 422
    assert client.post("/v1/scoring/asrs5", json={"responses": {}}).status_code == 422
    reg = client.get("/v1/scoring/instruments").json()
    assert reg["implemented"]["phq9"]["active"] is True and "asrs5" in reg["not_implemented"]
    act("admin-sc", "admin")
    assert client.post("/v1/scoring/phq9", json={"responses": {}}).status_code == 403  # admin is not clinical
    act("client-sc", "client")
    assert client.post("/v1/scoring/phq9", json={"responses": {}}).status_code == 403
    monkeypatch.setenv("STN_ACTIVE_INSTRUMENTS", "gad7")
    act("clin-sc", "clinician")
    assert client.post("/v1/scoring/phq9", json={"responses": {}}).status_code == 503
    rows = raw("SELECT action, outcome FROM audit_events WHERE action LIKE ?", ("scoring.%",))
    assert ("scoring.phq9", "ok_complete") in [tuple(r) for r in rows]
