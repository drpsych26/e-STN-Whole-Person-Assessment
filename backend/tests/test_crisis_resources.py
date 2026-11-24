"""Public crisis-resource register: endpoint and validation rules. No database needed."""
from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from app import crisis_resources
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_public_without_authentication():
    r = client.get("/v1/public/crisis-resources")
    assert r.status_code == 200
    body = r.json()
    assert [t["id"] for t in body["tiers"]] == list(crisis_resources.TIER_ORDER)
    assert body["approval"]["status"] == "provisional" and body["approval"]["clinically_approved"] is False
    assert "not an emergency service" in body["stn_statement"]
    assert r.headers["cache-control"] == "public, max-age=3600"


def test_region_selection():
    r = client.get("/v1/public/crisis-resources", params={"region": "canterbury"})
    assert r.json()["selected_region"]["teams"][0]["tel"] == "0800920092"
    assert client.get("/v1/public/crisis-resources", params={"region": "atlantis"}).status_code == 404
    assert client.get("/v1/public/crisis-resources", params={"region": "<script>"}).status_code == 422


def _broken(mutate):
    data = copy.deepcopy(crisis_resources.register())
    mutate(data)
    with pytest.raises(crisis_resources.RegisterInvalid):
        crisis_resources.validate(data)


def test_validation_refuses_unsafe_registers():
    def lifeline_24_7(d):
        for t in d["tiers"]:
            for a in t["actions"]:
                if a.get("tel") == "0800543354":
                    a["hours"] = "24/7"
    _broken(lifeline_24_7)
    _broken(lambda d: d["tiers"][0]["actions"][0].update(tel="1737"))  # 111 must lead
    _broken(lambda d: d["tiers"].reverse() or [t.update(order=i) for i, t in enumerate(d["tiers"])])
    _broken(lambda d: d["tiers"][2]["actions"][0].update(hours=""))
    _broken(lambda d: d["regions"][1]["teams"].append({"place": "x", "phone": "0800 000 000", "tel": "0800000000"}))
    _broken(lambda d: d["regions"][2]["teams"][0].update(tel="0800999999"))
    _broken(lambda d: d["approval"].update(status="approved"))
