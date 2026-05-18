"""Tests for Growing Degree Days model."""

from agstack_pnd.models.weather.growing_degree_days import GrowingDegreeDays


class TestGDD:
    def test_basic_accumulation(self, seven_day_weather):
        model = GrowingDegreeDays()
        result = model.calculate(seven_day_weather, {"base_temp": 10.0})
        assert len(result.daily_scores) == 7
        assert result.summary["total_gdd"] > 0
        assert result.summary["base_temp"] == 10.0

    def test_cumulative_is_monotonic(self, seven_day_weather):
        model = GrowingDegreeDays()
        result = model.calculate(seven_day_weather, {"base_temp": 10.0})
        values = [s.value for s in result.daily_scores]
        for i in range(1, len(values)):
            assert values[i] >= values[i - 1]

    def test_high_base_temp_yields_zero(self, seven_day_weather):
        model = GrowingDegreeDays()
        result = model.calculate(seven_day_weather, {"base_temp": 40.0, "upper_threshold": 50.0})
        assert result.summary["total_gdd"] == 0.0

    def test_metadata(self):
        model = GrowingDegreeDays()
        assert model.metadata.name == "growing_degree_days"
        assert model.metadata.layer.value == "weather"
