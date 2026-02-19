"""Unit conversion tool for jarvis-mcp.

Provides unit conversion between common units as MCP tools.
"""

import json
from typing import Any

from mcp.types import Tool, TextContent

from jarvis_mcp.services.conversion_service import convert, get_supported_units


CONVERSION_TOOLS: list[Tool] = [
    Tool(
        name="unit_convert",
        description=(
            "Convert a value between units. "
            "Supports temperature (celsius, fahrenheit, kelvin), "
            "weight (kg, lb, oz, g), volume (cup, ml, liter, gallon, tbsp, tsp), "
            "distance (km, mile, meter, feet, inch, cm), "
            "speed (mph, kph, m/s), and time (seconds, minutes, hours, days). "
            "Accepts common aliases (e.g., 'c' for celsius, 'lbs' for pounds)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "value": {
                    "type": "number",
                    "description": "Numeric value to convert.",
                },
                "from_unit": {
                    "type": "string",
                    "description": "Source unit (e.g., 'celsius', 'kg', 'miles', 'cup').",
                },
                "to_unit": {
                    "type": "string",
                    "description": "Target unit (e.g., 'fahrenheit', 'lb', 'km', 'ml').",
                },
            },
            "required": ["value", "from_unit", "to_unit"],
        },
    ),
    Tool(
        name="unit_list",
        description=(
            "List all supported unit categories and their canonical unit names. "
            "Useful for discovering what conversions are available."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


async def handle_conversion_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle execution of conversion tools."""
    if name == "unit_convert":
        return await _unit_convert(arguments)
    elif name == "unit_list":
        return await _unit_list(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown conversion tool: {name}")]


async def _unit_convert(args: dict[str, Any]) -> list[TextContent]:
    """Convert a value between units."""
    value = args.get("value")
    from_unit = args.get("from_unit")
    to_unit = args.get("to_unit")

    if value is None or from_unit is None or to_unit is None:
        return [TextContent(type="text", text='{"error": "value, from_unit, and to_unit are required"}')]

    if not isinstance(from_unit, str) or not isinstance(to_unit, str):
        return [TextContent(type="text", text='{"error": "from_unit and to_unit must be strings"}')]

    try:
        value = float(value)
    except (TypeError, ValueError):
        return [TextContent(type="text", text='{"error": "value must be a number"}')]

    try:
        result = convert(value, from_unit, to_unit)
        return [TextContent(type="text", text=json.dumps({
            "result": round(result, 6),
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
        }))]
    except ValueError as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _unit_list(args: dict[str, Any]) -> list[TextContent]:
    """List supported units."""
    units = get_supported_units()
    return [TextContent(type="text", text=json.dumps(units, indent=2))]
