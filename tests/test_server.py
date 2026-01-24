"""Tests for MCP server."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent

from jarvis_mcp.server import get_enabled_tools, list_tools, call_tool


class TestGetEnabledTools:
    """Tests for get_enabled_tools function."""

    def test_logs_and_debug_enabled(self):
        """Test with logs and debug enabled."""
        with patch("jarvis_mcp.server.config") as mock_config:
            mock_config.is_enabled.side_effect = lambda x: x in ["logs", "debug"]

            tools = get_enabled_tools()

            # Should have tools from both groups
            tool_names = [t.name for t in tools]
            assert any(name.startswith("logs_") for name in tool_names)
            assert any(name.startswith("debug_") for name in tool_names)

    def test_only_logs_enabled(self):
        """Test with only logs enabled."""
        with patch("jarvis_mcp.server.config") as mock_config:
            mock_config.is_enabled.side_effect = lambda x: x == "logs"

            tools = get_enabled_tools()

            tool_names = [t.name for t in tools]
            assert any(name.startswith("logs_") for name in tool_names)
            assert not any(name.startswith("debug_") for name in tool_names)

    def test_only_debug_enabled(self):
        """Test with only debug enabled."""
        with patch("jarvis_mcp.server.config") as mock_config:
            mock_config.is_enabled.side_effect = lambda x: x == "debug"

            tools = get_enabled_tools()

            tool_names = [t.name for t in tools]
            assert not any(name.startswith("logs_") for name in tool_names)
            assert any(name.startswith("debug_") for name in tool_names)

    def test_no_tools_enabled(self):
        """Test with no tools enabled."""
        with patch("jarvis_mcp.server.config") as mock_config:
            mock_config.is_enabled.return_value = False

            tools = get_enabled_tools()

            assert tools == []


class TestListTools:
    """Tests for list_tools handler."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_enabled(self):
        """Test that list_tools returns enabled tools."""
        with patch("jarvis_mcp.server.config") as mock_config:
            mock_config.is_enabled.side_effect = lambda x: x in ["logs", "debug"]

            tools = await list_tools()

            assert len(tools) > 0
            tool_names = [t.name for t in tools]
            assert "logs_query" in tool_names
            assert "debug_health" in tool_names


class TestCallTool:
    """Tests for call_tool handler."""

    @pytest.mark.asyncio
    async def test_call_logs_tool(self):
        """Test calling a logs tool."""
        with patch("jarvis_mcp.server.config") as mock_config, \
             patch("jarvis_mcp.server.handle_logs_tool", new_callable=AsyncMock) as mock_handler:

            mock_config.is_enabled.return_value = True
            mock_handler.return_value = [TextContent(type="text", text="result")]

            result = await call_tool("logs_query", {"service": "test"})

            mock_handler.assert_called_once_with("logs_query", {"service": "test"})
            assert len(result) == 1
            assert result[0].text == "result"

    @pytest.mark.asyncio
    async def test_call_logs_tool_disabled(self):
        """Test calling logs tool when disabled."""
        with patch("jarvis_mcp.server.config") as mock_config:
            mock_config.is_enabled.return_value = False

            result = await call_tool("logs_query", {})

            assert len(result) == 1
            assert "not enabled" in result[0].text

    @pytest.mark.asyncio
    async def test_call_debug_tool(self):
        """Test calling a debug tool."""
        with patch("jarvis_mcp.server.config") as mock_config, \
             patch("jarvis_mcp.server.handle_debug_tool", new_callable=AsyncMock) as mock_handler:

            mock_config.is_enabled.return_value = True
            mock_handler.return_value = [TextContent(type="text", text="health status")]

            result = await call_tool("debug_health", {})

            mock_handler.assert_called_once_with("debug_health", {})
            assert result[0].text == "health status"

    @pytest.mark.asyncio
    async def test_call_debug_tool_disabled(self):
        """Test calling debug tool when disabled."""
        with patch("jarvis_mcp.server.config") as mock_config:
            mock_config.is_enabled.return_value = False

            result = await call_tool("debug_health", {})

            assert "not enabled" in result[0].text

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """Test calling an unknown tool."""
        result = await call_tool("unknown_tool", {})

        assert len(result) == 1
        assert "Unknown tool" in result[0].text
        assert "unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_routes_correctly(self):
        """Test that tools are routed to correct handlers."""
        with patch("jarvis_mcp.server.config") as mock_config, \
             patch("jarvis_mcp.server.handle_logs_tool", new_callable=AsyncMock) as logs_handler, \
             patch("jarvis_mcp.server.handle_debug_tool", new_callable=AsyncMock) as debug_handler:

            mock_config.is_enabled.return_value = True
            logs_handler.return_value = [TextContent(type="text", text="logs")]
            debug_handler.return_value = [TextContent(type="text", text="debug")]

            # Call logs tool
            await call_tool("logs_tail", {"service": "test"})
            logs_handler.assert_called_with("logs_tail", {"service": "test"})
            debug_handler.assert_not_called()

            logs_handler.reset_mock()

            # Call debug tool
            await call_tool("debug_service_info", {"service": "logs"})
            debug_handler.assert_called_with("debug_service_info", {"service": "logs"})
            logs_handler.assert_not_called()
