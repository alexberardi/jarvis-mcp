"""Tests for unit conversion MCP tool handler."""

import json

import pytest

from jarvis_mcp.tools.conversion import CONVERSION_TOOLS, handle_conversion_tool


class TestConversionToolDefinitions:
    """Tests for tool definitions."""

    def test_unit_convert_tool_exists(self):
        names = [t.name for t in CONVERSION_TOOLS]
        assert "unit_convert" in names

    def test_unit_convert_required_fields(self):
        tool = next(t for t in CONVERSION_TOOLS if t.name == "unit_convert")
        required = tool.inputSchema.get("required", [])
        assert "value" in required
        assert "from_unit" in required
        assert "to_unit" in required

    def test_unit_list_tool_exists(self):
        names = [t.name for t in CONVERSION_TOOLS]
        assert "unit_list" in names


class TestUnitConvertTool:
    """Tests for unit_convert tool handler."""

    @pytest.mark.asyncio
    async def test_temperature_conversion(self):
        result = await handle_conversion_tool(
            "unit_convert", {"value": 100, "from_unit": "celsius", "to_unit": "fahrenheit"}
        )
        data = json.loads(result[0].text)
        assert data["result"] == 212.0

    @pytest.mark.asyncio
    async def test_weight_conversion(self):
        result = await handle_conversion_tool(
            "unit_convert", {"value": 1, "from_unit": "kg", "to_unit": "lb"}
        )
        data = json.loads(result[0].text)
        assert abs(data["result"] - 2.20462) < 0.01

    @pytest.mark.asyncio
    async def test_missing_fields(self):
        result = await handle_conversion_tool("unit_convert", {"value": 1})
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_unsupported_unit(self):
        result = await handle_conversion_tool(
            "unit_convert", {"value": 1, "from_unit": "parsec", "to_unit": "km"}
        )
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_value(self):
        result = await handle_conversion_tool(
            "unit_convert", {"value": "not_a_number", "from_unit": "kg", "to_unit": "lb"}
        )
        data = json.loads(result[0].text)
        assert "error" in data


class TestUnitListTool:
    """Tests for unit_list tool handler."""

    @pytest.mark.asyncio
    async def test_list_all_units(self):
        result = await handle_conversion_tool("unit_list", {})
        data = json.loads(result[0].text)
        assert "temperature" in data
        assert "weight" in data

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        result = await handle_conversion_tool("unit_unknown", {})
        assert "Unknown" in result[0].text
