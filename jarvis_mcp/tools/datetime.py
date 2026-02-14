"""Datetime tools for jarvis-mcp.

Provides date context generation and date key resolution as MCP tools.
"""

import json
from typing import Any

from mcp.types import Tool, TextContent

from jarvis_mcp.services.datetime_service import (
    generate_date_context_object,
    resolve_date_keys,
)


DATETIME_TOOLS: list[Tool] = [
    Tool(
        name="datetime_context",
        description=(
            "Generate a full date context object for a timezone. "
            "Returns current date/time, relative dates (tomorrow, yesterday), "
            "weekdays, weekends, weeks, months, years, and pre-calculated time expressions. "
            "Useful for understanding what 'tomorrow', 'next Monday', etc. mean right now."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone (e.g., 'America/New_York', 'UTC'). Defaults to UTC.",
                },
            },
        },
    ),
    Tool(
        name="datetime_resolve",
        description=(
            "Resolve semantic date keys to ISO 8601 datetime strings. "
            "Takes date keys like ['tomorrow', 'morning'] and returns resolved "
            "UTC datetimes. Handles relative dates, time modifiers, weekdays, "
            "and relative offsets like 'in_30_minutes'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "date_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of date keys to resolve (e.g., ['tomorrow', 'morning'], ['next_monday'], ['in_30_minutes']).",
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone (e.g., 'America/New_York', 'UTC'). Defaults to UTC.",
                },
            },
            "required": ["date_keys"],
        },
    ),
]


async def handle_datetime_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle execution of datetime tools."""
    if name == "datetime_context":
        return await _datetime_context(arguments)
    elif name == "datetime_resolve":
        return await _datetime_resolve(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown datetime tool: {name}")]


async def _datetime_context(args: dict[str, Any]) -> list[TextContent]:
    """Generate full date context for a timezone."""
    timezone_str = args.get("timezone", "UTC")
    if not isinstance(timezone_str, str) or len(timezone_str) > 100:
        return [TextContent(type="text", text='{"error": "invalid timezone parameter"}')]
    context = generate_date_context_object(timezone_str)
    return [TextContent(type="text", text=json.dumps(context, indent=2))]


async def _datetime_resolve(args: dict[str, Any]) -> list[TextContent]:
    """Resolve semantic date keys to ISO datetimes."""
    date_keys = args.get("date_keys")
    if date_keys is None:
        return [TextContent(type="text", text='{"error": "date_keys is required"}')]

    # Validate date_keys is a list of strings with a reasonable length limit
    if not isinstance(date_keys, list):
        return [TextContent(type="text", text='{"error": "date_keys must be a list"}')]
    if len(date_keys) > 100:
        return [TextContent(type="text", text='{"error": "date_keys exceeds maximum of 100 items"}')]
    date_keys = [str(k) for k in date_keys]

    timezone_str = args.get("timezone", "UTC")
    if not isinstance(timezone_str, str) or len(timezone_str) > 100:
        return [TextContent(type="text", text='{"error": "invalid timezone parameter"}')]

    # Generate fresh date context for resolution
    date_context = generate_date_context_object(timezone_str)
    resolved, unresolved = resolve_date_keys(date_keys, date_context)

    result = {
        "resolved": resolved,
        "unresolved": unresolved,
    }
    return [TextContent(type="text", text=json.dumps(result))]
