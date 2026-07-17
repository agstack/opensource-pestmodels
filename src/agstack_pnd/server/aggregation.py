"""Distinct-field risk aggregation.

Aggregation is where AR2 identity earns its keep: a statistic like "what % of
maize fields in this district are at high risk this week" is a ratio over
*distinct* fields. This module aggregates published PEST_DISEASE risk BITEs over
a set of GeoIDs, de-duplicating fields and (when available) rolling child fields
up to their parent via the AR2 nesting relationship.

Cross-field correctness notes:
  * De-duplication: GeoIDs are canonical, so a set() is the distinct-field set;
    the same field captured twice does not double-count.
  * Nesting: a small plot nested in a larger field is recorded by AR2 as a
    ``child_of`` link (not a merge). ``resolve_field_set`` expands a parent into
    its children when the registry exposes them, so a roll-up is a clean tree
    walk rather than a double-count. Cross-node child resolution is not shipped
    yet (see WHATS_MISSING); today the explicit GeoID set is authoritative.
"""

from __future__ import annotations

from collections import Counter

import httpx

from agstack_pnd.foundation.types import RiskLevel

RISK_BITE_TYPE = "pest_disease"
_RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MODERATE: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
_HIGH_OR_WORSE = {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value}


async def resolve_field_set(
    geoids: list[str] | None,
    parent_geo_id: str | None,
    registry_url: str,
    token: str | None = None,
) -> list[str]:
    """Return the distinct set of fields to aggregate.

    An explicit ``geoids`` list is authoritative. A ``parent_geo_id`` is expanded
    into its ``child_of`` descendants when the registry exposes them; otherwise it
    falls back to the parent itself.
    """
    resolved: set[str] = set(geoids or [])
    if parent_geo_id:
        resolved.add(parent_geo_id)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{registry_url.rstrip('/')}/geoid/{parent_geo_id}/children",
                    headers=headers,
                )
            if resp.status_code == 200:
                data = resp.json()
                children = data.get("children") or data.get("child_geoids") or []
                resolved.update(children)
        except httpx.HTTPError:
            # Child resolution is forward-looking; the parent alone is fine today.
            pass
    return sorted(resolved)


async def _latest_risk_for_field(
    client: httpx.AsyncClient, geoid: str, pancake_url: str, headers: dict
) -> dict | None:
    resp = await client.get(
        f"{pancake_url.rstrip('/')}/bites",
        params={"geoid": geoid, "type": RISK_BITE_TYPE, "limit": 1},
        headers=headers,
    )
    if resp.status_code != 200:
        return None
    bites = resp.json().get("bites", [])
    return bites[0] if bites else None


def _worst_risk(daily_scores: list[dict]) -> tuple[str | None, float | None]:
    """Return (worst_risk_level, max_value) across a field's daily scores."""
    worst_level: RiskLevel | None = None
    max_value: float | None = None
    for s in daily_scores:
        v = s.get("value")
        if v is not None:
            max_value = v if max_value is None else max(max_value, v)
        rl = s.get("risk_level")
        if rl:
            level = RiskLevel(rl)
            if worst_level is None or _RISK_ORDER[level] > _RISK_ORDER[worst_level]:
                worst_level = level
    return (worst_level.value if worst_level else None, max_value)


async def aggregate_risk(
    pancake_url: str,
    registry_url: str,
    geoids: list[str] | None = None,
    parent_geo_id: str | None = None,
    token: str | None = None,
) -> dict:
    """Aggregate published risk over a distinct set of fields."""
    fields = await resolve_field_set(geoids, parent_geo_id, registry_url, token)
    if not fields:
        return {"distinct_field_count": 0, "fields_with_risk": 0,
                "risk_level_counts": {}, "percent_high_or_critical": 0.0, "per_field": []}

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    per_field: list[dict] = []
    level_counts: Counter = Counter()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for geoid in fields:
            bite = await _latest_risk_for_field(client, geoid, pancake_url, headers)
            if bite is None:
                per_field.append({"geoid": geoid, "has_risk": False})
                continue
            data = bite.get("Body", {}).get("sirup_data", {})
            worst_level, max_value = _worst_risk(data.get("daily_scores", []))
            if worst_level:
                level_counts[worst_level] += 1
            per_field.append({
                "geoid": geoid,
                "has_risk": True,
                "worst_risk_level": worst_level,
                "max_score": max_value,
                "model_name": data.get("model_name"),
            })

    fields_with_risk = sum(1 for f in per_field if f.get("has_risk"))
    high = sum(level_counts.get(lvl, 0) for lvl in _HIGH_OR_WORSE)
    pct = (100.0 * high / fields_with_risk) if fields_with_risk else 0.0

    return {
        "distinct_field_count": len(fields),
        "fields_with_risk": fields_with_risk,
        "risk_level_counts": dict(level_counts),
        "percent_high_or_critical": round(pct, 1),
        "per_field": per_field,
    }
