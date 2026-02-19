"""MCP tools for E2E command testing via jarvis-command-center."""

import json
import logging
from typing import Any

from mcp.types import Tool, TextContent

from jarvis_mcp.services.command_service import (
    test_single_command,
    test_command_suite,
    get_builtin_test_cases,
)

logger = logging.getLogger(__name__)

COMMAND_TOOLS: list[Tool] = [
    Tool(
        name="command_test",
        description=(
            "Test a single voice command through the command-center pipeline. "
            "Sends the command through warmup -> LLM inference -> tool extraction "
            "and returns the parsed command name and parameters."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "voice_command": {
                    "type": "string",
                    "description": "The voice command to test (e.g., \"What's the weather in Miami?\")",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for date resolution (default: America/New_York)",
                },
            },
            "required": ["voice_command"],
        },
    ),
    Tool(
        name="command_test_suite",
        description=(
            "Run a batch of voice command tests with validation. "
            "Uses built-in test cases (or custom ones) and reports "
            "pass/fail, success rates per command, and a confusion matrix."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Filter built-in tests by category. "
                        "Options: weather, calendar, knowledge, search, jokes, "
                        "calculator, sports, timers. Omit for all."
                    ),
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for date resolution (default: America/New_York)",
                },
            },
        },
    ),
    Tool(
        name="command_test_list",
        description=(
            "List built-in test cases. Returns the voice commands, "
            "expected command names, and expected parameters for each test."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "Filter by category. "
                        "Options: weather, calendar, knowledge, search, jokes, "
                        "calculator, sports, timers."
                    ),
                },
            },
        },
    ),
]


async def handle_command_tool(
    name: str, arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle execution of command testing tools."""
    if name == "command_test":
        return await _handle_test(arguments)
    elif name == "command_test_suite":
        return await _handle_suite(arguments)
    elif name == "command_test_list":
        return _handle_list(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown command tool: {name}")]


async def _handle_test(args: dict[str, Any]) -> list[TextContent]:
    """Handle command_test tool."""
    voice_command = args.get("voice_command", "").strip()
    if not voice_command:
        return [TextContent(type="text", text="Error: voice_command must not be empty")]

    timezone = args.get("timezone", "America/New_York")

    result = await test_single_command(voice_command, timezone=timezone)

    if "error" in result and "stop_reason" not in result:
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_suite(args: dict[str, Any]) -> list[TextContent]:
    """Handle command_test_suite tool."""
    categories = args.get("categories")
    timezone = args.get("timezone", "America/New_York")

    result = await test_command_suite(categories=categories, timezone=timezone)

    if "error" in result and "summary" not in result:
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def _handle_list(args: dict[str, Any]) -> list[TextContent]:
    """Handle command_test_list tool."""
    category = args.get("category")
    categories = [category] if category else None

    cases = get_builtin_test_cases(categories=categories)
    return [TextContent(type="text", text=json.dumps(cases, indent=2))]
