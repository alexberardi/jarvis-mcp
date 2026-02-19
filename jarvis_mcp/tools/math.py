"""Math evaluation tool for jarvis-mcp.

Provides safe mathematical expression evaluation as an MCP tool.
"""

import json
from typing import Any

from mcp.types import Tool, TextContent

from jarvis_mcp.services.math_service import evaluate_expression


MATH_TOOLS: list[Tool] = [
    Tool(
        name="math_evaluate",
        description=(
            "Safely evaluate a mathematical expression. "
            "Supports basic arithmetic (+, -, *, /, //, %, **), "
            "functions (sqrt, abs, round, ceil, floor, log, log10, sin, cos, tan), "
            "and constants (pi, e). Returns the numeric result."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression to evaluate (e.g., '2 + 3', 'sqrt(144)', 'pi * r**2').",
                },
            },
            "required": ["expression"],
        },
    ),
]


async def handle_math_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle execution of math tools."""
    if name == "math_evaluate":
        return await _math_evaluate(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown math tool: {name}")]


async def _math_evaluate(args: dict[str, Any]) -> list[TextContent]:
    """Evaluate a math expression safely."""
    expression = args.get("expression")
    if not expression or not isinstance(expression, str):
        return [TextContent(type="text", text='{"error": "expression is required"}')]

    if len(expression) > 1000:
        return [TextContent(type="text", text='{"error": "expression too long (max 1000 chars)"}')]

    try:
        result = evaluate_expression(expression)
        return [TextContent(type="text", text=json.dumps({
            "result": result,
            "expression": expression,
        }))]
    except ValueError as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
