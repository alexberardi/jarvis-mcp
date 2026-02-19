"""Tests for MCP command tool definitions and handlers."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from jarvis_mcp.tools.command import COMMAND_TOOLS, handle_command_tool


class TestToolDefinitions:
    """Tests for COMMAND_TOOLS definitions."""

    def test_tool_count(self):
        """Has exactly 3 tools."""
        assert len(COMMAND_TOOLS) == 3

    def test_tool_names(self):
        """Tools have correct names."""
        names = {t.name for t in COMMAND_TOOLS}
        assert names == {"command_test", "command_test_suite", "command_test_list"}

    def test_command_test_schema(self):
        """command_test has required voice_command parameter."""
        tool = next(t for t in COMMAND_TOOLS if t.name == "command_test")
        props = tool.inputSchema["properties"]
        assert "voice_command" in props
        assert "voice_command" in tool.inputSchema.get("required", [])

    def test_command_test_suite_schema(self):
        """command_test_suite has optional categories parameter."""
        tool = next(t for t in COMMAND_TOOLS if t.name == "command_test_suite")
        props = tool.inputSchema["properties"]
        assert "categories" in props
        # categories is not required
        assert "categories" not in tool.inputSchema.get("required", [])

    def test_command_test_list_schema(self):
        """command_test_list has optional category parameter."""
        tool = next(t for t in COMMAND_TOOLS if t.name == "command_test_list")
        props = tool.inputSchema["properties"]
        assert "category" in props


class TestHandlerRouting:
    """Tests for handle_command_tool routing."""

    def test_routes_to_command_test(self):
        """command_test routes to single command handler."""
        mock_result = {
            "command_name": "get_weather",
            "parameters": {"city": "Miami"},
            "stop_reason": "tool_calls",
        }

        with patch(
            "jarvis_mcp.tools.command.test_single_command",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = asyncio.run(
                handle_command_tool("command_test", {"voice_command": "What's the weather in Miami?"})
            )

        assert len(result) == 1
        text = result[0].text
        parsed = json.loads(text)
        assert parsed["command_name"] == "get_weather"

    def test_routes_to_command_test_suite(self):
        """command_test_suite routes to suite handler."""
        mock_result = {
            "summary": {"total": 4, "passed": 4, "failed": 0, "errors": 0, "success_rate": 100.0},
            "results": [],
            "analysis": {},
        }

        with patch(
            "jarvis_mcp.tools.command.test_command_suite",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = asyncio.run(
                handle_command_tool("command_test_suite", {})
            )

        assert len(result) == 1
        text = result[0].text
        parsed = json.loads(text)
        assert parsed["summary"]["total"] == 4

    def test_routes_to_command_test_list(self):
        """command_test_list routes to list handler."""
        result = asyncio.run(
            handle_command_tool("command_test_list", {})
        )

        assert len(result) == 1
        text = result[0].text
        parsed = json.loads(text)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert "voice_command" in parsed[0]

    def test_unknown_tool(self):
        """Unknown tool name returns error message."""
        result = asyncio.run(
            handle_command_tool("command_unknown", {})
        )

        assert len(result) == 1
        assert "Unknown" in result[0].text

    def test_list_filters_by_category(self):
        """command_test_list filters by category."""
        result = asyncio.run(
            handle_command_tool("command_test_list", {"category": "jokes"})
        )

        parsed = json.loads(result[0].text)
        assert all(tc["category"] == "jokes" for tc in parsed)
        assert len(parsed) == 4

    def test_suite_passes_categories(self):
        """command_test_suite passes categories to service."""
        mock_result = {
            "summary": {"total": 7, "passed": 7, "failed": 0, "errors": 0, "success_rate": 100.0},
            "results": [],
            "analysis": {},
        }

        with patch(
            "jarvis_mcp.tools.command.test_command_suite",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_suite:
            asyncio.run(
                handle_command_tool("command_test_suite", {"categories": ["weather"]})
            )

            mock_suite.assert_called_once()
            call_kwargs = mock_suite.call_args.kwargs
            assert call_kwargs["categories"] == ["weather"]
