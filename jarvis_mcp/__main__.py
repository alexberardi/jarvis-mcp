import asyncio
import logging
import sys

from jarvis_mcp.config import config

# Configure logging to stderr (stdout is used for MCP protocol in stdio mode)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("jarvis-mcp")


def main() -> None:
    """Run the jarvis-mcp server."""
    logger.info("Starting jarvis-mcp server")
    logger.info("Enabled tool groups: %s", ", ".join(config.enabled_tools))
    logger.info("Logs URL: %s", config.logs_url)
    logger.info("Server: http://%s:%d", config.host, config.port)

    # Import here to avoid issues if mcp isn't installed
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    import uvicorn

    from jarvis_mcp.server import server

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

    # Create Starlette app
    app = Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ],
    )

    # Run with uvicorn
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
