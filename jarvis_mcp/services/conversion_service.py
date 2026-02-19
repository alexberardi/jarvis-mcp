"""Unit conversion service.

Converts between common units across categories: temperature, weight,
volume, distance, speed, and time. Each category uses a canonical base
unit with conversion factors, except temperature which uses explicit formulas.
"""

from typing import Union

NumericResult = Union[int, float]

# Unit aliases: maps common names/abbreviations to canonical names
_ALIASES: dict[str, str] = {
    # Temperature
    "c": "celsius",
    "f": "fahrenheit",
    "k": "kelvin",
    # Weight
    "kilogram": "kg",
    "kilograms": "kg",
    "gram": "g",
    "grams": "g",
    "milligram": "mg",
    "milligrams": "mg",
    "pound": "lb",
    "pounds": "lb",
    "lbs": "lb",
    "ounce": "oz",
    "ounces": "oz",
    # Volume
    "cups": "cup",
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "litre": "liter",
    "litres": "liter",
    "liters": "liter",
    "l": "liter",
    "gallon": "gal",
    "gallons": "gal",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "fluid_ounce": "fl_oz",
    "fluid_ounces": "fl_oz",
    "pint": "pt",
    "pints": "pt",
    "quart": "qt",
    "quarts": "qt",
    # Distance
    "meter": "m",
    "meters": "m",
    "metre": "m",
    "metres": "m",
    "kilometer": "km",
    "kilometers": "km",
    "kilometre": "km",
    "kilometres": "km",
    "centimeter": "cm",
    "centimeters": "cm",
    "centimetre": "cm",
    "centimetres": "cm",
    "millimeter": "mm",
    "millimeters": "mm",
    "mile": "mi",
    "miles": "mi",
    "foot": "ft",
    "feet": "ft",
    "inch": "in",
    "inches": "in",
    "yard": "yd",
    "yards": "yd",
    # Speed
    "mph": "mi_per_h",
    "miles_per_hour": "mi_per_h",
    "kph": "km_per_h",
    "kmh": "km_per_h",
    "km_per_hour": "km_per_h",
    "meters_per_second": "m_per_s",
    "mps": "m_per_s",
    # Time
    "second": "s",
    "seconds": "s",
    "sec": "s",
    "minute": "min",
    "minutes": "min",
    "hour": "h",
    "hours": "h",
    "hr": "h",
    "day": "d",
    "days": "d",
    "week": "wk",
    "weeks": "wk",
}

# Conversion factors to base unit (base_unit is factor 1.0)
# Each category maps: unit -> factor to convert TO base unit
# So: value_in_base = value * factor

_WEIGHT_BASE = "g"  # grams
_WEIGHT_FACTORS: dict[str, float] = {
    "g": 1.0,
    "kg": 1000.0,
    "mg": 0.001,
    "lb": 453.592,
    "oz": 28.3495,
}

_VOLUME_BASE = "ml"  # milliliters
_VOLUME_FACTORS: dict[str, float] = {
    "ml": 1.0,
    "liter": 1000.0,
    "cup": 236.588,
    "gal": 3785.41,
    "tbsp": 14.787,
    "tsp": 4.929,
    "fl_oz": 29.5735,
    "pt": 473.176,
    "qt": 946.353,
}

_DISTANCE_BASE = "m"  # meters
_DISTANCE_FACTORS: dict[str, float] = {
    "m": 1.0,
    "km": 1000.0,
    "cm": 0.01,
    "mm": 0.001,
    "mi": 1609.34,
    "ft": 0.3048,
    "in": 0.0254,
    "yd": 0.9144,
}

_SPEED_BASE = "m_per_s"  # meters per second
_SPEED_FACTORS: dict[str, float] = {
    "m_per_s": 1.0,
    "km_per_h": 1 / 3.6,  # 1 km/h = 1/3.6 m/s
    "mi_per_h": 0.44704,  # 1 mph = 0.44704 m/s
}

_TIME_BASE = "s"  # seconds
_TIME_FACTORS: dict[str, float] = {
    "s": 1.0,
    "min": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "wk": 604800.0,
}

# Temperature units (handled with formulas, not factors)
_TEMPERATURE_UNITS: set[str] = {"celsius", "fahrenheit", "kelvin"}

# Category lookup: unit -> (category_name, factors_dict)
_CATEGORY_MAP: dict[str, tuple[str, dict[str, float]]] = {}

for unit in _WEIGHT_FACTORS:
    _CATEGORY_MAP[unit] = ("weight", _WEIGHT_FACTORS)
for unit in _VOLUME_FACTORS:
    _CATEGORY_MAP[unit] = ("volume", _VOLUME_FACTORS)
for unit in _DISTANCE_FACTORS:
    _CATEGORY_MAP[unit] = ("distance", _DISTANCE_FACTORS)
for unit in _SPEED_FACTORS:
    _CATEGORY_MAP[unit] = ("speed", _SPEED_FACTORS)
for unit in _TIME_FACTORS:
    _CATEGORY_MAP[unit] = ("time", _TIME_FACTORS)
for unit in _TEMPERATURE_UNITS:
    _CATEGORY_MAP[unit] = ("temperature", {})


def _normalize_unit(unit: str) -> str:
    """Normalize a unit string to its canonical form."""
    unit = unit.strip().lower().replace(" ", "_")
    return _ALIASES.get(unit, unit)


def convert(value: float | int, from_unit: str, to_unit: str) -> float:
    """Convert a value between units.

    Args:
        value: Numeric value to convert.
        from_unit: Source unit (e.g., "celsius", "kg", "miles").
        to_unit: Target unit (e.g., "fahrenheit", "lb", "km").

    Returns:
        Converted value as float.

    Raises:
        ValueError: If units are unsupported or incompatible.
    """
    from_canonical = _normalize_unit(from_unit)
    to_canonical = _normalize_unit(to_unit)

    # Same unit: return as-is
    if from_canonical == to_canonical:
        return float(value)

    # Look up categories
    from_info = _CATEGORY_MAP.get(from_canonical)
    to_info = _CATEGORY_MAP.get(to_canonical)

    if from_info is None:
        raise ValueError(f"Unsupported unit: {from_unit}")
    if to_info is None:
        raise ValueError(f"Unsupported unit: {to_unit}")

    from_category = from_info[0]
    to_category = to_info[0]

    if from_category != to_category:
        raise ValueError(
            f"Incompatible units: {from_unit} ({from_category}) and {to_unit} ({to_category})"
        )

    # Temperature: use explicit formulas
    if from_category == "temperature":
        return _convert_temperature(value, from_canonical, to_canonical)

    # All other categories: convert via base unit
    factors = from_info[1]
    from_factor = factors[from_canonical]
    to_factor = factors[to_canonical]

    # value -> base -> target
    base_value = value * from_factor
    return base_value / to_factor


def _convert_temperature(value: float | int, from_unit: str, to_unit: str) -> float:
    """Convert temperature using explicit formulas."""
    # Convert to Celsius first
    if from_unit == "celsius":
        celsius = float(value)
    elif from_unit == "fahrenheit":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "kelvin":
        celsius = value - 273.15
    else:
        raise ValueError(f"Unsupported temperature unit: {from_unit}")

    # Convert from Celsius to target
    if to_unit == "celsius":
        return celsius
    elif to_unit == "fahrenheit":
        return celsius * 9 / 5 + 32
    elif to_unit == "kelvin":
        return celsius + 273.15
    else:
        raise ValueError(f"Unsupported temperature unit: {to_unit}")


def get_supported_units() -> dict[str, list[str]]:
    """Return a dict of category -> list of canonical unit names."""
    return {
        "temperature": sorted(_TEMPERATURE_UNITS),
        "weight": sorted(_WEIGHT_FACTORS.keys()),
        "volume": sorted(_VOLUME_FACTORS.keys()),
        "distance": sorted(_DISTANCE_FACTORS.keys()),
        "speed": sorted(_SPEED_FACTORS.keys()),
        "time": sorted(_TIME_FACTORS.keys()),
    }
