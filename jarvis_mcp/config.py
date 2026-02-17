import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Service name to config attribute mapping (short names)
_SERVICE_URL_MAP = {
    "logs": "logs_url",
    "auth": "auth_url",
    "recipes": "recipes_url",
    "command-center": "command_center_url",
    "whisper": "whisper_url",
    "tts": "tts_url",
    "ocr": "ocr_url",
    "llm-proxy": "llm_proxy_url",
}


@dataclass
class JarvisMcpConfig:
    """Configuration for jarvis-mcp server."""

    # Server settings
    host: str = "localhost"
    port: int = 8011

    # Tool groups to enable (comma-separated in env, or list)
    enabled_tools: set[str] = field(default_factory=lambda: {"logs", "debug", "health"})

    # Service URLs (populated from config service or defaults)
    logs_url: str = "http://localhost:8006"
    auth_url: str = "http://localhost:8007"
    recipes_url: str = "http://localhost:8001"
    command_center_url: str = "http://localhost:8002"
    whisper_url: str = "http://localhost:8012"
    tts_url: str = "http://localhost:8009"
    ocr_url: str = "http://localhost:5009"
    llm_proxy_url: str = "http://localhost:8000"

    # Database (PostgreSQL)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "devuser"
    postgres_password: str = "devpassword"
    postgres_db: str = "postgres"

    # Auth (optional - for authenticated endpoints)
    app_id: str | None = None
    app_key: str | None = None

    # Track if service discovery is initialized
    _service_discovery_initialized: bool = field(default=False, repr=False)

    @classmethod
    def from_env(cls) -> "JarvisMcpConfig":
        """Load configuration from environment variables."""
        tools_str = os.getenv("JARVIS_MCP_TOOLS", "logs,debug")
        enabled_tools = {t.strip() for t in tools_str.split(",") if t.strip()}

        # Map env var names to config attribute names for service URLs
        env_url_map = {
            "JARVIS_LOGS_URL": "logs_url",
            "JARVIS_AUTH_URL": "auth_url",
            "JARVIS_RECIPES_URL": "recipes_url",
            "JARVIS_COMMAND_CENTER_URL": "command_center_url",
            "JARVIS_WHISPER_URL": "whisper_url",
            "JARVIS_TTS_URL": "tts_url",
            "JARVIS_OCR_URL": "ocr_url",
            "JARVIS_LLM_PROXY_URL": "llm_proxy_url",
        }

        # Build service URL kwargs from env vars (only override if set)
        url_kwargs: dict[str, str] = {}
        for env_var, attr_name in env_url_map.items():
            value = os.getenv(env_var)
            if value:
                url_kwargs[attr_name] = value

        return cls(
            host=os.getenv("JARVIS_MCP_HOST", "localhost"),
            port=int(os.getenv("JARVIS_MCP_PORT", "8011")),
            enabled_tools=enabled_tools,
            app_id=os.getenv("JARVIS_APP_ID"),
            app_key=os.getenv("JARVIS_APP_KEY"),
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_user=os.getenv("POSTGRES_USER", "devuser"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "devpassword"),
            postgres_db=os.getenv("POSTGRES_DB", "postgres"),
            **url_kwargs,
        )

    def init_service_discovery(self) -> bool:
        """
        Initialize service discovery from jarvis-config-service.

        Returns True if successful, False if using defaults.
        """
        try:
            from jarvis_config_client import init as init_config_client, get_service_url

            success = init_config_client()

            if success:
                self._update_urls_from_config(get_service_url)
                self._service_discovery_initialized = True
                logger.info("Service discovery initialized")
                return True
            else:
                logger.warning("Config service unavailable - using defaults")
                return False

        except ImportError:
            logger.warning("jarvis-config-client not installed - using defaults")
            return False
        except (OSError, RuntimeError) as e:
            logger.error("Failed to initialize service discovery: %s", e)
            return False

    def _update_urls_from_config(self, get_service_url) -> None:
        """Update service URLs from config client."""
        for service_name, attr_name in _SERVICE_URL_MAP.items():
            url = get_service_url(service_name)
            if url:
                setattr(self, attr_name, url)
                logger.debug("Set %s = %s", attr_name, url)

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
