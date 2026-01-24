"""Tests for logs tools."""

import re
from datetime import datetime
from unittest.mock import patch

import pytest
from pytest_httpx import HTTPXMock

from jarvis_mcp.tools.logs import (
    LOGS_TOOLS,
    handle_logs_tool,
    _logs_query,
    _logs_tail,
    _logs_errors,
    _logs_services,
    _format_logs,
)


class TestLogsToolsDefinition:
    """Tests for logs tool definitions."""

    def test_tools_count(self):
        """Test expected number of tools."""
        assert len(LOGS_TOOLS) == 4

    def test_tool_names(self):
        """Test tool names."""
        names = [t.name for t in LOGS_TOOLS]
        assert "logs_query" in names
        assert "logs_tail" in names
        assert "logs_errors" in names
        assert "logs_services" in names

    def test_logs_query_schema(self):
        """Test logs_query has correct schema."""
        tool = next(t for t in LOGS_TOOLS if t.name == "logs_query")
        props = tool.inputSchema["properties"]
        assert "service" in props
        assert "level" in props
        assert "search" in props
        assert "since_minutes" in props
        assert "limit" in props

    def test_logs_tail_schema(self):
        """Test logs_tail has required service field."""
        tool = next(t for t in LOGS_TOOLS if t.name == "logs_tail")
        assert "service" in tool.inputSchema["required"]

    def test_logs_errors_schema(self):
        """Test logs_errors has correct schema."""
        tool = next(t for t in LOGS_TOOLS if t.name == "logs_errors")
        props = tool.inputSchema["properties"]
        assert "since_minutes" in props
        assert "service" in props

    def test_logs_services_schema(self):
        """Test logs_services has empty properties."""
        tool = next(t for t in LOGS_TOOLS if t.name == "logs_services")
        assert tool.inputSchema["properties"] == {}


class TestHandleLogsTool:
    """Tests for handle_logs_tool dispatcher."""

    @pytest.mark.asyncio
    async def test_routes_to_logs_query(self, httpx_mock: HTTPXMock):
        """Test routing to logs_query."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[],
            )

            result = await handle_logs_tool("logs_query", {})
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_routes_to_logs_tail(self, httpx_mock: HTTPXMock):
        """Test routing to logs_tail."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[],
            )

            result = await handle_logs_tool("logs_tail", {"service": "test"})
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_routes_to_logs_errors(self, httpx_mock: HTTPXMock):
        """Test routing to logs_errors."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[],
            )

            result = await handle_logs_tool("logs_errors", {})
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_routes_to_logs_services(self, httpx_mock: HTTPXMock):
        """Test routing to logs_services."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url="http://test:8006/api/v0/services",
                json=["svc1", "svc2"],
            )

            result = await handle_logs_tool("logs_services", {})
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test handling unknown tool."""
        result = await handle_logs_tool("logs_unknown", {})
        assert "Unknown logs tool" in result[0].text


class TestLogsQuery:
    """Tests for logs_query implementation."""

    @pytest.mark.asyncio
    async def test_query_with_filters(self, httpx_mock: HTTPXMock):
        """Test query passes filters correctly."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {"X-Jarvis-App-Id": "test"}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[
                    {
                        "timestamp": "2024-01-15T12:00:00",
                        "service": "test",
                        "level": "ERROR",
                        "message": "Error occurred",
                        "context": None,
                    }
                ],
            )

            result = await handle_logs_tool(
                "logs_query",
                {"service": "test", "level": "ERROR", "limit": 50},
            )

            request = httpx_mock.get_request()
            assert "service=test" in str(request.url)
            assert "level=ERROR" in str(request.url)
            assert "limit=50" in str(request.url)

    @pytest.mark.asyncio
    async def test_query_includes_auth_headers(self, httpx_mock: HTTPXMock):
        """Test query includes auth headers."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {
                "X-Jarvis-App-Id": "my-app",
                "X-Jarvis-App-Key": "my-key",
            }

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[],
            )

            await handle_logs_tool("logs_query", {})

            request = httpx_mock.get_request()
            assert request.headers["X-Jarvis-App-Id"] == "my-app"
            assert request.headers["X-Jarvis-App-Key"] == "my-key"

    @pytest.mark.asyncio
    async def test_query_connection_error(self, httpx_mock: HTTPXMock):
        """Test handling connection errors."""
        import httpx

        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

            result = await handle_logs_tool("logs_query", {})
            assert "Error connecting" in result[0].text

    @pytest.mark.asyncio
    async def test_query_http_error(self, httpx_mock: HTTPXMock):
        """Test handling HTTP errors."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                status_code=500,
            )

            result = await handle_logs_tool("logs_query", {})
            assert "server error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_query_limit_capped(self, httpx_mock: HTTPXMock):
        """Test that limit is capped at 200."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[],
            )

            await handle_logs_tool("logs_query", {"limit": 500})

            request = httpx_mock.get_request()
            assert "limit=200" in str(request.url)


class TestLogsTail:
    """Tests for logs_tail implementation."""

    @pytest.mark.asyncio
    async def test_tail_with_service(self, httpx_mock: HTTPXMock):
        """Test tail with service parameter."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[
                    {
                        "timestamp": "2024-01-15T12:00:00",
                        "service": "my-service",
                        "level": "INFO",
                        "message": "Log entry",
                        "context": None,
                    }
                ],
            )

            result = await handle_logs_tool("logs_tail", {"service": "my-service"})

            request = httpx_mock.get_request()
            assert "service=my-service" in str(request.url)
            assert "Last" in result[0].text

    @pytest.mark.asyncio
    async def test_tail_lines_capped(self, httpx_mock: HTTPXMock):
        """Test that lines is capped at 100."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[],
            )

            await handle_logs_tool("logs_tail", {"service": "test", "lines": 500})

            request = httpx_mock.get_request()
            assert "limit=100" in str(request.url)


class TestLogsErrors:
    """Tests for logs_errors implementation."""

    @pytest.mark.asyncio
    async def test_errors_queries_error_level(self, httpx_mock: HTTPXMock):
        """Test that errors queries ERROR level."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[],
            )

            result = await handle_logs_tool("logs_errors", {})

            request = httpx_mock.get_request()
            assert "level=ERROR" in str(request.url)
            assert "No errors found" in result[0].text

    @pytest.mark.asyncio
    async def test_errors_with_service_filter(self, httpx_mock: HTTPXMock):
        """Test errors with service filter."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url=re.compile(r"http://test:8006/api/v0/logs.*"),
                json=[
                    {
                        "timestamp": "2024-01-15T12:00:00",
                        "service": "my-service",
                        "level": "ERROR",
                        "message": "Error!",
                        "context": None,
                    }
                ],
            )

            result = await handle_logs_tool("logs_errors", {"service": "my-service"})

            request = httpx_mock.get_request()
            assert "service=my-service" in str(request.url)
            assert "Found 1 errors" in result[0].text


class TestLogsServices:
    """Tests for logs_services implementation."""

    @pytest.mark.asyncio
    async def test_services_returns_list(self, httpx_mock: HTTPXMock):
        """Test services returns formatted list."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url="http://test:8006/api/v0/services",
                json=["svc1", "svc2", "svc3"],
            )

            result = await handle_logs_tool("logs_services", {})

            assert "svc1" in result[0].text
            assert "svc2" in result[0].text
            assert "svc3" in result[0].text

    @pytest.mark.asyncio
    async def test_services_empty(self, httpx_mock: HTTPXMock):
        """Test services when none exist."""
        with patch("jarvis_mcp.tools.logs.config") as mock_config:
            mock_config.logs_url = "http://test:8006"
            mock_config.get_auth_headers.return_value = {}

            httpx_mock.add_response(
                url="http://test:8006/api/v0/services",
                json=[],
            )

            result = await handle_logs_tool("logs_services", {})
            assert "No services" in result[0].text


class TestFormatLogs:
    """Tests for _format_logs helper."""

    def test_format_empty(self):
        """Test formatting empty logs."""
        result = _format_logs([])
        assert result == "No logs found."

    def test_format_single_log(self):
        """Test formatting single log."""
        logs = [
            {
                "timestamp": "2024-01-15T12:00:00.123456",
                "service": "test",
                "level": "INFO",
                "message": "Test message",
                "context": None,
            }
        ]
        result = _format_logs(logs)
        assert "[2024-01-15T12:00:00]" in result
        assert "[INFO]" in result
        assert "[test]" in result
        assert "Test message" in result

    def test_format_with_context(self):
        """Test formatting log with context."""
        logs = [
            {
                "timestamp": "2024-01-15T12:00:00",
                "service": "test",
                "level": "ERROR",
                "message": "Error occurred",
                "context": {"request_id": "abc123"},
            }
        ]
        result = _format_logs(logs)
        assert "Error occurred" in result
        assert "request_id" in result
        assert "abc123" in result

    def test_format_multiple_logs(self):
        """Test formatting multiple logs."""
        logs = [
            {"timestamp": "2024-01-15T12:00:00", "service": "svc1", "level": "INFO", "message": "Msg 1", "context": None},
            {"timestamp": "2024-01-15T12:01:00", "service": "svc2", "level": "ERROR", "message": "Msg 2", "context": None},
        ]
        result = _format_logs(logs)
        assert "Msg 1" in result
        assert "Msg 2" in result
        assert result.count("\n") >= 1
