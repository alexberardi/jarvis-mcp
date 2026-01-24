"""Tests for health tools."""

import pytest
from mcp.types import TextContent

from jarvis_mcp.tools.health import (
    HEALTH_TOOLS,
    SERVICES,
    handle_health_tool,
)


class TestHealthToolsDefinition:
    """Tests for health tool definitions."""

    def test_health_check_tool_exists(self):
        """Test health_check tool is defined."""
        tool_names = [t.name for t in HEALTH_TOOLS]
        assert "health_check" in tool_names

    def test_health_service_tool_exists(self):
        """Test health_service tool is defined."""
        tool_names = [t.name for t in HEALTH_TOOLS]
        assert "health_service" in tool_names

    def test_health_check_schema(self):
        """Test health_check has correct schema."""
        tool = next(t for t in HEALTH_TOOLS if t.name == "health_check")
        assert tool.inputSchema["type"] == "object"
        assert "services" in tool.inputSchema["properties"]

    def test_health_service_schema(self):
        """Test health_service has correct schema."""
        tool = next(t for t in HEALTH_TOOLS if t.name == "health_service")
        assert tool.inputSchema["type"] == "object"
        assert "service" in tool.inputSchema["properties"]
        assert "service" in tool.inputSchema["required"]


class TestServicesConfig:
    """Tests for services configuration."""

    def test_all_services_defined(self):
        """Test expected services are defined."""
        expected = [
            "jarvis-auth",
            "jarvis-command-center",
            "jarvis-logs",
            "jarvis-recipes",
            "jarvis-whisper",
            "jarvis-ocr",
            "llm-proxy",
        ]
        for service in expected:
            assert service in SERVICES

    def test_service_config_structure(self):
        """Test each service has url_attr and health_path."""
        for name, config in SERVICES.items():
            assert len(config) == 2, f"{name} should have (url_attr, health_path)"
            url_attr, health_path = config
            assert isinstance(url_attr, str)
            assert health_path.startswith("/")


class TestHandleHealthTool:
    """Tests for handle_health_tool routing."""

    @pytest.mark.asyncio
    async def test_routes_to_health_check(self, httpx_mock):
        """Test health_check routes correctly."""
        httpx_mock.add_response(url="http://localhost:8007/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:8002/api/v0/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:8006/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:8001/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:9999/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:5009/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:8000/v1/health", json={"status": "ok"})

        result = await handle_health_tool("health_check", {})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Jarvis Health Check" in result[0].text

    @pytest.mark.asyncio
    async def test_routes_to_health_service(self, httpx_mock):
        """Test health_service routes correctly."""
        httpx_mock.add_response(
            url="http://localhost:8007/health",
            json={"status": "ok"}
        )

        result = await handle_health_tool("health_service", {"service": "jarvis-auth"})
        assert len(result) == 1
        assert "jarvis-auth Health" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test unknown tool returns error."""
        result = await handle_health_tool("health_unknown", {})
        assert "Unknown health tool" in result[0].text


class TestHealthCheck:
    """Tests for health_check tool."""

    @pytest.mark.asyncio
    async def test_check_all_services(self, httpx_mock):
        """Test checking all services."""
        httpx_mock.add_response(url="http://localhost:8007/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:8002/api/v0/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:8006/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:8001/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:9999/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:5009/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:8000/v1/health", json={"status": "ok"})

        result = await handle_health_tool("health_check", {})
        assert "7/7 services healthy" in result[0].text

    @pytest.mark.asyncio
    async def test_check_specific_services(self, httpx_mock):
        """Test checking specific services only."""
        httpx_mock.add_response(url="http://localhost:8007/health", json={"status": "ok"})
        httpx_mock.add_response(url="http://localhost:8006/health", json={"status": "ok"})

        result = await handle_health_tool("health_check", {
            "services": ["jarvis-auth", "jarvis-logs"]
        })
        assert "2/2 services healthy" in result[0].text

    @pytest.mark.asyncio
    async def test_unhealthy_service(self, httpx_mock):
        """Test handling unhealthy service."""
        httpx_mock.add_response(url="http://localhost:8007/health", status_code=500)

        result = await handle_health_tool("health_check", {
            "services": ["jarvis-auth"]
        })
        assert "0/1 services healthy" in result[0].text
        assert "HTTP 500" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_service_in_list(self, httpx_mock):
        """Test unknown service in services list."""
        result = await handle_health_tool("health_check", {
            "services": ["unknown-service"]
        })
        assert "Unknown service" in result[0].text


class TestHealthService:
    """Tests for health_service tool."""

    @pytest.mark.asyncio
    async def test_check_single_service(self, httpx_mock):
        """Test checking a single service."""
        httpx_mock.add_response(
            url="http://localhost:8002/api/v0/health",
            json={"status": "healthy", "services": {"db": "ok"}}
        )

        result = await handle_health_tool("health_service", {
            "service": "jarvis-command-center"
        })
        assert "jarvis-command-center Health" in result[0].text
        assert "Status: 200" in result[0].text
        assert "healthy" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_service(self):
        """Test checking unknown service."""
        result = await handle_health_tool("health_service", {
            "service": "unknown-service"
        })
        assert "Unknown service" in result[0].text

    @pytest.mark.asyncio
    async def test_connection_error(self, httpx_mock):
        """Test handling connection error."""
        import httpx
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

        result = await handle_health_tool("health_service", {
            "service": "jarvis-auth"
        })
        assert "Connection failed" in result[0].text
