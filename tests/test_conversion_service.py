"""Tests for unit conversion service.

Tests conversion between common units across categories.
"""

import pytest

from jarvis_mcp.services.conversion_service import convert, get_supported_units


class TestTemperature:
    """Tests for temperature conversions."""

    def test_celsius_to_fahrenheit(self):
        assert convert(100, "celsius", "fahrenheit") == 212.0

    def test_fahrenheit_to_celsius(self):
        assert convert(32, "fahrenheit", "celsius") == 0.0

    def test_celsius_to_kelvin(self):
        assert convert(0, "celsius", "kelvin") == 273.15

    def test_kelvin_to_celsius(self):
        assert convert(273.15, "kelvin", "celsius") == 0.0

    def test_fahrenheit_to_kelvin(self):
        result = convert(212, "fahrenheit", "kelvin")
        assert abs(result - 373.15) < 0.01

    def test_kelvin_to_fahrenheit(self):
        result = convert(373.15, "kelvin", "fahrenheit")
        assert abs(result - 212.0) < 0.01

    def test_negative_celsius(self):
        result = convert(-40, "celsius", "fahrenheit")
        assert abs(result - (-40)) < 0.01

    def test_temperature_aliases(self):
        assert convert(100, "c", "f") == 212.0
        assert convert(0, "f", "c") == pytest.approx(-17.778, abs=0.01)


class TestWeight:
    """Tests for weight/mass conversions."""

    def test_kg_to_lb(self):
        result = convert(1, "kg", "lb")
        assert abs(result - 2.20462) < 0.01

    def test_lb_to_kg(self):
        result = convert(1, "lb", "kg")
        assert abs(result - 0.453592) < 0.01

    def test_kg_to_g(self):
        assert convert(1, "kg", "g") == 1000.0

    def test_g_to_kg(self):
        assert convert(1000, "g", "kg") == 1.0

    def test_oz_to_g(self):
        result = convert(1, "oz", "g")
        assert abs(result - 28.3495) < 0.01

    def test_weight_aliases(self):
        result = convert(1, "kilogram", "pound")
        assert abs(result - 2.20462) < 0.01


class TestVolume:
    """Tests for volume conversions."""

    def test_cup_to_ml(self):
        result = convert(1, "cup", "ml")
        assert abs(result - 236.588) < 0.01

    def test_ml_to_cup(self):
        result = convert(236.588, "ml", "cup")
        assert abs(result - 1.0) < 0.01

    def test_liter_to_ml(self):
        assert convert(1, "liter", "ml") == 1000.0

    def test_gallon_to_liter(self):
        result = convert(1, "gallon", "liter")
        assert abs(result - 3.78541) < 0.01

    def test_tablespoon_to_ml(self):
        result = convert(1, "tablespoon", "ml")
        assert abs(result - 14.787) < 0.01

    def test_teaspoon_to_ml(self):
        result = convert(1, "teaspoon", "ml")
        assert abs(result - 4.929) < 0.01


class TestDistance:
    """Tests for distance/length conversions."""

    def test_mile_to_km(self):
        result = convert(1, "mile", "km")
        assert abs(result - 1.60934) < 0.01

    def test_km_to_mile(self):
        result = convert(1, "km", "mile")
        assert abs(result - 0.621371) < 0.01

    def test_meter_to_feet(self):
        result = convert(1, "meter", "feet")
        assert abs(result - 3.28084) < 0.01

    def test_inch_to_cm(self):
        result = convert(1, "inch", "cm")
        assert abs(result - 2.54) < 0.01

    def test_cm_to_inch(self):
        result = convert(1, "cm", "inch")
        assert abs(result - 0.393701) < 0.01


class TestSpeed:
    """Tests for speed conversions."""

    def test_mph_to_kph(self):
        result = convert(60, "mph", "kph")
        assert abs(result - 96.5606) < 0.01

    def test_kph_to_mph(self):
        result = convert(100, "kph", "mph")
        assert abs(result - 62.1371) < 0.01

    def test_speed_aliases(self):
        result = convert(60, "miles_per_hour", "km_per_hour")
        assert abs(result - 96.5606) < 0.01


class TestTime:
    """Tests for time conversions."""

    def test_hours_to_minutes(self):
        assert convert(1, "hour", "minute") == 60.0

    def test_minutes_to_seconds(self):
        assert convert(1, "minute", "second") == 60.0

    def test_hours_to_seconds(self):
        assert convert(1, "hour", "second") == 3600.0

    def test_days_to_hours(self):
        assert convert(1, "day", "hour") == 24.0


class TestEdgeCases:
    """Tests for edge cases and errors."""

    def test_same_unit(self):
        assert convert(42, "kg", "kg") == 42.0

    def test_unsupported_unit(self):
        with pytest.raises(ValueError, match="[Uu]nsupported"):
            convert(1, "parsec", "km")

    def test_incompatible_units(self):
        with pytest.raises(ValueError):
            convert(1, "kg", "km")

    def test_zero_value(self):
        assert convert(0, "celsius", "fahrenheit") == 32.0

    def test_negative_value(self):
        result = convert(-10, "celsius", "fahrenheit")
        assert abs(result - 14.0) < 0.01


class TestSupportedUnits:
    """Tests for the supported units listing."""

    def test_returns_categories(self):
        units = get_supported_units()
        assert "temperature" in units
        assert "weight" in units
        assert "volume" in units
        assert "distance" in units
        assert "speed" in units
        assert "time" in units

    def test_categories_have_units(self):
        units = get_supported_units()
        for category, unit_list in units.items():
            assert len(unit_list) > 0, f"Category {category} has no units"
