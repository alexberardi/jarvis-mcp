import logging
import sys

import uvicorn
from fastapi import FastAPI
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

from jarvis_mcp.config import config
from jarvis_mcp.server import server

# Configure logging to stderr (stdout is used for MCP protocol in stdio mode)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("jarvis-mcp")

# Create SSE transport
sse = SseServerTransport("/messages")


async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )


async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)


async def handle_health(request):
    return JSONResponse({
        "status": "ok",
        "service": "jarvis-mcp",
        "enabled_tools": list(config.enabled_tools),
        "service_discovery": config._service_discovery_initialized,
    })


# Create FastAPI sub-app for settings
from jarvis_settings_client import create_settings_router
from jarvis_mcp.services.settings_service import get_settings_service

settings_app = FastAPI(title="jarvis-mcp settings")
_settings_router = create_settings_router(
    service=get_settings_service(),
    auth_dependency=None,  # No auth for MCP settings (developer tool)
)
settings_app.include_router(_settings_router)


# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route("/health", endpoint=handle_health),
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
        Mount("/v1/settings", app=settings_app),
    ],
)


def main() -> None:
    """Run the jarvis-mcp server."""
    logger.info("Starting jarvis-mcp server")

    # Initialize service discovery (updates URLs from jarvis-config-service)
    if config.init_service_discovery():
        logger.info("✅ Service discovery initialized")
    else:
        logger.info("⚠️  Using env vars for service URLs")

    logger.info("Enabled tool groups: %s", ", ".join(config.enabled_tools))
    logger.info("Logs URL: %s", config.logs_url)
    logger.info("Server: http://%s:%d", config.host, config.port)

    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
