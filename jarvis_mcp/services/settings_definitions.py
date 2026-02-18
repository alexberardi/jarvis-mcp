"""Settings definitions for jarvis-mcp.

Defines all configurable settings with their types, defaults, and metadata.
"""

from jarvis_settings_client import SettingDefinition


SETTINGS_DEFINITIONS: list[SettingDefinition] = [
    # MCP configuration
    SettingDefinition(
        key="mcp.enabled_tools",
        category="mcp",
        value_type="string",
        default="logs,debug",
        description="Comma-separated list of enabled tool groups",
        env_fallback="JARVIS_MCP_TOOLS",
    ),
    SettingDefinition(
        key="mcp.config_url_style",
        category="mcp",
        value_type="string",
        default="",
        description="URL style for config service (empty or 'dockerized')",
        env_fallback="JARVIS_CONFIG_URL_STYLE",
    ),

    # Server configuration
    SettingDefinition(
        key="server.host",
        category="server",
        value_type="string",
        default="localhost",
        description="Server host",
        env_fallback="JARVIS_MCP_HOST",
        requires_reload=True,
    ),
    SettingDefinition(
        key="server.port",
        category="server",
        value_type="int",
        default=7709,
        description="Server port",
        env_fallback="JARVIS_MCP_PORT",
        requires_reload=True,
    ),

    # Service discovery
    SettingDefinition(
        key="discovery.refresh_interval",
        category="discovery",
        value_type="int",
        default=300,
        description="Service discovery refresh interval in seconds",
        env_fallback="JARVIS_DISCOVERY_REFRESH_INTERVAL",
    ),
]
