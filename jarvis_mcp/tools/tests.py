"""Test execution tools for jarvis services."""

from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import Any

from mcp.types import Tool, TextContent

_REPO_ROOT = Path(__file__).resolve().parents[3]

SERVICE_DIRS: dict[str, Path] = {
    "jarvis-auth": _REPO_ROOT / "jarvis-auth",
    "jarvis-command-center": _REPO_ROOT / "jarvis-command-center",
    "jarvis-config-service": _REPO_ROOT / "jarvis-config-service",
    "jarvis-logs": _REPO_ROOT / "jarvis-logs",
    "jarvis-mcp": _REPO_ROOT / "jarvis-mcp",
    "jarvis-node-setup": _REPO_ROOT / "jarvis-node-setup",
    "jarvis-ocr-service": _REPO_ROOT / "jarvis-ocr-service",
    "jarvis-recipes-server": _REPO_ROOT / "jarvis-recipes-server",
    "jarvis-tts": _REPO_ROOT / "jarvis-tts",
    "jarvis-whisper-api": _REPO_ROOT / "jarvis-whisper-api",
    "jarvis-llm-proxy-api": _REPO_ROOT / "jarvis-llm-proxy-api",
}

_SAFE_ARG_RE = re.compile(r"^[A-Za-z0-9_./:=\\-]+$")
_MAX_OUTPUT_CHARS = 6000

TESTS_TOOLS: list[Tool] = [
    Tool(
        name="run_tests",
        description="Run test suites for a jarvis service or category.",
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "enum": sorted(SERVICE_DIRS.keys()),
                    "description": "Service to run pytest in.",
                },
                "category": {
                    "type": "string",
                    "enum": ["pytest", "command-parsing", "database"],
                    "description": "Test category to run. 'pytest' uses the service directory.",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional extra args passed to the test command.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Timeout for test execution in seconds (default: 900).",
                    "default": 900,
                },
            },
        },
    ),
]


async def handle_tests_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle execution of tests tools."""
    if name == "run_tests":
        return await _run_tests(arguments)
    return [TextContent(type="text", text=f"Unknown tests tool: {name}")]


def _sanitize_args(args: list[str] | None) -> tuple[list[str], list[str]]:
    if not args:
        return [], []
    safe_args = []
    rejected = []
    for arg in args[:50]:
        if _SAFE_ARG_RE.match(arg):
            safe_args.append(arg)
        else:
            rejected.append(arg)
    return safe_args, rejected


def _build_command(
    service: str | None, category: str | None, args: list[str]
) -> tuple[list[str], Path] | tuple[None, None]:
    if category == "command-parsing":
        cwd = SERVICE_DIRS["jarvis-node-setup"]
        command = ["python", "test_command_parsing.py", *args]
        return command, cwd

    if category == "database":
        if service and service != "jarvis-command-center":
            return None, None
        cwd = SERVICE_DIRS["jarvis-command-center"]
        command = ["python", "run_database_tests.py", "--type", "sqlite", *args]
        return command, cwd

    # Default to pytest in a service directory
    target_service = service
    if not target_service:
        return None, None
    cwd = SERVICE_DIRS.get(target_service)
    if not cwd:
        return None, None
    command = ["pytest", *args]
    return command, cwd


async def _run_tests(args: dict[str, Any]) -> list[TextContent]:
    service = args.get("service")
    category = args.get("category", "pytest")
    timeout_seconds = int(args.get("timeout_seconds", 900))
    extra_args, rejected_args = _sanitize_args(args.get("args"))

    command, cwd = _build_command(service, category, extra_args)
    if not command or not cwd:
        if category == "database" and service and service != "jarvis-command-center":
            return [
                TextContent(
                    type="text",
                    text="database category only supports service 'jarvis-command-center'.",
                )
            ]
        if not service and category == "pytest":
            return [TextContent(type="text", text="Missing required field: service")]
        return [
            TextContent(
                type="text",
                text="Invalid service/category selection. Provide a valid service or category.",
            )
        ]

    if not cwd.exists():
        return [
            TextContent(
                type="text",
                text=f"Service directory not found: {cwd}",
            )
        ]

    start = time.monotonic()
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout_seconds
            )
        except TimeoutError:
            process.kill()
            stdout, stderr = await process.communicate()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return [
                TextContent(
                    type="text",
                    text=_format_output(
                        command,
                        cwd,
                        "TIMEOUT",
                        stdout,
                        stderr,
                        elapsed_ms,
                        rejected_args,
                    ),
                )
            ]
    except (OSError, ValueError) as exc:
        return [
            TextContent(
                type="text",
                text=f"Failed to start test process: {exc}",
            )
        ]

    elapsed_ms = int((time.monotonic() - start) * 1000)
    return_code = process.returncode if process.returncode is not None else 1

    return [
        TextContent(
            type="text",
            text=_format_output(
                command, cwd, return_code, stdout, stderr, elapsed_ms, rejected_args
            ),
        )
    ]


def _format_output(
    command: list[str],
    cwd: Path,
    return_code: int | str,
    stdout: bytes,
    stderr: bytes,
    elapsed_ms: int,
    rejected_args: list[str],
) -> str:
    header = [
        "=== Test Run Result ===",
        f"Command: {' '.join(command)}",
        f"Working Dir: {cwd}",
        f"Exit Code: {return_code}",
        f"Elapsed: {elapsed_ms}ms",
    ]

    if rejected_args:
        header.append(f"Rejected args: {', '.join(rejected_args)}")

    stdout_text = stdout.decode(errors="replace")
    stderr_text = stderr.decode(errors="replace")

    stdout_text = _trim_output(stdout_text)
    stderr_text = _trim_output(stderr_text)

    return "\n".join(
        header
        + [
            "",
            "--- STDOUT ---",
            stdout_text or "(empty)",
            "",
            "--- STDERR ---",
            stderr_text or "(empty)",
        ]
    )


def _trim_output(text: str) -> str:
    if len(text) <= _MAX_OUTPUT_CHARS:
        return text
    return text[:_MAX_OUTPUT_CHARS] + "\n... [truncated]"
