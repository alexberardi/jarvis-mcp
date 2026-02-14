"""Tests for configuration loading."""

import os
from unittest.mock import patch

import pytest

from jarvis_mcp.config import JarvisMcpConfig


class TestJarvisMcpConfig:
    """Tests for JarvisMcpConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            config = JarvisMcpConfig.from_env()
            assert config.host == "localhost"
            assert config.port == 7709
            assert config.enabled_tools == {"logs", "debug", "health", "datetime"}
            assert config.logs_url == "http://localhost:7702"
            assert config.auth_url == "http://localhost:7701"
            assert config.recipes_url == "http://localhost:7030"
            assert config.command_center_url == "http://localhost:7703"
            assert config.app_id is None
            assert config.app_key is None

    def test_custom_host_port(self):
        """Test custom host and port."""
        with patch.dict(
            os.environ,
            {
                "JARVIS_MCP_HOST": "0.0.0.0",
                "JARVIS_MCP_PORT": "9999",
            },
            clear=True,
        ):
            config = JarvisMcpConfig.from_env()
            assert config.host == "0.0.0.0"
            assert config.port == 9999

    def test_custom_tools(self):
        """Test custom tool groups."""
        with patch.dict(
            os.environ,
            {"JARVIS_MCP_TOOLS": "logs,recipes,auth"},
            clear=True,
        ):
            config = JarvisMcpConfig.from_env()
            assert config.enabled_tools == {"logs", "recipes", "auth"}

    def test_tools_with_spaces(self):
        """Test tool groups with spaces are trimmed."""
        with patch.dict(
            os.environ,
            {"JARVIS_MCP_TOOLS": "logs , debug , recipes"},
            clear=True,
        ):
            config = JarvisMcpConfig.from_env()
            assert config.enabled_tools == {"logs", "debug", "recipes"}

    def test_tools_empty_string(self):
        """Test empty tools string."""
        with patch.dict(
            os.environ,
            {"JARVIS_MCP_TOOLS": ""},
            clear=True,
        ):
            config = JarvisMcpConfig.from_env()
            assert config.enabled_tools == set()

    def test_tools_single(self):
        """Test single tool group."""
        with patch.dict(
            os.environ,
            {"JARVIS_MCP_TOOLS": "logs"},
            clear=True,
        ):
            config = JarvisMcpConfig.from_env()
            assert config.enabled_tools == {"logs"}

    def test_custom_service_urls(self):
        """Test custom service URLs."""
        with patch.dict(
            os.environ,
            {
                "JARVIS_LOGS_URL": "http://custom-logs:3000",
                "JARVIS_AUTH_URL": "http://custom-auth:3001",
                "JARVIS_RECIPES_URL": "http://custom-recipes:3002",
                "JARVIS_COMMAND_CENTER_URL": "http://custom-cc:3003",
            },
            clear=True,
        ):
            config = JarvisMcpConfig.from_env()
            assert config.logs_url == "http://custom-logs:3000"
            assert config.auth_url == "http://custom-auth:3001"
            assert config.recipes_url == "http://custom-recipes:3002"
            assert config.command_center_url == "http://custom-cc:3003"

    def test_app_credentials(self):
        """Test app credentials loading."""
        with patch.dict(
            os.environ,
            {
                "JARVIS_APP_ID": "my-app",
                "JARVIS_APP_KEY": "secret-key-123",
            },
            clear=True,
        ):
            config = JarvisMcpConfig.from_env()
            assert config.app_id == "my-app"
            assert config.app_key == "secret-key-123"


class TestIsEnabled:
    """Tests for is_enabled method."""

    def test_enabled_tool(self):
        """Test checking enabled tool group."""
        config = JarvisMcpConfig(enabled_tools={"logs", "debug"})
        assert config.is_enabled("logs") is True
        assert config.is_enabled("debug") is True

    def test_disabled_tool(self):
        """Test checking disabled tool group."""
        config = JarvisMcpConfig(enabled_tools={"logs"})
        assert config.is_enabled("debug") is False
        assert config.is_enabled("recipes") is False

    def test_empty_tools(self):
        """Test with no tools enabled."""
        config = JarvisMcpConfig(enabled_tools=set())
        assert config.is_enabled("logs") is False
        assert config.is_enabled("debug") is False


class TestGetAuthHeaders:
    """Tests for get_auth_headers method."""

    def test_with_credentials(self):
        """Test getting auth headers with credentials."""
        config = JarvisMcpConfig(app_id="my-app", app_key="my-key")
        headers = config.get_auth_headers()
        assert headers == {
            "X-Jarvis-App-Id": "my-app",
            "X-Jarvis-App-Key": "my-key",
        }

    def test_without_app_id(self):
        """Test getting auth headers without app_id."""
        config = JarvisMcpConfig(app_id=None, app_key="my-key")
        headers = config.get_auth_headers()
        assert headers == {}

    def test_without_app_key(self):
        """Test getting auth headers without app_key."""
        config = JarvisMcpConfig(app_id="my-app", app_key=None)
        headers = config.get_auth_headers()
        assert headers == {}

    def test_without_any_credentials(self):
        """Test getting auth headers without any credentials."""
        config = JarvisMcpConfig(app_id=None, app_key=None)
        headers = config.get_auth_headers()
        assert headers == {}
