import os
from dataclasses import dataclass, field


@dataclass
class JarvisMcpConfig:
    """Configuration for jarvis-mcp server."""

    # Server settings
    host: str = "localhost"
    port: int = 8011

    # Tool groups to enable (comma-separated in env, or list)
    enabled_tools: set[str] = field(default_factory=lambda: {"logs", "debug", "health"})

    # Service URLs
    logs_url: str = "http://localhost:8006"
    auth_url: str = "http://localhost:8007"
    recipes_url: str = "http://localhost:8001"
    command_center_url: str = "http://localhost:8002"
    whisper_url: str = "http://localhost:9999"
    ocr_url: str = "http://localhost:5009"
    llm_proxy_url: str = "http://localhost:8000"

    # Auth (optional - for authenticated endpoints)
    app_id: str | None = None
    app_key: str | None = None

    @classmethod
    def from_env(cls) -> "JarvisMcpConfig":
        """Load configuration from environment variables."""
        tools_str = os.getenv("JARVIS_MCP_TOOLS", "logs,debug")
        enabled_tools = {t.strip() for t in tools_str.split(",") if t.strip()}

        return cls(
            host=os.getenv("JARVIS_MCP_HOST", "localhost"),
            port=int(os.getenv("JARVIS_MCP_PORT", "8011")),
            enabled_tools=enabled_tools,
            logs_url=os.getenv("JARVIS_LOGS_URL", "http://localhost:8006"),
            auth_url=os.getenv("JARVIS_AUTH_URL", "http://localhost:8007"),
            recipes_url=os.getenv("JARVIS_RECIPES_URL", "http://localhost:8001"),
            command_center_url=os.getenv("JARVIS_COMMAND_CENTER_URL", "http://localhost:8002"),
            whisper_url=os.getenv("JARVIS_WHISPER_URL", "http://localhost:9999"),
            ocr_url=os.getenv("JARVIS_OCR_URL", "http://localhost:5009"),
            llm_proxy_url=os.getenv("JARVIS_LLM_PROXY_URL", "http://localhost:8000"),
            app_id=os.getenv("JARVIS_APP_ID"),
            app_key=os.getenv("JARVIS_APP_KEY"),
        )

    def is_enabled(self, tool_group: str) -> bool:
        """Check if a tool group is enabled."""
        return tool_group in self.enabled_tools

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for service calls."""
        if self.app_id and self.app_key:
            return {
                "X-Jarvis-App-Id": self.app_id,
                "X-Jarvis-App-Key": self.app_key,
            }
        return {}


# Global config instance
config = JarvisMcpConfig.from_env()
