"""Health check tools for jarvis services."""

import time
from typing import Any

import httpx
from mcp.types import Tool, TextContent

from jarvis_mcp.config import config


# Service definitions: name -> (url_attr, health_path)
SERVICES = {
    "jarvis-auth": ("auth_url", "/health"),
    "jarvis-command-center": ("command_center_url", "/api/v0/health"),
    "jarvis-logs": ("logs_url", "/health"),
    "jarvis-recipes": ("recipes_url", "/health"),
    "jarvis-whisper": ("whisper_url", "/health"),
    "jarvis-ocr": ("ocr_url", "/health"),
    "llm-proxy": ("llm_proxy_url", "/v1/health"),
}


HEALTH_TOOLS: list[Tool] = [
    Tool(
        name="health_check",
        description="Check health status of all jarvis services. Returns which services are up/down and their response times.",
        inputSchema={
            "type": "object",
            "properties": {
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"Optional: specific services to check. Available: {', '.join(SERVICES.keys())}. If not specified, checks all.",
                },
            },
        },
    ),
    Tool(
        name="health_service",
        description="Check health of a specific jarvis service with detailed response.",
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": f"Service to check. One of: {', '.join(SERVICES.keys())}",
                },
            },
            "required": ["service"],
        },
    ),
]


async def handle_health_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle execution of health tools."""
    if name == "health_check":
        return await _health_check_all(arguments)
    elif name == "health_service":
        return await _health_check_single(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown health tool: {name}")]


async def _health_check_all(args: dict[str, Any]) -> list[TextContent]:
    """Check health of all (or specified) services."""
    services_to_check = args.get("services") or list(SERVICES.keys())

    results: list[str] = []
    healthy_count = 0
    unhealthy_count = 0

    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name in services_to_check:
            if service_name not in SERVICES:
                results.append(f"  {service_name}: ⚠️  Unknown service")
                continue

            url_attr, health_path = SERVICES[service_name]
            base_url = getattr(config, url_attr, None)

            if not base_url:
                results.append(f"  {service_name}: ⚠️  Not configured")
                continue

            status, response_time, details = await _check_service(client, base_url, health_path)

            if status == "healthy":
                healthy_count += 1
                results.append(f"  {service_name}: ✅ {response_time}ms")
            else:
                unhealthy_count += 1
                results.append(f"  {service_name}: ❌ {details}")

    # Build summary
    total = healthy_count + unhealthy_count
    header = f"=== Jarvis Health Check ===\n"
    header += f"Status: {healthy_count}/{total} services healthy\n\n"

    return [TextContent(type="text", text=header + "\n".join(results))]


async def _health_check_single(args: dict[str, Any]) -> list[TextContent]:
    """Check health of a single service with details."""
    service_name = args["service"]

    if service_name not in SERVICES:
        return [TextContent(type="text", text=f"Unknown service: {service_name}. Available: {', '.join(SERVICES.keys())}")]

    url_attr, health_path = SERVICES[service_name]
    base_url = getattr(config, url_attr, None)

    if not base_url:
        return [TextContent(type="text", text=f"{service_name}: Not configured (missing {url_attr})")]

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            start = time.monotonic()
            response = await client.get(f"{base_url}{health_path}")
            elapsed = int((time.monotonic() - start) * 1000)

            text = f"=== {service_name} Health ===\n"
            text += f"URL: {base_url}{health_path}\n"
            text += f"Status: {response.status_code}\n"
            text += f"Response Time: {elapsed}ms\n"

            if response.status_code == 200:
                text += f"Response: {response.text[:500]}"
            else:
                text += f"Error: HTTP {response.status_code}"

            return [TextContent(type="text", text=text)]

        except httpx.RequestError as e:
            return [TextContent(type="text", text=f"{service_name}: Connection failed - {e}")]


async def _check_service(
    client: httpx.AsyncClient, base_url: str, health_path: str
) -> tuple[str, int, str]:
    """Check a single service. Returns (status, response_time_ms, details)."""
    try:
        start = time.monotonic()
        response = await client.get(f"{base_url}{health_path}")
        elapsed = int((time.monotonic() - start) * 1000)

        if response.status_code == 200:
            return ("healthy", elapsed, "OK")
        else:
            return ("unhealthy", elapsed, f"HTTP {response.status_code}")

    except httpx.ConnectError:
        return ("unhealthy", 0, "Connection refused")
    except httpx.TimeoutException:
        return ("unhealthy", 0, "Timeout")
    except httpx.RequestError as e:
        return ("unhealthy", 0, str(e))
