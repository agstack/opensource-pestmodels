"""Tests for Layer 2 agronomic models."""

from agstack_pnd.models.agronomic.humidity_streak import HumidityStreak
from agstack_pnd.models.agronomic.leaf_wetness_cart import LeafWetnessCART
from agstack_pnd.models.agronomic.leaf_wetness_rh import LeafWetnessRH
from agstack_pnd.models.agronomic.vpd import VapourPressureDeficit


class TestLeafWetnessCART:
    def test_produces_daily_hours(self, seven_day_weather):
        model = LeafWetnessCART()
        result = model.calculate(seven_day_weather)
        assert len(result.daily_scores) == 7
        for s in result.daily_scores:
            assert 0 <= s.value <= 24


class TestLeafWetnessRH:
    def test_produces_daily_hours(self, seven_day_weather):
        model = LeafWetnessRH()
        result = model.calculate(seven_day_weather)
        assert len(result.daily_scores) == 7
        for s in result.daily_scores:
            assert 0 <= s.value <= 24


class TestVPD:
    def test_produces_positive_vpd(self, seven_day_weather):
        model = VapourPressureDeficit()
        result = model.calculate(seven_day_weather)
        assert len(result.daily_scores) == 7
        assert result.summary["mean_vpd_kpa"] >= 0


class TestHumidityStreak:
    def test_streak_tracking(self, seven_day_weather):
        model = HumidityStreak()
        result = model.calculate(seven_day_weather, {"rh_threshold": 80.0})
        assert len(result.daily_scores) == 7
        assert result.summary["max_streak_days"] >= 0
