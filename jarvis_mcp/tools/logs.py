from datetime import datetime, timedelta
from typing import Any

import httpx
from mcp.types import Tool, TextContent

from jarvis_mcp.config import config

# Tool definitions for the logs group
LOGS_TOOLS: list[Tool] = [
    Tool(
        name="logs_query",
        description="Query logs from jarvis services with optional filters. Returns recent logs matching the criteria.",
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Filter by service name (e.g., 'llm-proxy', 'command-center')",
                },
                "level": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "description": "Filter by log level",
                },
                "search": {
                    "type": "string",
                    "description": "Search term to filter log messages",
                },
                "since_minutes": {
                    "type": "integer",
                    "description": "Only show logs from the last N minutes (default: 60)",
                    "default": 60,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of logs to return (default: 50, max: 200)",
                    "default": 50,
                },
            },
        },
    ),
    Tool(
        name="logs_tail",
        description="Get the most recent logs from a specific service. Like 'tail -f' for jarvis services.",
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name to tail logs from",
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of recent log lines to return (default: 30)",
                    "default": 30,
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="logs_errors",
        description="Find recent errors across all jarvis services. Useful for debugging issues.",
        inputSchema={
            "type": "object",
            "properties": {
                "since_minutes": {
                    "type": "integer",
                    "description": "Look for errors in the last N minutes (default: 30)",
                    "default": 30,
                },
                "service": {
                    "type": "string",
                    "description": "Optional: filter to a specific service",
                },
            },
        },
    ),
    Tool(
        name="logs_services",
        description="List all services that have sent logs to the logging server.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


async def handle_logs_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle execution of logs tools."""
    # Get auth headers from config
    headers = config.get_auth_headers()

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        if name == "logs_query":
            return await _logs_query(client, arguments)
        elif name == "logs_tail":
            return await _logs_tail(client, arguments)
        elif name == "logs_errors":
            return await _logs_errors(client, arguments)
        elif name == "logs_services":
            return await _logs_services(client)
        else:
            return [TextContent(type="text", text=f"Unknown logs tool: {name}")]


async def _logs_query(client: httpx.AsyncClient, args: dict[str, Any]) -> list[TextContent]:
    """Query logs with filters."""
    params: dict[str, Any] = {}

    if args.get("service"):
        params["service"] = args["service"]
    if args.get("level"):
        params["level"] = args["level"]
    if args.get("search"):
        params["search"] = args["search"]

    since_minutes = args.get("since_minutes", 60)
    since = datetime.utcnow() - timedelta(minutes=since_minutes)
    params["since"] = since.isoformat()

    params["limit"] = min(args.get("limit", 50), 200)

    try:
        response = await client.get(f"{config.logs_url}/api/v0/logs", params=params)
        response.raise_for_status()
        logs = response.json()
        return [TextContent(type="text", text=_format_logs(logs))]
    except httpx.RequestError as e:
        return [TextContent(type="text", text=f"Error connecting to logs server: {e}")]
    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"Logs server error: {e.response.status_code}")]


async def _logs_tail(client: httpx.AsyncClient, args: dict[str, Any]) -> list[TextContent]:
    """Tail recent logs from a service."""
    service = args["service"]
    lines = min(args.get("lines", 30), 100)

    params = {
        "service": service,
        "limit": lines,
    }

    try:
        response = await client.get(f"{config.logs_url}/api/v0/logs", params=params)
        response.raise_for_status()
        logs = response.json()
        header = f"=== Last {len(logs)} logs from {service} ===\n\n"
        return [TextContent(type="text", text=header + _format_logs(logs))]
    except httpx.RequestError as e:
        return [TextContent(type="text", text=f"Error connecting to logs server: {e}")]
    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"Logs server error: {e.response.status_code}")]


async def _logs_errors(client: httpx.AsyncClient, args: dict[str, Any]) -> list[TextContent]:
    """Find recent errors across services."""
    since_minutes = args.get("since_minutes", 30)
    since = datetime.utcnow() - timedelta(minutes=since_minutes)

    params: dict[str, Any] = {
        "level": "ERROR",
        "since": since.isoformat(),
        "limit": 100,
    }

    if args.get("service"):
        params["service"] = args["service"]

    try:
        response = await client.get(f"{config.logs_url}/api/v0/logs", params=params)
        response.raise_for_status()
        logs = response.json()

        if not logs:
            return [TextContent(type="text", text=f"No errors found in the last {since_minutes} minutes.")]

        header = f"=== Found {len(logs)} errors in the last {since_minutes} minutes ===\n\n"
        return [TextContent(type="text", text=header + _format_logs(logs))]
    except httpx.RequestError as e:
        return [TextContent(type="text", text=f"Error connecting to logs server: {e}")]
    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"Logs server error: {e.response.status_code}")]


async def _logs_services(client: httpx.AsyncClient) -> list[TextContent]:
    """List all services with logs."""
    try:
        response = await client.get(f"{config.logs_url}/api/v0/services")
        response.raise_for_status()
        services = response.json()

        if not services:
            return [TextContent(type="text", text="No services have sent logs yet.")]

        text = "Services with logs:\n" + "\n".join(f"  - {s}" for s in services)
        return [TextContent(type="text", text=text)]
    except httpx.RequestError as e:
        return [TextContent(type="text", text=f"Error connecting to logs server: {e}")]
    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"Logs server error: {e.response.status_code}")]


def _format_logs(logs: list[dict[str, Any]]) -> str:
    """Format logs for display."""
    if not logs:
        return "No logs found."

    lines = []
    for log in logs:
        ts = log.get("timestamp", "")[:19]  # Trim microseconds
        level = log.get("level", "?")
        service = log.get("service", "?")
        message = log.get("message", "")
        context = log.get("context")

        line = f"[{ts}] [{level}] [{service}] {message}"
        if context:
            line += f" | {context}"
        lines.append(line)

    return "\n".join(lines)
