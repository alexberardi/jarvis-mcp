"""Settings service for jarvis-mcp.

Provides runtime configuration that can be modified without restarting.
Settings are stored in the database with fallback to environment variables.
"""

import logging
from typing import Any

from jarvis_settings_client import SettingsService as BaseSettingsService

from jarvis_mcp.services.settings_definitions import SETTINGS_DEFINITIONS

logger = logging.getLogger(__name__)


class MCPSettingsService(BaseSettingsService):
    """Settings service for MCP with helper methods."""

    def get_mcp_config(self) -> dict[str, Any]:
        """Get MCP configuration."""
        return {
            "enabled_tools": self.get_str("mcp.enabled_tools", "logs,debug"),
            "config_url_style": self.get_str("mcp.config_url_style", ""),
        }

    def get_enabled_tools_list(self) -> list[str]:
        """Get list of enabled tool groups."""
        tools_str = self.get_str("mcp.enabled_tools", "logs,debug")
        return [tool.strip() for tool in tools_str.split(",") if tool.strip()]


# Global singleton
_settings_service: MCPSettingsService | None = None


def get_settings_service() -> MCPSettingsService:
    """Get the global SettingsService instance."""
    global _settings_service
    if _settings_service is None:
        from jarvis_mcp.db.models import Setting
        from jarvis_mcp.db.session import get_session_local

        SessionLocal = get_session_local()
        _settings_service = MCPSettingsService(
            definitions=SETTINGS_DEFINITIONS,
            get_db_session=SessionLocal,
            setting_model=Setting,
        )
    return _settings_service


def reset_settings_service() -> None:
    """Reset the settings service singleton (for testing)."""
    global _settings_service
    _settings_service = None
