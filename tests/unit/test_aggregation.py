"""Distinct-field risk aggregation logic."""

from __future__ import annotations

import pytest

from agstack_pnd.server import aggregation


def test_worst_risk_picks_highest_level_and_max_value():
    scores = [
        {"value": 0.2, "risk_level": "low"},
        {"value": 0.7, "risk_level": "high"},
        {"value": 0.5, "risk_level": "moderate"},
    ]
    level, mx = aggregation._worst_risk(scores)
    assert level == "high"
    assert mx == 0.7


def test_worst_risk_handles_missing_levels():
    level, mx = aggregation._worst_risk([{"value": 0.3}, {"value": 0.1}])
    assert level is None
    assert mx == 0.3


@pytest.mark.asyncio
async def test_aggregate_counts_distinct_and_percent(monkeypatch):
    async def fake_resolve(geoids, parent, reg, token=None):
        return ["g1", "g2", "g3"]

    canned = {
        "g1": {"Body": {"sirup_data": {
            "daily_scores": [{"value": 0.9, "risk_level": "critical"}], "model_name": "m"}}},
        "g2": {"Body": {"sirup_data": {
            "daily_scores": [{"value": 0.2, "risk_level": "low"}], "model_name": "m"}}},
        "g3": None,  # no risk published for this field
    }

    async def fake_latest(client, geoid, url, headers):
        return canned[geoid]

    monkeypatch.setattr(aggregation, "resolve_field_set", fake_resolve)
    monkeypatch.setattr(aggregation, "_latest_risk_for_field", fake_latest)

    out = await aggregation.aggregate_risk(
        "http://pancake.test", "http://registry.test", geoids=["g1", "g2", "g3"]
    )
    assert out["distinct_field_count"] == 3
    assert out["fields_with_risk"] == 2
    assert out["risk_level_counts"] == {"critical": 1, "low": 1}
    assert out["percent_high_or_critical"] == 50.0


@pytest.mark.asyncio
async def test_resolve_field_set_dedupes_explicit_geoids():
    fields = await aggregation.resolve_field_set(
        ["g1", "g2", "g1"], None, "http://registry.test"
    )
    assert fields == ["g1", "g2"]
