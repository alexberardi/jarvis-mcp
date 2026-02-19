import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from jarvis_mcp.config import config
from jarvis_mcp.tools.logs import LOGS_TOOLS, handle_logs_tool
from jarvis_mcp.tools.debug import DEBUG_TOOLS, handle_debug_tool
from jarvis_mcp.tools.health import HEALTH_TOOLS, handle_health_tool
from jarvis_mcp.tools.tests import TESTS_TOOLS, handle_tests_tool
from jarvis_mcp.tools.database import DB_TOOLS, handle_db_tool
from jarvis_mcp.tools.datetime import DATETIME_TOOLS, handle_datetime_tool
from jarvis_mcp.tools.math import MATH_TOOLS, handle_math_tool
from jarvis_mcp.tools.conversion import CONVERSION_TOOLS, handle_conversion_tool
from jarvis_mcp.tools.command import COMMAND_TOOLS, handle_command_tool

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

    if config.is_enabled("tests"):
        tools.extend(TESTS_TOOLS)
        logger.info("Enabled tool group: tests (%d tools)", len(TESTS_TOOLS))

    if config.is_enabled("db"):
        tools.extend(DB_TOOLS)
        logger.info("Enabled tool group: db (%d tools)", len(DB_TOOLS))

    if config.is_enabled("datetime"):
        tools.extend(DATETIME_TOOLS)
        logger.info("Enabled tool group: datetime (%d tools)", len(DATETIME_TOOLS))

    if config.is_enabled("math"):
        tools.extend(MATH_TOOLS)
        logger.info("Enabled tool group: math (%d tools)", len(MATH_TOOLS))

    if config.is_enabled("conversion"):
        tools.extend(CONVERSION_TOOLS)
        logger.info("Enabled tool group: conversion (%d tools)", len(CONVERSION_TOOLS))

    if config.is_enabled("command"):
        tools.extend(COMMAND_TOOLS)
        logger.info("Enabled tool group: command (%d tools)", len(COMMAND_TOOLS))

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

    elif name == "run_tests" or name.startswith("tests_"):
        if not config.is_enabled("tests"):
            return [TextContent(type="text", text="Tests tools are not enabled")]
        return await handle_tests_tool(name, arguments)

    elif name.startswith("db_"):
        if not config.is_enabled("db"):
            return [TextContent(type="text", text="DB tools are not enabled")]
        return await handle_db_tool(name, arguments)

    elif name.startswith("datetime_"):
        if not config.is_enabled("datetime"):
            return [TextContent(type="text", text="Datetime tools are not enabled")]
        return await handle_datetime_tool(name, arguments)

    elif name.startswith("math_"):
        if not config.is_enabled("math"):
            return [TextContent(type="text", text="Math tools are not enabled")]
        return await handle_math_tool(name, arguments)

    elif name.startswith("unit_"):
        if not config.is_enabled("conversion"):
            return [TextContent(type="text", text="Conversion tools are not enabled")]
        return await handle_conversion_tool(name, arguments)

    elif name.startswith("command_"):
        if not config.is_enabled("command"):
            return [TextContent(type="text", text="Command tools are not enabled")]
        return await handle_command_tool(name, arguments)

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
