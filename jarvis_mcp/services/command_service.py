"""Command testing service — HTTP client for JCC test endpoint.

Sends voice commands through the command-center pipeline and validates results.
"""

import logging
from typing import Any

import httpx

from jarvis_mcp.config import config
from jarvis_mcp.services.command_definitions import (
    BUILTIN_TEST_CASES,
    DEFAULT_AVAILABLE_COMMANDS,
    DEFAULT_CLIENT_TOOLS,
)

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60.0


async def test_single_command(
    voice_command: str,
    timezone: str = "America/New_York",
    custom_commands: list[dict[str, Any]] | None = None,
    custom_tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Test a single voice command through the JCC pipeline.

    Args:
        voice_command: The voice command text to test.
        timezone: Timezone for date resolution.
        custom_commands: Custom command definitions (uses defaults if None).
        custom_tools: Custom tool schemas (uses defaults if None).

    Returns:
        JCC response dict or {"error": "..."} on failure.
    """
    if not voice_command or not voice_command.strip():
        return {"error": "voice_command cannot be empty"}

    auth_headers = config.get_auth_headers()
    if not auth_headers:
        return {"error": "No auth credentials configured (JARVIS_APP_ID/JARVIS_APP_KEY)"}

    url = f"{config.command_center_url}/api/v0/test/command"
    payload = {
        "voice_command": voice_command,
        "available_commands": custom_commands or DEFAULT_AVAILABLE_COMMANDS,
        "client_tools": custom_tools or DEFAULT_CLIENT_TOOLS,
        "timezone": timezone,
        "skip_warmup_inference": True,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=auth_headers)

        if response.status_code != 200:
            return {"error": f"JCC returned {response.status_code}: {response.text}"}

        return response.json()

    except httpx.TimeoutException:
        return {"error": f"Request timed out after {TIMEOUT_SECONDS}s"}
    except httpx.RequestError as e:
        return {"error": f"Connection error: {e}"}


async def test_command_suite(
    tests: list[dict[str, Any]] | None = None,
    categories: list[str] | None = None,
    timezone: str = "America/New_York",
) -> dict[str, Any]:
    """
    Run a suite of command tests with validation.

    Args:
        tests: Custom test cases. Uses BUILTIN_TEST_CASES if None.
        categories: Filter built-in tests by category.
        timezone: Timezone for date resolution.

    Returns:
        Summary dict with total/passed/failed/errors/success_rate,
        per-test results, and analysis.
    """
    test_cases = tests or get_builtin_test_cases(categories=categories)

    results: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    errors = 0

    for tc in test_cases:
        voice_command = tc["voice_command"]
        expected_command = tc["expected_command"]
        expected_params = tc.get("expected_params", {})

        response = await test_single_command(voice_command, timezone=timezone)

        if "error" in response and response.get("stop_reason") != "error":
            # Service-level error (connection, auth)
            errors += 1
            results.append({
                **tc,
                "status": "error",
                "actual_command": None,
                "actual_params": None,
                "error": response["error"],
            })
            continue

        actual_command = response.get("command_name")
        actual_params = response.get("parameters") or {}
        command_match = actual_command == expected_command

        # Check parameters
        missing_params, mismatched_params = _check_params(expected_params, actual_params)
        params_ok = not missing_params and not mismatched_params

        test_passed = command_match and params_ok
        if test_passed:
            passed += 1
        else:
            failed += 1

        results.append({
            **tc,
            "status": "passed" if test_passed else "failed",
            "actual_command": actual_command,
            "actual_params": actual_params,
            "command_match": command_match,
            "missing_params": missing_params,
            "mismatched_params": mismatched_params,
            "elapsed_seconds": response.get("elapsed_seconds"),
        })

    total = len(test_cases)
    success_rate = round((passed / total) * 100, 1) if total > 0 else 0.0

    # Build analysis
    analysis = _build_analysis(results)

    return {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "success_rate": success_rate,
        },
        "results": results,
        "analysis": analysis,
    }


def get_builtin_test_cases(
    categories: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Get built-in test cases, optionally filtered by category.

    Args:
        categories: Filter by these categories. Returns all if None or empty.

    Returns:
        List of test case dicts.
    """
    if not categories:
        return list(BUILTIN_TEST_CASES)

    return [tc for tc in BUILTIN_TEST_CASES if tc["category"] in categories]


def _check_params(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """
    Check if actual parameters match expected parameters.

    Only checks parameters listed in expected — extra actual params are OK.
    Skips resolved_datetimes (tested implicitly by date resolution).

    Returns:
        (missing_params, mismatched_params) — both empty means pass.
    """
    missing: list[str] = []
    mismatched: list[str] = []

    for key, expected_val in expected.items():
        if key == "resolved_datetimes":
            continue  # Skip — date resolution tested implicitly

        if key not in actual:
            missing.append(key)
        elif _normalize_for_comparison(actual[key]) != _normalize_for_comparison(expected_val):
            mismatched.append(
                f"{key}: expected={expected_val!r}, actual={actual[key]!r}"
            )

    return missing, mismatched


def _normalize_for_comparison(value: Any) -> Any:
    """Normalize a value for comparison (handle float/int equivalence, case)."""
    if isinstance(value, float) and value == int(value):
        return int(value)
    if isinstance(value, str):
        return value.lower().strip()
    return value


def _build_analysis(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build analysis from test results."""
    # Success rates per expected command
    command_stats: dict[str, dict[str, int]] = {}
    confusion: dict[str, dict[str, int]] = {}

    for r in results:
        expected = r.get("expected_command", "unknown")
        actual = r.get("actual_command")
        status = r.get("status", "error")

        if expected not in command_stats:
            command_stats[expected] = {"total": 0, "passed": 0}
        command_stats[expected]["total"] += 1
        if status == "passed":
            command_stats[expected]["passed"] += 1

        # Confusion matrix
        if actual and actual != expected:
            if expected not in confusion:
                confusion[expected] = {}
            confusion[expected][actual] = confusion[expected].get(actual, 0) + 1

    # Calculate rates
    command_success_rates = {}
    for cmd, stats in command_stats.items():
        rate = round((stats["passed"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0.0
        command_success_rates[cmd] = {
            "total": stats["total"],
            "passed": stats["passed"],
            "success_rate": rate,
        }

    return {
        "command_success_rates": command_success_rates,
        "confusion_matrix": confusion,
    }
