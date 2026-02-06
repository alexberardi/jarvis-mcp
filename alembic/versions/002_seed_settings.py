"""Seed default settings

Revision ID: 002
Revises: 001
Create Date: 2026-02-05 17:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


# Settings definitions from jarvis_mcp/services/settings_definitions.py
# All settings are safe to seed (no secrets or URLs)
SETTINGS = [
    # MCP configuration
    {
        "key": "mcp.enabled_tools",
        "value": "logs,debug",
        "value_type": "string",
        "category": "mcp",
        "description": "Comma-separated list of enabled tool groups",
        "env_fallback": "JARVIS_MCP_TOOLS",
        "requires_reload": False,
        "is_secret": False,
    },
    {
        "key": "mcp.config_url_style",
        "value": "",
        "value_type": "string",
        "category": "mcp",
        "description": "URL style for config service (empty or 'dockerized')",
        "env_fallback": "JARVIS_CONFIG_URL_STYLE",
        "requires_reload": False,
        "is_secret": False,
    },
    # Server configuration
    {
        "key": "server.host",
        "value": "localhost",
        "value_type": "string",
        "category": "server",
        "description": "Server host",
        "env_fallback": "JARVIS_MCP_HOST",
        "requires_reload": True,
        "is_secret": False,
    },
    {
        "key": "server.port",
        "value": "8011",
        "value_type": "int",
        "category": "server",
        "description": "Server port",
        "env_fallback": "JARVIS_MCP_PORT",
        "requires_reload": True,
        "is_secret": False,
    },
    # Service discovery
    {
        "key": "discovery.refresh_interval",
        "value": "300",
        "value_type": "int",
        "category": "discovery",
        "description": "Service discovery refresh interval in seconds",
        "env_fallback": "JARVIS_DISCOVERY_REFRESH_INTERVAL",
        "requires_reload": False,
        "is_secret": False,
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == 'postgresql'

    for setting in SETTINGS:
        if is_postgres:
            conn.execute(
                sa.text("""
                    INSERT INTO settings (key, value, value_type, category, description,
                                         env_fallback, requires_reload, is_secret,
                                         household_id, node_id, user_id)
                    VALUES (:key, :value, :value_type, :category, :description,
                           :env_fallback, :requires_reload, :is_secret,
                           NULL, NULL, NULL)
                    ON CONFLICT (key, household_id, node_id, user_id) DO NOTHING
                """),
                setting
            )
        else:
            conn.execute(
                sa.text("""
                    INSERT OR IGNORE INTO settings (key, value, value_type, category, description,
                                                   env_fallback, requires_reload, is_secret,
                                                   household_id, node_id, user_id)
                    VALUES (:key, :value, :value_type, :category, :description,
                           :env_fallback, :requires_reload, :is_secret,
                           NULL, NULL, NULL)
                """),
                setting
            )


def downgrade() -> None:
    conn = op.get_bind()
    for setting in SETTINGS:
        conn.execute(
            sa.text("""
                DELETE FROM settings
                WHERE key = :key
                  AND household_id IS NULL
                  AND node_id IS NULL
                  AND user_id IS NULL
            """),
            {"key": setting["key"]}
        )
