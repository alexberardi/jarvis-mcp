from typing import Any

import httpx
from mcp.types import Tool, TextContent

from jarvis_mcp.config import config

# Tool definitions for the debug group
DEBUG_TOOLS: list[Tool] = [
    Tool(
        name="debug_health",
        description="Check health status of jarvis services. Returns which services are up/down.",
        inputSchema={
            "type": "object",
            "properties": {
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific services to check. If empty, checks all known services.",
                },
            },
        },
    ),
    Tool(
        name="debug_service_info",
        description="Get detailed information about a specific jarvis service (version, config, etc).",
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "enum": ["logs", "auth", "recipes", "command-center"],
                    "description": "Service to get info about",
                },
            },
            "required": ["service"],
        },
    ),
]

# Known services and their health endpoints
KNOWN_SERVICES = {
    "logs": {"url_key": "logs_url", "health": "/health"},
    "auth": {"url_key": "auth_url", "health": "/health"},
    "recipes": {"url_key": "recipes_url", "health": "/health"},
    "command-center": {"url_key": "command_center_url", "health": "/api/v0/health"},
}


async def handle_debug_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle execution of debug tools."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        if name == "debug_health":
            return await _debug_health(client, arguments)
        elif name == "debug_service_info":
            return await _debug_service_info(client, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown debug tool: {name}")]


async def _debug_health(client: httpx.AsyncClient, args: dict[str, Any]) -> list[TextContent]:
    """Check health of services."""
    services_to_check = args.get("services") or list(KNOWN_SERVICES.keys())

    results = []
    for service_name in services_to_check:
        if service_name not in KNOWN_SERVICES:
            results.append(f"  {service_name}: unknown service")
            continue

        service_info = KNOWN_SERVICES[service_name]
        base_url = getattr(config, service_info["url_key"])
        health_path = service_info["health"]

        try:
            response = await client.get(f"{base_url}{health_path}")
            if response.status_code == 200:
                results.append(f"  {service_name}: UP")
            else:
                results.append(f"  {service_name}: DEGRADED (status {response.status_code})")
        except httpx.RequestError:
            results.append(f"  {service_name}: DOWN")

    header = "=== Service Health Status ===\n"
    return [TextContent(type="text", text=header + "\n".join(results))]


async def _debug_service_info(client: httpx.AsyncClient, args: dict[str, Any]) -> list[TextContent]:
    """Get info about a specific service."""
    service_name = args["service"]

    if service_name not in KNOWN_SERVICES:
        return [TextContent(type="text", text=f"Unknown service: {service_name}")]

    service_info = KNOWN_SERVICES[service_name]
    base_url = getattr(config, service_info["url_key"])
    health_path = service_info["health"]

    info_lines = [
        f"=== {service_name} ===",
        f"  URL: {base_url}",
        f"  Health endpoint: {health_path}",
    ]

    # Try to get health details
    try:
        response = await client.get(f"{base_url}{health_path}")
        info_lines.append(f"  Status: {response.status_code}")
        if response.status_code == 200:
            try:
                health_data = response.json()
                for key, value in health_data.items():
                    if isinstance(value, dict):
                        info_lines.append(f"  {key}:")
                        for k, v in value.items():
                            info_lines.append(f"    {k}: {v}")
                    else:
                        info_lines.append(f"  {key}: {value}")
            except Exception:
                pass
    except httpx.RequestError as e:
        info_lines.append(f"  Status: UNREACHABLE ({e})")

    return [TextContent(type="text", text="\n".join(info_lines))]
