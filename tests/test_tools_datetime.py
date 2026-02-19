"""Tests for datetime MCP tools."""

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from mcp.types import TextContent


class TestDatetimeToolDefinitions:
    """Tests for datetime tool definitions."""

    def test_tools_list_exists(self):
        from jarvis_mcp.tools.datetime import DATETIME_TOOLS
        assert isinstance(DATETIME_TOOLS, list)
        assert len(DATETIME_TOOLS) == 2

    def test_datetime_context_tool_definition(self):
        from jarvis_mcp.tools.datetime import DATETIME_TOOLS
        context_tool = next(t for t in DATETIME_TOOLS if t.name == "datetime_context")
        assert "timezone" in context_tool.inputSchema.get("properties", {})

    def test_datetime_resolve_tool_definition(self):
        from jarvis_mcp.tools.datetime import DATETIME_TOOLS
        resolve_tool = next(t for t in DATETIME_TOOLS if t.name == "datetime_resolve")
        assert "date_keys" in resolve_tool.inputSchema.get("properties", {})
        assert "date_keys" in resolve_tool.inputSchema.get("required", [])


class TestHandleDatetimeTool:
    """Tests for datetime tool dispatch."""

    @pytest.mark.asyncio
    async def test_routes_to_datetime_context(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_context", {})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert "current" in data

    @pytest.mark.asyncio
    async def test_routes_to_datetime_resolve(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {
            "date_keys": ["tomorrow"],
            "timezone": "UTC",
        })
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert "resolved" in data

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_unknown", {})
        assert "Unknown" in result[0].text


class TestDatetimeContextTool:
    """Tests for the datetime_context tool."""

    @pytest.mark.asyncio
    async def test_returns_full_context(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_context", {})
        data = json.loads(result[0].text)
        assert "current" in data
        assert "relative_dates" in data
        assert "weekdays" in data
        assert "timezone" in data

    @pytest.mark.asyncio
    async def test_respects_timezone_param(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_context", {
            "timezone": "America/New_York"
        })
        data = json.loads(result[0].text)
        assert data["timezone"]["user_timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_default_timezone_is_utc(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_context", {})
        data = json.loads(result[0].text)
        assert data["timezone"]["user_timezone"] == "UTC"


class TestDatetimeResolveTool:
    """Tests for the datetime_resolve tool."""

    @pytest.mark.asyncio
    async def test_resolves_tomorrow(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {
            "date_keys": ["tomorrow"],
            "timezone": "UTC",
        })
        data = json.loads(result[0].text)
        assert len(data["resolved"]) >= 1
        assert data["unresolved"] == []

    @pytest.mark.asyncio
    async def test_resolves_with_time_modifier(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {
            "date_keys": ["tomorrow", "morning"],
            "timezone": "UTC",
        })
        data = json.loads(result[0].text)
        # Should contain the combined tomorrow+morning result
        assert any("T07:00:00Z" in r for r in data["resolved"])

    @pytest.mark.asyncio
    async def test_reports_unresolved_keys(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {
            "date_keys": ["next_fortnight"],
            "timezone": "UTC",
        })
        data = json.loads(result[0].text)
        assert "next_fortnight" in data["unresolved"]

    @pytest.mark.asyncio
    async def test_empty_date_keys(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {
            "date_keys": [],
        })
        data = json.loads(result[0].text)
        assert data["resolved"] == []
        assert data["unresolved"] == []

    @pytest.mark.asyncio
    async def test_missing_date_keys_returns_error(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {})
        # Should return an error message
        assert "required" in result[0].text.lower() or "date_keys" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_relative_time_key(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {
            "date_keys": ["in_30_minutes"],
            "timezone": "UTC",
        })
        data = json.loads(result[0].text)
        assert len(data["resolved"]) == 1
        assert data["unresolved"] == []

    @pytest.mark.asyncio
    async def test_date_keys_not_a_list_returns_error(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {
            "date_keys": "tomorrow",
        })
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_date_keys_too_many_returns_error(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {
            "date_keys": [f"key_{i}" for i in range(101)],
        })
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_timezone_type_returns_error(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_resolve", {
            "date_keys": ["tomorrow"],
            "timezone": 12345,
        })
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_context_invalid_timezone_type_returns_error(self):
        from jarvis_mcp.tools.datetime import handle_datetime_tool
        result = await handle_datetime_tool("datetime_context", {
            "timezone": ["not", "a", "string"],
        })
        data = json.loads(result[0].text)
        assert "error" in data
