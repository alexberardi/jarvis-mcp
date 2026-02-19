"""Tests for command service (HTTP client for JCC test endpoint)."""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from jarvis_mcp.config import JarvisMcpConfig
from jarvis_mcp.services.command_definitions import BUILTIN_TEST_CASES


def _make_config(**kwargs) -> JarvisMcpConfig:
    """Create a config with auth credentials set."""
    defaults = {
        "app_id": "test-app",
        "app_key": "test-key",
        "command_center_url": "http://localhost:8002",
    }
    defaults.update(kwargs)
    return JarvisMcpConfig(**defaults)


def _make_no_auth_config() -> JarvisMcpConfig:
    """Create a config without auth credentials."""
    return JarvisMcpConfig(app_id=None, app_key=None)


class TestSingleCommand:
    """Tests for test_single_command function."""

    def test_success_returns_jcc_response(self):
        """Successful call returns JCC response dict."""
        from jarvis_mcp.services.command_service import test_single_command

        jcc_response = {
            "voice_command": "What's the weather in Miami?",
            "stop_reason": "tool_calls",
            "command_name": "get_weather",
            "parameters": {"city": "Miami"},
            "elapsed_seconds": 1.5,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = jcc_response

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("jarvis_mcp.services.command_service.config", _make_config()):
            with patch("jarvis_mcp.services.command_service.httpx.AsyncClient") as mock_cls:
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                result = asyncio.run(test_single_command("What's the weather in Miami?"))

        assert result["command_name"] == "get_weather"
        assert result["parameters"] == {"city": "Miami"}

    def test_no_auth_configured_returns_error(self):
        """Returns error when auth credentials are not configured."""
        from jarvis_mcp.services.command_service import test_single_command

        with patch("jarvis_mcp.services.command_service.config", _make_no_auth_config()):
            result = asyncio.run(test_single_command("test"))

        assert "error" in result
        assert "auth" in result["error"].lower() or "credentials" in result["error"].lower()

    def test_connection_error_returns_error(self):
        """Returns error on connection failure."""
        from jarvis_mcp.services.command_service import test_single_command

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch("jarvis_mcp.services.command_service.config", _make_config()):
            with patch("jarvis_mcp.services.command_service.httpx.AsyncClient") as mock_cls:
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                result = asyncio.run(test_single_command("test"))

        assert "error" in result
        assert "Connection" in result["error"] or "connect" in result["error"].lower()

    def test_jcc_401_returns_error(self):
        """Returns error on 401 response from JCC."""
        from jarvis_mcp.services.command_service import test_single_command

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid app credentials"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("jarvis_mcp.services.command_service.config", _make_config()):
            with patch("jarvis_mcp.services.command_service.httpx.AsyncClient") as mock_cls:
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                result = asyncio.run(test_single_command("test"))

        assert "error" in result
        assert "401" in result["error"]

    def test_sends_correct_payload(self):
        """Sends voice_command, commands, and tools to JCC."""
        from jarvis_mcp.services.command_service import test_single_command

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stop_reason": "complete"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("jarvis_mcp.services.command_service.config", _make_config()):
            with patch("jarvis_mcp.services.command_service.httpx.AsyncClient") as mock_cls:
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                asyncio.run(test_single_command("What's the weather?"))

                call_args = mock_client.post.call_args
                payload = call_args.kwargs.get("json")
                assert payload["voice_command"] == "What's the weather?"
                assert "available_commands" in payload
                assert "client_tools" in payload


class TestCommandSuite:
    """Tests for test_command_suite function."""

    def test_all_pass(self):
        """Suite with all passing tests returns correct summary."""
        from jarvis_mcp.services.command_service import test_command_suite

        async def mock_single(voice_command, **kwargs):
            for tc in BUILTIN_TEST_CASES:
                if tc["voice_command"] == voice_command:
                    return {
                        "voice_command": voice_command,
                        "stop_reason": "tool_calls",
                        "command_name": tc["expected_command"],
                        "parameters": tc["expected_params"],
                    }
            return {"stop_reason": "error", "error": "unknown"}

        with patch("jarvis_mcp.services.command_service.test_single_command", side_effect=mock_single):
            result = asyncio.run(test_command_suite(categories=["jokes"]))

        assert result["summary"]["total"] == 4
        assert result["summary"]["passed"] == 4
        assert result["summary"]["failed"] == 0
        assert result["summary"]["success_rate"] == 100.0

    def test_mixed_results(self):
        """Suite with mixed results reports correctly."""
        from jarvis_mcp.services.command_service import test_command_suite

        call_count = 0

        async def mock_single(voice_command, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                return {
                    "stop_reason": "tool_calls",
                    "command_name": "wrong_command",
                    "parameters": {},
                }
            return {
                "stop_reason": "tool_calls",
                "command_name": "tell_joke",
                "parameters": {},
            }

        with patch("jarvis_mcp.services.command_service.test_single_command", side_effect=mock_single):
            result = asyncio.run(test_command_suite(categories=["jokes"]))

        assert result["summary"]["total"] == 4
        assert result["summary"]["passed"] > 0
        assert result["summary"]["failed"] > 0
        assert "confusion_matrix" in result["analysis"]

    def test_category_filter(self):
        """Filters test cases by category."""
        from jarvis_mcp.services.command_service import test_command_suite

        async def mock_single(voice_command, **kwargs):
            return {
                "stop_reason": "tool_calls",
                "command_name": "get_weather",
                "parameters": {},
            }

        with patch("jarvis_mcp.services.command_service.test_single_command", side_effect=mock_single):
            result = asyncio.run(test_command_suite(categories=["weather"]))

        assert result["summary"]["total"] == 7


class TestBuiltinTestCases:
    """Tests for get_builtin_test_cases function."""

    def test_returns_all_cases(self):
        """Returns all test cases when no filter."""
        from jarvis_mcp.services.command_service import get_builtin_test_cases

        cases = get_builtin_test_cases()
        assert len(cases) == len(BUILTIN_TEST_CASES)

    def test_filters_by_category(self):
        """Filters by category."""
        from jarvis_mcp.services.command_service import get_builtin_test_cases

        weather_cases = get_builtin_test_cases(categories=["weather"])
        assert all(c["category"] == "weather" for c in weather_cases)
        assert len(weather_cases) == 7

    def test_multiple_categories(self):
        """Filters by multiple categories."""
        from jarvis_mcp.services.command_service import get_builtin_test_cases

        cases = get_builtin_test_cases(categories=["weather", "jokes"])
        categories = {c["category"] for c in cases}
        assert categories == {"weather", "jokes"}
        assert len(cases) == 11

    def test_empty_category_list_returns_all(self):
        """Empty category list returns all cases."""
        from jarvis_mcp.services.command_service import get_builtin_test_cases

        cases = get_builtin_test_cases(categories=[])
        assert len(cases) == len(BUILTIN_TEST_CASES)


class TestParamValidation:
    """Tests for parameter validation logic."""

    def test_matching_params(self):
        """Correctly identifies matching parameters."""
        from jarvis_mcp.services.command_service import _check_params

        expected = {"city": "Miami"}
        actual = {"city": "Miami", "resolved_datetimes": ["2024-01-01"]}

        missing, mismatched = _check_params(expected, actual)
        assert missing == []
        assert mismatched == []

    def test_missing_params(self):
        """Identifies missing expected parameters."""
        from jarvis_mcp.services.command_service import _check_params

        expected = {"city": "Miami", "unit_system": "metric"}
        actual = {"city": "Miami"}

        missing, mismatched = _check_params(expected, actual)
        assert "unit_system" in missing

    def test_mismatched_params(self):
        """Identifies mismatched parameter values."""
        from jarvis_mcp.services.command_service import _check_params

        expected = {"num1": 5, "operation": "add"}
        actual = {"num1": 5, "operation": "subtract"}

        missing, mismatched = _check_params(expected, actual)
        assert any("operation" in m for m in mismatched)

    def test_empty_expected_always_passes(self):
        """Empty expected params always pass."""
        from jarvis_mcp.services.command_service import _check_params

        missing, mismatched = _check_params({}, {"city": "Miami"})
        assert missing == []
        assert mismatched == []

    def test_numeric_equivalence(self):
        """Float 5.0 matches int 5."""
        from jarvis_mcp.services.command_service import _check_params

        expected = {"num1": 5}
        actual = {"num1": 5.0}

        missing, mismatched = _check_params(expected, actual)
        assert missing == []
        assert mismatched == []
