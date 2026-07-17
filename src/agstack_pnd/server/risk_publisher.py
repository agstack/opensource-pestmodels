"""Publish model results back to the DPI as PEST_DISEASE risk BITEs.

Closing the OpenScience loop: instead of a forecast being an opaque API
response, agstack-pnd can publish it as a GeoID-addressed, content-hashed,
queryable/auditable BITE in Pancake's store (POST /bites). Other services then
merge risk with soil/satellite/insurance data by an equijoin on the GeoID.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from agstack_pnd.foundation.types import ModelResult

RISK_BITE_TYPE = "pest_disease"
PUBLISHER = "agstack-pnd"


def build_risk_bite(result: ModelResult, geo_id: str) -> dict:
    """Build a PEST_DISEASE BITE envelope from a model result.

    Envelope shape matches the Pancake BITE store contract (Header/Body/Footer
    with a content hash over Header+Body).
    """
    timestamp = datetime.now(UTC).isoformat()
    header = {
        "id": uuid4().hex,
        "geoid": geo_id,
        "timestamp": timestamp,
        "type": RISK_BITE_TYPE,
        "source": {
            "pipeline": "agstack-pnd",
            "vendor": PUBLISHER,
            "model_uuid": str(result.model_uuid),
            "model_name": result.model_name,
        },
    }
    body = {
        "sirup_data": {
            "model_uuid": str(result.model_uuid),
            "model_name": result.model_name,
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "daily_scores": [s.model_dump(mode="json") for s in result.daily_scores],
            "summary": result.summary,
        },
        "metadata": result.metadata,
        "units": {"risk": "score"},
    }
    digest = hashlib.sha256(
        (json.dumps(header, sort_keys=True) + json.dumps(body, sort_keys=True)).encode()
    ).hexdigest()
    return {
        "Header": header,
        "Body": body,
        "Footer": {"hash": digest, "schema_version": "1.0",
                   "tags": ["pest_disease", "risk", "agstack-pnd"]},
    }


async def publish_risk_bite(
    result: ModelResult,
    geo_id: str,
    pancake_url: str,
    token: str | None = None,
) -> dict:
    """POST a risk BITE to Pancake. Returns the server response JSON.

    Raises httpx.HTTPError on transport failure; callers decide whether a
    publish failure should be fatal (usually not -- the forecast still stands).
    """
    envelope = build_risk_bite(result, geo_id)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{pancake_url.rstrip('/')}/bites", json=envelope, headers=headers
        )
        resp.raise_for_status()
        return resp.json()
