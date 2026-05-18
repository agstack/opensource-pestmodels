"""Rule-based risk engine -- boolean condition matching.

Legacy-compatible engine: evaluates hard threshold rules on weather variables.
Each rule has conditions (field, operator, value) and a risk level.

Ported from the upstream OpenAgri PestAndDiseaseManagement rule engine.
"""

from __future__ import annotations

import operator as op
from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import UUID

import numpy as np

from agstack_pnd.foundation.base_model import PestModelBase
from agstack_pnd.foundation.exceptions import ModelValidationError
from agstack_pnd.foundation.types import (
    DailyScore,
    ModelLayer,
    ModelMetadata,
    ModelResult,
    RiskLevel,
    ThreatDefinition,
    WeatherDataFrame,
)

_OPERATORS: dict[str, Any] = {
    ">": op.gt,
    ">=": op.ge,
    "<": op.lt,
    "<=": op.le,
    "==": op.eq,
    "!=": op.ne,
}


class RuleCondition:
    """A single condition: field op value."""

    def __init__(self, field: str, operator: str, value: float) -> None:
        if operator not in _OPERATORS:
            raise ModelValidationError(f"Unknown operator '{operator}'")
        self.field = field
        self.operator = operator
        self.value = value
        self._op_fn = _OPERATORS[operator]

    def evaluate(self, field_value: float) -> bool:
        return bool(self._op_fn(field_value, self.value))


class Rule:
    """A risk rule: all conditions must match for the risk level to apply."""

    def __init__(self, conditions: list[RuleCondition], risk_level: RiskLevel) -> None:
        self.conditions = conditions
        self.risk_level = risk_level


class RuleBasedRisk(PestModelBase):
    """Boolean rule-based risk assessment.

    Rules are passed via the ``parameters`` dict as a list of rule definitions.
    Each rule: {"conditions": [{"field": ..., "op": ..., "value": ...}], "risk": "high"}.

    Evaluates hourly, then reports the highest triggered risk per day.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0004-4000-8000-000000000002"),
        name="rule_based_risk",
        display_name="Rule-Based Risk Engine",
        version="2.0.0",
        layer=ModelLayer.DISEASE,
        description="Boolean condition matching on weather variables, 3-tier risk output.",
        supported_crops=None,
        required_weather_fields=["air_temperature", "relative_humidity", "precipitation"],
        citation="OpenAgri PestAndDiseaseManagement rule engine.",
        author="AgStack Foundation / OpenAgri",
    )

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        params = dict(parameters) if parameters else {}
        if "rules" not in params:
            raise ModelValidationError("rule_based_risk requires 'rules' parameter")
        return params

    def _parse_rules(self, rules_raw: list[dict[str, Any]]) -> list[Rule]:
        rules: list[Rule] = []
        for r in rules_raw:
            conditions = [
                RuleCondition(c["field"], c["op"], float(c["value"]))
                for c in r.get("conditions", [])
            ]
            risk = RiskLevel(r.get("risk", "low"))
            rules.append(Rule(conditions, risk))
        return rules

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        params = self.validate_parameters(parameters)
        rules = self._parse_rules(params["rules"])  # type: ignore[arg-type]

        ts = weather_data.timestamps
        unique_dates = np.unique(ts.astype("datetime64[D]"))

        _risk_order = {RiskLevel.LOW: 0, RiskLevel.MODERATE: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
        daily_scores: list[DailyScore] = []

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            indices = np.where(mask)[0]
            max_risk = RiskLevel.LOW

            for idx in indices:
                for rule in rules:
                    all_match = all(
                        c.evaluate(float(weather_data[c.field][idx]))
                        for c in rule.conditions
                        if c.field in weather_data
                    )
                    if all_match and _risk_order[rule.risk_level] > _risk_order[max_risk]:
                        max_risk = rule.risk_level

            score_map = {RiskLevel.LOW: 10.0, RiskLevel.MODERATE: 50.0, RiskLevel.HIGH: 90.0, RiskLevel.CRITICAL: 100.0}
            daily_scores.append(DailyScore(
                date=day.astype("datetime64[D]").astype(object),
                value=score_map[max_risk],
                risk_level=max_risk,
            ))

        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={"rules_count": len(rules), "days": len(daily_scores)},
        )
