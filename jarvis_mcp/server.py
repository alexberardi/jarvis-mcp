import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from jarvis_mcp.config import config
from jarvis_mcp.tools.logs import LOGS_TOOLS, handle_logs_tool
from jarvis_mcp.tools.debug import DEBUG_TOOLS, handle_debug_tool
from jarvis_mcp.tools.health import HEALTH_TOOLS, handle_health_tool

logger = logging.getLogger(__name__)

# Create the MCP server
server = Server("jarvis-mcp")


def get_enabled_tools() -> list[Tool]:
    """Get all tools from enabled tool groups."""
    tools: list[Tool] = []

    if config.is_enabled("logs"):
        tools.extend(LOGS_TOOLS)
        logger.info("Enabled tool group: logs (%d tools)", len(LOGS_TOOLS))

    if config.is_enabled("debug"):
        tools.extend(DEBUG_TOOLS)
        logger.info("Enabled tool group: debug (%d tools)", len(DEBUG_TOOLS))

    if config.is_enabled("health"):
        tools.extend(HEALTH_TOOLS)
        logger.info("Enabled tool group: health (%d tools)", len(HEALTH_TOOLS))

    # Future tool groups can be added here:
    # if config.is_enabled("recipes"):
    #     tools.extend(RECIPES_TOOLS)
    # if config.is_enabled("auth"):
    #     tools.extend(AUTH_TOOLS)

    return tools


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools based on configuration."""
    return get_enabled_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Route tool calls to the appropriate handler."""
    logger.info("Tool call: %s with args: %s", name, arguments)

    # Route to appropriate handler based on tool prefix
    if name.startswith("logs_"):
        if not config.is_enabled("logs"):
            return [TextContent(type="text", text="Logs tools are not enabled")]
        return await handle_logs_tool(name, arguments)

    elif name.startswith("debug_"):
        if not config.is_enabled("debug"):
            return [TextContent(type="text", text="Debug tools are not enabled")]
        return await handle_debug_tool(name, arguments)

    elif name.startswith("health_"):
        if not config.is_enabled("health"):
            return [TextContent(type="text", text="Health tools are not enabled")]
        return await handle_health_tool(name, arguments)

    # Future handlers:
    # elif name.startswith("recipes_"):
    #     return await handle_recipes_tool(name, arguments)
    # elif name.startswith("auth_"):
    #     return await handle_auth_tool(name, arguments)

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
