import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Service name to config attribute mapping
_SERVICE_URL_MAP = {
    "jarvis-logs": "logs_url",
    "jarvis-auth": "auth_url",
    "jarvis-recipes": "recipes_url",
    "jarvis-command-center": "command_center_url",
    "jarvis-whisper": "whisper_url",
    "jarvis-tts": "tts_url",
    "jarvis-ocr": "ocr_url",
    "jarvis-llm-proxy": "llm_proxy_url",
}

# Env var fallbacks for each service
_ENV_VAR_FALLBACKS = {
    "jarvis-logs": "JARVIS_LOGS_URL",
    "jarvis-auth": "JARVIS_AUTH_URL",
    "jarvis-recipes": "JARVIS_RECIPES_URL",
    "jarvis-command-center": "JARVIS_COMMAND_CENTER_URL",
    "jarvis-whisper": "JARVIS_WHISPER_URL",
    "jarvis-tts": "JARVIS_TTS_URL",
    "jarvis-ocr": "JARVIS_OCR_URL",
    "jarvis-llm-proxy": "JARVIS_LLM_PROXY_URL",
}

# Default URLs if no config service and no env var
_DEFAULTS = {
    "jarvis-logs": "http://localhost:8006",
    "jarvis-auth": "http://localhost:8007",
    "jarvis-recipes": "http://localhost:8001",
    "jarvis-command-center": "http://localhost:8002",
    "jarvis-whisper": "http://localhost:8012",
    "jarvis-tts": "http://localhost:8009",
    "jarvis-ocr": "http://localhost:5009",
    "jarvis-llm-proxy": "http://localhost:8000",
}


@dataclass
class JarvisMcpConfig:
    """Configuration for jarvis-mcp server."""

    # Server settings
    host: str = "localhost"
    port: int = 8011

    # Tool groups to enable (comma-separated in env, or list)
    enabled_tools: set[str] = field(default_factory=lambda: {"logs", "debug", "health"})

    # Service URLs (populated from config service or env vars)
    logs_url: str = "http://localhost:8006"
    auth_url: str = "http://localhost:8007"
    recipes_url: str = "http://localhost:8001"
    command_center_url: str = "http://localhost:8002"
    whisper_url: str = "http://localhost:8012"
    tts_url: str = "http://localhost:8009"
    ocr_url: str = "http://localhost:5009"
    llm_proxy_url: str = "http://localhost:8000"

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

        return cls(
            host=os.getenv("JARVIS_MCP_HOST", "localhost"),
            port=int(os.getenv("JARVIS_MCP_PORT", "8011")),
            enabled_tools=enabled_tools,
            logs_url=os.getenv("JARVIS_LOGS_URL", "http://localhost:8006"),
            auth_url=os.getenv("JARVIS_AUTH_URL", "http://localhost:8007"),
            recipes_url=os.getenv("JARVIS_RECIPES_URL", "http://localhost:8001"),
            command_center_url=os.getenv("JARVIS_COMMAND_CENTER_URL", "http://localhost:8002"),
            whisper_url=os.getenv("JARVIS_WHISPER_URL", "http://localhost:8012"),
            tts_url=os.getenv("JARVIS_TTS_URL", "http://localhost:8009"),
            ocr_url=os.getenv("JARVIS_OCR_URL", "http://localhost:5009"),
            llm_proxy_url=os.getenv("JARVIS_LLM_PROXY_URL", "http://localhost:8000"),
            app_id=os.getenv("JARVIS_APP_ID"),
            app_key=os.getenv("JARVIS_APP_KEY"),
        )

    def init_service_discovery(self) -> bool:
        """
        Initialize service discovery from jarvis-config-service.

        Returns True if successful, False if falling back to env vars.
        """
        config_url = os.getenv("JARVIS_CONFIG_URL")
        if not config_url:
            logger.warning("JARVIS_CONFIG_URL not set - using env vars for service URLs")
            return False

        try:
            from jarvis_config_client import init as init_config_client, get_service_url

            # Initialize the config client (no DB for MCP - just in-memory cache)
            success = init_config_client(config_url=config_url)

            if success:
                # Update URLs from config service
                self._update_urls_from_config(get_service_url)
                self._service_discovery_initialized = True
                logger.info("Service discovery initialized from %s", config_url)
                return True
            else:
                logger.warning("Config service unavailable - using env vars")
                return False

        except ImportError:
            logger.warning("jarvis-config-client not installed - using env vars")
            return False
        except OSError as e:
            logger.error("Network error during service discovery: %s", e)
            return False
        except (ValueError, KeyError) as e:
            logger.error("Configuration parsing error during service discovery: %s", e)
            return False
        except (TypeError, AttributeError) as e:
            logger.error("Config client API error during service discovery: %s", e)
            return False
        except RuntimeError as e:
            logger.error("Runtime error during service discovery: %s", e)
            return False

    def _update_urls_from_config(self, get_service_url) -> None:
        """Update service URLs from config client."""
        for service_name, attr_name in _SERVICE_URL_MAP.items():
            url = get_service_url(service_name)
            if url:
                setattr(self, attr_name, url)
                logger.debug("Set %s = %s", attr_name, url)
            else:
                # Fall back to env var or default
                env_var = _ENV_VAR_FALLBACKS.get(service_name)
                default = _DEFAULTS.get(service_name)
                fallback_url = os.getenv(env_var, default) if env_var else default
                if fallback_url:
                    setattr(self, attr_name, fallback_url)
                    logger.debug("Service %s not in config, using fallback: %s", service_name, fallback_url)

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
