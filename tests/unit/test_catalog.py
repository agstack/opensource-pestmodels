"""Tests for the threat catalog."""

from agstack_pnd.catalog.loader import get_threat, list_crops, list_threats
from agstack_pnd.foundation.engine_params import (
    FuzzyMamdaniParams,
    PowderyMildewGrapeParams,
)
from agstack_pnd.foundation.model_registry import ModelRegistry


class TestCatalog:
    def test_list_crops(self):
        crops = list_crops()
        assert len(crops) > 0
        assert "grape" in crops
        assert "apple" in crops

    def test_list_threats(self):
        threats = list_threats()
        assert len(threats) > 0

    def test_list_threats_by_crop(self):
        threats = list_threats("grape")
        assert len(threats) >= 3
        names = [t.scientific_name for t in threats]
        assert "Botrytis cinerea" in names

    def test_get_threat(self):
        threat = get_threat("grape", "Botrytis cinerea")
        assert threat.common_name == "Grey mold"
        assert len(threat.fuzzy_rules) > 0
        assert threat.bio_params.t_base == 0.0

    def test_all_threats_resolve_engine_params(self):
        """Every catalog entry, legacy or new-format, must resolve to a valid schema."""
        registry = ModelRegistry()
        for threat in list_threats():
            resolved = threat.resolve_engine_params(registry)
            if threat.engine_type == "powdery_mildew_grape":
                assert isinstance(resolved, PowderyMildewGrapeParams)
            else:
                assert isinstance(resolved, FuzzyMamdaniParams)

    def test_powdery_mildew_entry_uses_dedicated_params(self):
        threat = get_threat("grape", "Uncinula necator")
        assert threat.engine_type == "powdery_mildew_grape"
        assert threat.engine_params is not None
        resolved = threat.resolve_engine_params(ModelRegistry())
        assert isinstance(resolved, PowderyMildewGrapeParams)
        assert resolved.conidial_favorable_temp_min_f == 70.0
        assert resolved.conidial_heat_penalty_temp_f == 95.0

    def test_new_format_entry_uses_engine_params(self):
        threat = get_threat("pear", "Venturia pirina")
        assert threat.engine_type == "fuzzy_mamdani"
        assert threat.engine_params is not None
        resolved = threat.resolve_engine_params(ModelRegistry())
        assert threat.bio_params.t_optimal_min == 14.0
        assert isinstance(resolved, FuzzyMamdaniParams)
        assert len(resolved.fuzzy_rules) == 3

