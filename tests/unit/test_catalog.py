"""Tests for the threat catalog."""

from agstack_pnd.catalog.loader import get_threat, list_crops, list_threats


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
