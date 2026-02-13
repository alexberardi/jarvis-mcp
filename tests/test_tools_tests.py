"""Tests for tests tools."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from jarvis_mcp.tools.tests import TESTS_TOOLS, _build_command, _sanitize_args, handle_tests_tool


class FakeProcess:
    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.killed = False

    async def communicate(self):
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True


class TestTestsToolsDefinition:
    def test_tools_count(self):
        assert len(TESTS_TOOLS) == 1

    def test_tool_name(self):
        assert TESTS_TOOLS[0].name == "run_tests"

    def test_schema_has_fields(self):
        props = TESTS_TOOLS[0].inputSchema["properties"]
        assert "service" in props
        assert "category" in props
        assert "args" in props
        assert "timeout_seconds" in props


class TestArgsSanitization:
    def test_sanitize_args(self):
        safe, rejected = _sanitize_args(["-k", "auth", "bad;rm"])
        assert safe == ["-k", "auth"]
        assert rejected == ["bad;rm"]


class TestBuildCommand:
    def test_build_command_parsing(self):
        command, cwd = _build_command(None, "command-parsing", [])
        assert command[:2] == ["python", "test_command_parsing.py"]
        assert isinstance(cwd, Path)

    def test_build_database_with_wrong_service(self):
        command, cwd = _build_command("jarvis-auth", "database", [])
        assert command is None
        assert cwd is None

    def test_build_pytest_requires_service(self):
        command, cwd = _build_command(None, "pytest", [])
        assert command is None
        assert cwd is None


class TestHandleRunTests:
    @pytest.mark.asyncio
    async def test_run_tests_success(self):
        fake_process = FakeProcess(stdout=b"ok", stderr=b"", returncode=0)
        with patch("jarvis_mcp.tools.tests.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = fake_process

            result = await handle_tests_tool("run_tests", {"service": "jarvis-auth"})

            assert len(result) == 1
            assert "Exit Code: 0" in result[0].text
            assert "Command: pytest" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tests_missing_service(self):
        result = await handle_tests_tool("run_tests", {"category": "pytest"})
        assert "Missing required field: service" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tests_invalid_category(self):
        result = await handle_tests_tool("run_tests", {"service": "jarvis-auth", "category": "nope"})
        assert "Invalid service/category" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tests_rejects_args(self):
        fake_process = FakeProcess(stdout=b"ok", stderr=b"", returncode=0)
        with patch("jarvis_mcp.tools.tests.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = fake_process
            result = await handle_tests_tool(
                "run_tests", {"service": "jarvis-auth", "args": ["-k", "auth", "bad;rm"]}
            )
            assert "Rejected args" in result[0].text
