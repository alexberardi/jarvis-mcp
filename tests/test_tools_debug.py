"""Tests for debug tools."""

from unittest.mock import patch

import pytest
from pytest_httpx import HTTPXMock

from jarvis_mcp.tools.debug import (
    DEBUG_TOOLS,
    KNOWN_SERVICES,
    handle_debug_tool,
    _debug_health,
    _debug_service_info,
)


class TestDebugToolsDefinition:
    """Tests for debug tool definitions."""

    def test_tools_count(self):
        """Test expected number of tools."""
        assert len(DEBUG_TOOLS) == 2

    def test_tool_names(self):
        """Test tool names."""
        names = [t.name for t in DEBUG_TOOLS]
        assert "debug_health" in names
        assert "debug_service_info" in names

    def test_debug_health_schema(self):
        """Test debug_health has correct schema."""
        tool = next(t for t in DEBUG_TOOLS if t.name == "debug_health")
        props = tool.inputSchema["properties"]
        assert "services" in props
        assert props["services"]["type"] == "array"

    def test_debug_service_info_schema(self):
        """Test debug_service_info has required service field."""
        tool = next(t for t in DEBUG_TOOLS if t.name == "debug_service_info")
        assert "service" in tool.inputSchema["required"]
        assert "enum" in tool.inputSchema["properties"]["service"]


class TestKnownServices:
    """Tests for KNOWN_SERVICES configuration."""

    def test_known_services_structure(self):
        """Test known services have correct structure."""
        for name, info in KNOWN_SERVICES.items():
            assert "url_key" in info
            assert "health" in info
            assert info["health"].startswith("/")

    def test_expected_services(self):
        """Test expected services are defined."""
        assert "logs" in KNOWN_SERVICES
        assert "auth" in KNOWN_SERVICES
        assert "recipes" in KNOWN_SERVICES
        assert "command-center" in KNOWN_SERVICES


class TestHandleDebugTool:
    """Tests for handle_debug_tool dispatcher."""

    @pytest.mark.asyncio
    async def test_routes_to_debug_health(self, httpx_mock: HTTPXMock):
        """Test routing to debug_health."""
        with patch("jarvis_mcp.tools.debug.config") as mock_config:
            mock_config.logs_url = "http://logs:8006"
            mock_config.auth_url = "http://auth:8007"
            mock_config.recipes_url = "http://recipes:8001"
            mock_config.command_center_url = "http://cc:8002"

            httpx_mock.add_response(url="http://logs:8006/health", status_code=200)
            httpx_mock.add_response(url="http://auth:8007/health", status_code=200)
            httpx_mock.add_response(url="http://recipes:8001/health", status_code=200)
            httpx_mock.add_response(url="http://cc:8002/api/v0/health", status_code=200)

            result = await handle_debug_tool("debug_health", {})
            assert "Health Status" in result[0].text

    @pytest.mark.asyncio
    async def test_routes_to_debug_service_info(self, httpx_mock: HTTPXMock):
        """Test routing to debug_service_info."""
        with patch("jarvis_mcp.tools.debug.config") as mock_config:
            mock_config.logs_url = "http://logs:8006"

            httpx_mock.add_response(
                url="http://logs:8006/health",
                status_code=200,
                json={"status": "healthy"},
            )

            result = await handle_debug_tool("debug_service_info", {"service": "logs"})
            assert "logs" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test handling unknown tool."""
        result = await handle_debug_tool("debug_unknown", {})
        assert "Unknown debug tool" in result[0].text


class TestDebugHealth:
    """Tests for debug_health implementation."""

    @pytest.mark.asyncio
    async def test_health_all_up(self, httpx_mock: HTTPXMock):
        """Test health check when all services are up."""
        with patch("jarvis_mcp.tools.debug.config") as mock_config:
            mock_config.logs_url = "http://logs:8006"
            mock_config.auth_url = "http://auth:8007"
            mock_config.recipes_url = "http://recipes:8001"
            mock_config.command_center_url = "http://cc:8002"

            httpx_mock.add_response(url="http://logs:8006/health", status_code=200)
            httpx_mock.add_response(url="http://auth:8007/health", status_code=200)
            httpx_mock.add_response(url="http://recipes:8001/health", status_code=200)
            httpx_mock.add_response(url="http://cc:8002/api/v0/health", status_code=200)

            result = await handle_debug_tool("debug_health", {})

            assert "logs: UP" in result[0].text
            assert "auth: UP" in result[0].text
            assert "recipes: UP" in result[0].text
            assert "command-center: UP" in result[0].text

    @pytest.mark.asyncio
    async def test_health_some_down(self, httpx_mock: HTTPXMock):
        """Test health check when some services are down."""
        import httpx

        with patch("jarvis_mcp.tools.debug.config") as mock_config:
            mock_config.logs_url = "http://logs:8006"
            mock_config.auth_url = "http://auth:8007"
            mock_config.recipes_url = "http://recipes:8001"
            mock_config.command_center_url = "http://cc:8002"

            httpx_mock.add_response(url="http://logs:8006/health", status_code=200)
            httpx_mock.add_exception(httpx.ConnectError("Connection refused"), url="http://auth:8007/health")
            httpx_mock.add_response(url="http://recipes:8001/health", status_code=500)
            httpx_mock.add_response(url="http://cc:8002/api/v0/health", status_code=200)

            result = await handle_debug_tool("debug_health", {})

            assert "logs: UP" in result[0].text
            assert "auth: DOWN" in result[0].text
            assert "recipes: DEGRADED" in result[0].text
            assert "command-center: UP" in result[0].text

    @pytest.mark.asyncio
    async def test_health_specific_services(self, httpx_mock: HTTPXMock):
        """Test health check for specific services."""
        with patch("jarvis_mcp.tools.debug.config") as mock_config:
            mock_config.logs_url = "http://logs:8006"
            mock_config.auth_url = "http://auth:8007"

            httpx_mock.add_response(url="http://logs:8006/health", status_code=200)
            httpx_mock.add_response(url="http://auth:8007/health", status_code=200)

            result = await handle_debug_tool("debug_health", {"services": ["logs", "auth"]})

            assert "logs: UP" in result[0].text
            assert "auth: UP" in result[0].text
            # Should not check other services
            assert "recipes" not in result[0].text

    @pytest.mark.asyncio
    async def test_health_unknown_service(self, httpx_mock: HTTPXMock):
        """Test health check with unknown service."""
        with patch("jarvis_mcp.tools.debug.config"):
            result = await handle_debug_tool("debug_health", {"services": ["unknown-svc"]})
            assert "unknown service" in result[0].text


class TestDebugServiceInfo:
    """Tests for debug_service_info implementation."""

    @pytest.mark.asyncio
    async def test_service_info_success(self, httpx_mock: HTTPXMock):
        """Test getting service info successfully."""
        with patch("jarvis_mcp.tools.debug.config") as mock_config:
            mock_config.logs_url = "http://logs:8006"

            httpx_mock.add_response(
                url="http://logs:8006/health",
                status_code=200,
                json={
                    "status": "healthy",
                    "timestamp": "2024-01-15T12:00:00",
                    "services": {"loki": "available"},
                },
            )

            result = await handle_debug_tool("debug_service_info", {"service": "logs"})

            assert "logs" in result[0].text
            assert "http://logs:8006" in result[0].text
            assert "healthy" in result[0].text
            assert "loki" in result[0].text

    @pytest.mark.asyncio
    async def test_service_info_unreachable(self, httpx_mock: HTTPXMock):
        """Test service info when service is unreachable."""
        import httpx

        with patch("jarvis_mcp.tools.debug.config") as mock_config:
            mock_config.auth_url = "http://auth:8007"

            httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

            result = await handle_debug_tool("debug_service_info", {"service": "auth"})

            assert "auth" in result[0].text
            assert "UNREACHABLE" in result[0].text

    @pytest.mark.asyncio
    async def test_service_info_unknown_service(self):
        """Test service info for unknown service."""
        result = await handle_debug_tool("debug_service_info", {"service": "unknown"})
        assert "Unknown service" in result[0].text

    @pytest.mark.asyncio
    async def test_service_info_non_json_response(self, httpx_mock: HTTPXMock):
        """Test service info when health returns non-JSON."""
        with patch("jarvis_mcp.tools.debug.config") as mock_config:
            mock_config.recipes_url = "http://recipes:8001"

            httpx_mock.add_response(
                url="http://recipes:8001/health",
                status_code=200,
                text="OK",
            )

            result = await handle_debug_tool("debug_service_info", {"service": "recipes"})

            # Should still return basic info without error
            assert "recipes" in result[0].text
            assert "Status: 200" in result[0].text

    @pytest.mark.asyncio
    async def test_service_info_shows_nested_health(self, httpx_mock: HTTPXMock):
        """Test that nested health data is displayed."""
        with patch("jarvis_mcp.tools.debug.config") as mock_config:
            mock_config.logs_url = "http://logs:8006"

            httpx_mock.add_response(
                url="http://logs:8006/health",
                status_code=200,
                json={
                    "status": "healthy",
                    "services": {
                        "database": "connected",
                        "cache": "available",
                    },
                },
            )

            result = await handle_debug_tool("debug_service_info", {"service": "logs"})

            assert "database" in result[0].text
            assert "connected" in result[0].text
            assert "cache" in result[0].text
            assert "available" in result[0].text
