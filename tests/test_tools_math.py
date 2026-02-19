"""Tests for math MCP tool handler."""

import json

import pytest

from jarvis_mcp.tools.math import MATH_TOOLS, handle_math_tool


class TestMathToolDefinitions:
    """Tests for tool definitions."""

    def test_math_evaluate_tool_exists(self):
        names = [t.name for t in MATH_TOOLS]
        assert "math_evaluate" in names

    def test_math_evaluate_requires_expression(self):
        tool = next(t for t in MATH_TOOLS if t.name == "math_evaluate")
        assert "expression" in tool.inputSchema.get("required", [])


class TestMathEvaluateTool:
    """Tests for math_evaluate tool handler."""

    @pytest.mark.asyncio
    async def test_simple_expression(self):
        result = await handle_math_tool("math_evaluate", {"expression": "2 + 3"})
        data = json.loads(result[0].text)
        assert data["result"] == 5

    @pytest.mark.asyncio
    async def test_complex_expression(self):
        result = await handle_math_tool("math_evaluate", {"expression": "sqrt(144) + pi"})
        data = json.loads(result[0].text)
        assert abs(data["result"] - 15.14159) < 0.01

    @pytest.mark.asyncio
    async def test_missing_expression(self):
        result = await handle_math_tool("math_evaluate", {})
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_expression(self):
        result = await handle_math_tool("math_evaluate", {"expression": "import os"})
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_expression_too_long(self):
        result = await handle_math_tool("math_evaluate", {"expression": "1+" * 600})
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        result = await handle_math_tool("math_unknown", {})
        assert "Unknown" in result[0].text
