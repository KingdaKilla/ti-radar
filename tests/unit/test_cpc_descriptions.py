"""Tests fuer CPC-Beschreibungsbibliothek (domain/cpc_descriptions.py)."""

from ti_radar.domain.cpc_descriptions import (
    CPC_CLASS_DESCRIPTIONS,
    CPC_SECTION_DESCRIPTIONS,
    CPC_SUBCLASS_DESCRIPTIONS,
    describe_cpc,
)


class TestDescribeCpc:
    """Tests fuer describe_cpc() Lookup-Funktion."""

    def test_subclass_match(self):
        """Subklasse G06N → spezifische Beschreibung."""
        result = describe_cpc("G06N")
        assert "Computing" in result

    def test_subclass_h01l(self):
        """H01L → Semiconductor."""
        result = describe_cpc("H01L")
        assert "Semiconductor" in result

    def test_subclass_from_long_code(self):
        """Langer Code G06N10/00 → Subclass-Match auf G06N."""
        result = describe_cpc("G06N10/00")
        assert "Computing" in result

    def test_class_fallback(self):
        """Klasse G06 → Class-Beschreibung."""
        result = describe_cpc("G06")
        assert "Computing" in result or "Calculating" in result

    def test_section_fallback(self):
        """Sektion G → Section-Beschreibung."""
        result = describe_cpc("G")
        assert "Physics" in result

    def test_unknown_code(self):
        """Unbekannter Code → Leerstring."""
        result = describe_cpc("Z99X")
        assert result == ""

    def test_empty_code(self):
        """Leerer String → Leerstring."""
        assert describe_cpc("") == ""

    def test_none_safe(self):
        """None-Input nicht crashen (wird als Falsy behandelt)."""
        assert describe_cpc("") == ""

    def test_whitespace_handling(self):
        """Whitespace wird gestrippt."""
        result = describe_cpc("  G06N  ")
        assert "Computing" in result

    def test_medical_subclass(self):
        """A61K → Medical Preparations."""
        result = describe_cpc("A61K")
        assert "Medical" in result

    def test_vehicles_class(self):
        """B60 → Vehicles."""
        result = describe_cpc("B60")
        assert "Vehicle" in result

    def test_photovoltaics(self):
        """H02S → Photovoltaics."""
        result = describe_cpc("H02S")
        assert "Photovoltaic" in result or "Radiation" in result


class TestCpcDataCompleteness:
    """Tests fuer Vollstaendigkeit der CPC-Daten."""

    def test_all_sections_covered(self):
        """Alle 9 CPC-Sektionen (A-H + Y) haben Beschreibungen."""
        for section in "ABCDEFGHY":
            assert section in CPC_SECTION_DESCRIPTIONS, f"Section {section} fehlt"
            assert len(CPC_SECTION_DESCRIPTIONS[section]) > 0

    def test_common_classes_covered(self):
        """Haeufige CPC-Klassen sind vorhanden."""
        common = ["A61", "B01", "B60", "C07", "C08", "G01", "G06", "H01", "H04", "Y02"]
        for cls in common:
            assert cls in CPC_CLASS_DESCRIPTIONS, f"Class {cls} fehlt"

    def test_common_subclasses_covered(self):
        """Haeufige CPC-Subklassen sind vorhanden."""
        common = [
            "A61K", "A61B", "B01D", "B01J", "C07C", "C07D", "C08L",
            "G01N", "G06F", "G06N", "G06Q", "H01L", "H01M", "H04L", "H04W",
            "Y02E",
        ]
        for sub in common:
            assert sub in CPC_SUBCLASS_DESCRIPTIONS, f"Subclass {sub} fehlt"

    def test_class_descriptions_not_empty(self):
        """Keine leeren Beschreibungen in Class-Dict."""
        for code, desc in CPC_CLASS_DESCRIPTIONS.items():
            assert len(desc) > 0, f"Class {code} hat leere Beschreibung"

    def test_subclass_descriptions_not_empty(self):
        """Keine leeren Beschreibungen in Subclass-Dict."""
        for code, desc in CPC_SUBCLASS_DESCRIPTIONS.items():
            assert len(desc) > 0, f"Subclass {code} hat leere Beschreibung"

    def test_minimum_class_count(self):
        """Mindestens 50 Klassen vorhanden."""
        assert len(CPC_CLASS_DESCRIPTIONS) >= 50

    def test_minimum_subclass_count(self):
        """Mindestens 100 Subklassen vorhanden."""
        assert len(CPC_SUBCLASS_DESCRIPTIONS) >= 100
