"""MCP tools for Docker container management."""

import logging
from typing import Any

from mcp.types import Tool, TextContent

from jarvis_mcp.services import docker_service

logger = logging.getLogger(__name__)

DOCKER_TOOLS: list[Tool] = [
    Tool(
        name="docker_ps",
        description=(
            "List jarvis Docker containers with name, status, image, and ports. "
            "Only shows jarvis-related containers (filtered by name/labels)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "all": {
                    "type": "boolean",
                    "description": "Include stopped containers (default: false, only running)",
                },
            },
        },
    ),
    Tool(
        name="docker_logs",
        description=(
            "Get recent logs from a jarvis Docker container. "
            "Supports partial name matching (e.g., 'auth' matches 'jarvis-auth')."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Container name or partial match (e.g., 'auth', 'jarvis-tts')",
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of tail lines (default: 100, max: 1000)",
                },
                "since": {
                    "type": "string",
                    "description": "Only logs since this time (e.g., '1h', '30m')",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="docker_restart",
        description="Restart a jarvis Docker container by name (partial match supported).",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Container name or partial match",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="docker_stop",
        description="Stop a running jarvis Docker container by name (partial match supported).",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Container name or partial match",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="docker_start",
        description="Start a stopped jarvis Docker container by name (partial match supported).",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Container name or partial match",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="docker_compose_up",
        description=(
            "Run 'docker compose up -d' for a jarvis service. "
            "Accepts full name (jarvis-auth) or short name (auth)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name (e.g., 'jarvis-auth' or 'auth')",
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="docker_compose_down",
        description=(
            "Run 'docker compose down' for a jarvis service. "
            "Accepts full name (jarvis-auth) or short name (auth)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name (e.g., 'jarvis-auth' or 'auth')",
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="docker_compose_list",
        description="List jarvis services that have docker-compose files.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


async def handle_docker_tool(
    name: str, arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle execution of Docker tools."""
    if name == "docker_ps":
        return _handle_ps(arguments)
    elif name == "docker_logs":
        return _handle_logs(arguments)
    elif name == "docker_restart":
        return _handle_restart(arguments)
    elif name == "docker_stop":
        return _handle_stop(arguments)
    elif name == "docker_start":
        return _handle_start(arguments)
    elif name == "docker_compose_up":
        return _handle_compose_up(arguments)
    elif name == "docker_compose_down":
        return _handle_compose_down(arguments)
    elif name == "docker_compose_list":
        return _handle_compose_list()
    else:
        return [TextContent(type="text", text=f"Unknown docker tool: {name}")]


def _handle_ps(args: dict[str, Any]) -> list[TextContent]:
    """Handle docker_ps tool."""
    try:
        show_all: bool = args.get("all", False)
        containers = docker_service.list_containers(show_all=show_all)

        if not containers:
            return [TextContent(type="text", text="No jarvis containers found.")]

        lines: list[str] = [f"=== Jarvis Containers ({len(containers)}) ===", ""]
        for c in containers:
            status_icon = "●" if c["status"] == "running" else "○"
            line = f"  {status_icon} {c['name']:<30} {c['status']:<12} {c['ports']}"
            lines.append(line)

        lines.append("")
        lines.append(f"Image details:")
        for c in containers:
            lines.append(f"  {c['name']}: {c['image']}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        logger.error("docker_ps failed: %s", e)
        return [TextContent(type="text", text=f"Error: {e}")]


def _handle_logs(args: dict[str, Any]) -> list[TextContent]:
    """Handle docker_logs tool."""
    name: str = args.get("name", "")
    if not name:
        return [TextContent(type="text", text="Error: 'name' is required")]

    try:
        lines_count: int = args.get("lines", 100)
        since: str | None = args.get("since")
        logs = docker_service.get_container_logs(name, lines=lines_count, since=since)

        if not logs.strip():
            return [TextContent(type="text", text=f"No logs found for '{name}'.")]

        return [TextContent(type="text", text=logs)]

    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error("docker_logs failed: %s", e)
        return [TextContent(type="text", text=f"Error: {e}")]


def _handle_restart(args: dict[str, Any]) -> list[TextContent]:
    """Handle docker_restart tool."""
    name: str = args.get("name", "")
    if not name:
        return [TextContent(type="text", text="Error: 'name' is required")]

    try:
        msg = docker_service.restart_container(name)
        return [TextContent(type="text", text=msg)]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error("docker_restart failed: %s", e)
        return [TextContent(type="text", text=f"Error: {e}")]


def _handle_stop(args: dict[str, Any]) -> list[TextContent]:
    """Handle docker_stop tool."""
    name: str = args.get("name", "")
    if not name:
        return [TextContent(type="text", text="Error: 'name' is required")]

    try:
        msg = docker_service.stop_container(name)
        return [TextContent(type="text", text=msg)]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error("docker_stop failed: %s", e)
        return [TextContent(type="text", text=f"Error: {e}")]


def _handle_start(args: dict[str, Any]) -> list[TextContent]:
    """Handle docker_start tool."""
    name: str = args.get("name", "")
    if not name:
        return [TextContent(type="text", text="Error: 'name' is required")]

    try:
        msg = docker_service.start_container(name)
        return [TextContent(type="text", text=msg)]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error("docker_start failed: %s", e)
        return [TextContent(type="text", text=f"Error: {e}")]


def _handle_compose_up(args: dict[str, Any]) -> list[TextContent]:
    """Handle docker_compose_up tool."""
    service: str = args.get("service", "")
    if not service:
        return [TextContent(type="text", text="Error: 'service' is required")]

    try:
        output = docker_service.compose_up(service)
        return [TextContent(type="text", text=output)]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error("docker_compose_up failed: %s", e)
        return [TextContent(type="text", text=f"Error: {e}")]


def _handle_compose_down(args: dict[str, Any]) -> list[TextContent]:
    """Handle docker_compose_down tool."""
    service: str = args.get("service", "")
    if not service:
        return [TextContent(type="text", text="Error: 'service' is required")]

    try:
        output = docker_service.compose_down(service)
        return [TextContent(type="text", text=output)]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error("docker_compose_down failed: %s", e)
        return [TextContent(type="text", text=f"Error: {e}")]


def _handle_compose_list() -> list[TextContent]:
    """Handle docker_compose_list tool."""
    try:
        services = docker_service.list_known_services()

        if not services:
            return [TextContent(type="text", text="No jarvis services with compose files found.")]

        lines: list[str] = [f"=== Jarvis Services with Compose Files ({len(services)}) ===", ""]
        for s in services:
            lines.append(f"  {s['name']:<30} {s['path']}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        logger.error("docker_compose_list failed: %s", e)
        return [TextContent(type="text", text=f"Error: {e}")]
