"""Tests for Chill Hours and Chill Portions models."""

from agstack_pnd.models.weather.chill_hours import ChillHours3245, ChillHoursUtah
from agstack_pnd.models.weather.chill_portions import ChillPortions


class TestChillUtah:
    def test_produces_results(self, thirty_day_weather):
        model = ChillHoursUtah()
        result = model.calculate(thirty_day_weather)
        assert len(result.daily_scores) == 30
        assert "total_chill_units" in result.summary


class TestChill3245:
    def test_produces_results(self, thirty_day_weather):
        model = ChillHours3245()
        result = model.calculate(thirty_day_weather)
        assert len(result.daily_scores) == 30


class TestChillPortions:
    def test_produces_results(self, thirty_day_weather):
        model = ChillPortions()
        result = model.calculate(thirty_day_weather)
        assert len(result.daily_scores) == 30
        assert result.summary["total_portions"] >= 0
