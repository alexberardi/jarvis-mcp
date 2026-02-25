"""Tests for MCP Docker tool definitions and handlers."""

import asyncio
from unittest.mock import patch

import pytest

from jarvis_mcp.tools.docker import DOCKER_TOOLS, handle_docker_tool


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    def test_tool_count(self):
        assert len(DOCKER_TOOLS) == 8

    def test_tool_names(self):
        names = {t.name for t in DOCKER_TOOLS}
        expected = {
            "docker_ps",
            "docker_logs",
            "docker_restart",
            "docker_stop",
            "docker_start",
            "docker_compose_up",
            "docker_compose_down",
            "docker_compose_list",
        }
        assert names == expected

    def test_all_tools_have_input_schema(self):
        for tool in DOCKER_TOOLS:
            assert tool.inputSchema is not None
            assert tool.inputSchema["type"] == "object"

    def test_docker_logs_requires_name(self):
        tool = next(t for t in DOCKER_TOOLS if t.name == "docker_logs")
        assert "name" in tool.inputSchema.get("required", [])

    def test_docker_restart_requires_name(self):
        tool = next(t for t in DOCKER_TOOLS if t.name == "docker_restart")
        assert "name" in tool.inputSchema.get("required", [])

    def test_docker_compose_up_requires_service(self):
        tool = next(t for t in DOCKER_TOOLS if t.name == "docker_compose_up")
        assert "service" in tool.inputSchema.get("required", [])

    def test_docker_compose_down_requires_service(self):
        tool = next(t for t in DOCKER_TOOLS if t.name == "docker_compose_down")
        assert "service" in tool.inputSchema.get("required", [])

    def test_docker_ps_no_required(self):
        tool = next(t for t in DOCKER_TOOLS if t.name == "docker_ps")
        assert "required" not in tool.inputSchema

    def test_docker_compose_list_no_required(self):
        tool = next(t for t in DOCKER_TOOLS if t.name == "docker_compose_list")
        assert "required" not in tool.inputSchema


# ---------------------------------------------------------------------------
# Handler routing
# ---------------------------------------------------------------------------


class TestHandlerRouting:
    def test_unknown_tool(self):
        result = asyncio.run(handle_docker_tool("docker_unknown", {}))
        assert len(result) == 1
        assert "Unknown" in result[0].text

    def test_docker_ps(self):
        containers = [
            {"name": "jarvis-auth", "status": "running", "image": "jarvis-auth:latest", "ports": "7701->7701/tcp"},
        ]
        with patch("jarvis_mcp.tools.docker.docker_service.list_containers", return_value=containers):
            result = asyncio.run(handle_docker_tool("docker_ps", {}))

        assert len(result) == 1
        assert "jarvis-auth" in result[0].text
        assert "running" in result[0].text

    def test_docker_ps_empty(self):
        with patch("jarvis_mcp.tools.docker.docker_service.list_containers", return_value=[]):
            result = asyncio.run(handle_docker_tool("docker_ps", {}))

        assert "No jarvis containers" in result[0].text

    def test_docker_ps_passes_all_flag(self):
        with patch("jarvis_mcp.tools.docker.docker_service.list_containers", return_value=[]) as mock_list:
            asyncio.run(handle_docker_tool("docker_ps", {"all": True}))
            mock_list.assert_called_once_with(show_all=True)

    def test_docker_logs(self):
        with patch("jarvis_mcp.tools.docker.docker_service.get_container_logs", return_value="INFO started"):
            result = asyncio.run(handle_docker_tool("docker_logs", {"name": "auth"}))

        assert "INFO started" in result[0].text

    def test_docker_logs_empty_name(self):
        result = asyncio.run(handle_docker_tool("docker_logs", {"name": ""}))
        assert "required" in result[0].text.lower()

    def test_docker_logs_no_match(self):
        with patch(
            "jarvis_mcp.tools.docker.docker_service.get_container_logs",
            side_effect=ValueError("No jarvis container matching 'xyz'"),
        ):
            result = asyncio.run(handle_docker_tool("docker_logs", {"name": "xyz"}))

        assert "No jarvis container" in result[0].text

    def test_docker_restart(self):
        with patch(
            "jarvis_mcp.tools.docker.docker_service.restart_container",
            return_value="Container 'jarvis-auth' restarted successfully.",
        ):
            result = asyncio.run(handle_docker_tool("docker_restart", {"name": "auth"}))

        assert "restarted" in result[0].text

    def test_docker_stop(self):
        with patch(
            "jarvis_mcp.tools.docker.docker_service.stop_container",
            return_value="Container 'jarvis-auth' stopped successfully.",
        ):
            result = asyncio.run(handle_docker_tool("docker_stop", {"name": "auth"}))

        assert "stopped" in result[0].text

    def test_docker_start(self):
        with patch(
            "jarvis_mcp.tools.docker.docker_service.start_container",
            return_value="Container 'jarvis-auth' started successfully.",
        ):
            result = asyncio.run(handle_docker_tool("docker_start", {"name": "auth"}))

        assert "started" in result[0].text

    def test_docker_compose_up(self):
        with patch(
            "jarvis_mcp.tools.docker.docker_service.compose_up",
            return_value="Creating jarvis-auth ... done",
        ):
            result = asyncio.run(handle_docker_tool("docker_compose_up", {"service": "auth"}))

        assert "done" in result[0].text

    def test_docker_compose_up_empty_service(self):
        result = asyncio.run(handle_docker_tool("docker_compose_up", {"service": ""}))
        assert "required" in result[0].text.lower()

    def test_docker_compose_down(self):
        with patch(
            "jarvis_mcp.tools.docker.docker_service.compose_down",
            return_value="Stopping jarvis-auth ... done",
        ):
            result = asyncio.run(handle_docker_tool("docker_compose_down", {"service": "auth"}))

        assert "done" in result[0].text

    def test_docker_compose_list(self):
        services = [
            {"name": "jarvis-auth", "path": "/home/alex/jarvis/jarvis-auth"},
            {"name": "jarvis-tts", "path": "/home/alex/jarvis/jarvis-tts"},
        ]
        with patch("jarvis_mcp.tools.docker.docker_service.list_known_services", return_value=services):
            result = asyncio.run(handle_docker_tool("docker_compose_list", {}))

        assert "jarvis-auth" in result[0].text
        assert "jarvis-tts" in result[0].text

    def test_docker_compose_list_empty(self):
        with patch("jarvis_mcp.tools.docker.docker_service.list_known_services", return_value=[]):
            result = asyncio.run(handle_docker_tool("docker_compose_list", {}))

        assert "No jarvis services" in result[0].text

    def test_docker_logs_passes_since(self):
        with patch("jarvis_mcp.tools.docker.docker_service.get_container_logs", return_value="logs") as mock_logs:
            asyncio.run(handle_docker_tool("docker_logs", {"name": "auth", "lines": 50, "since": "1h"}))
            mock_logs.assert_called_once_with("auth", lines=50, since="1h")

    def test_compose_up_not_found(self):
        with patch(
            "jarvis_mcp.tools.docker.docker_service.compose_up",
            side_effect=ValueError("No compose file found"),
        ):
            result = asyncio.run(handle_docker_tool("docker_compose_up", {"service": "nonexistent"}))

        assert "No compose file" in result[0].text

    def test_write_tools_require_name(self):
        """Stop, start, restart all require non-empty name."""
        for tool_name in ("docker_stop", "docker_start", "docker_restart"):
            result = asyncio.run(handle_docker_tool(tool_name, {"name": ""}))
            assert "required" in result[0].text.lower(), f"{tool_name} should reject empty name"
