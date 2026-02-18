import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def reset_config():
    """Reset config before each test."""
    # Store original env vars
    original_env = {
        "JARVIS_MCP_HOST": os.environ.get("JARVIS_MCP_HOST"),
        "JARVIS_MCP_PORT": os.environ.get("JARVIS_MCP_PORT"),
        "JARVIS_MCP_TOOLS": os.environ.get("JARVIS_MCP_TOOLS"),
        "JARVIS_LOGS_URL": os.environ.get("JARVIS_LOGS_URL"),
        "JARVIS_AUTH_URL": os.environ.get("JARVIS_AUTH_URL"),
        "JARVIS_RECIPES_URL": os.environ.get("JARVIS_RECIPES_URL"),
        "JARVIS_COMMAND_CENTER_URL": os.environ.get("JARVIS_COMMAND_CENTER_URL"),
        "JARVIS_APP_ID": os.environ.get("JARVIS_APP_ID"),
        "JARVIS_APP_KEY": os.environ.get("JARVIS_APP_KEY"),
    }

    yield

    # Restore original env vars
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture
def test_env():
    """Set up test environment variables."""
    env_vars = {
        "JARVIS_MCP_HOST": "localhost",
        "JARVIS_MCP_PORT": "7709",
        "JARVIS_MCP_TOOLS": "logs,debug",
        "JARVIS_LOGS_URL": "http://localhost:7702",
        "JARVIS_AUTH_URL": "http://localhost:7701",
        "JARVIS_RECIPES_URL": "http://localhost:7030",
        "JARVIS_COMMAND_CENTER_URL": "http://localhost:7703",
        "JARVIS_APP_ID": "test-app",
        "JARVIS_APP_KEY": "test-key-12345",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def sample_log_query_args():
    """Sample arguments for logs_query tool."""
    return {
        "service": "test-service",
        "level": "ERROR",
        "since_minutes": 30,
        "limit": 50,
    }


@pytest.fixture
def sample_log_response():
    """Sample log response from jarvis-logs."""
    return [
        {
            "timestamp": "2024-01-15T12:00:00",
            "service": "test-service",
            "level": "ERROR",
            "message": "Test error message",
            "context": {"request_id": "abc123"},
        },
        {
            "timestamp": "2024-01-15T11:59:00",
            "service": "test-service",
            "level": "ERROR",
            "message": "Another error",
            "context": None,
        },
    ]
