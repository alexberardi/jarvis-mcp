#!/bin/bash
# Production server
# Usage: ./run-prod.sh [--build]

set -e
cd "$(dirname "$0")"

BUILD_FLAGS=""
if [[ "$1" == "--build" ]]; then
    BUILD_FLAGS="--build"
fi

echo "Starting jarvis-mcp..."
docker compose -f docker-compose.prod.yaml up -d $BUILD_FLAGS

echo ""
echo "Service started:"
echo "  - jarvis-mcp: http://localhost:${JARVIS_MCP_PORT:-7709}/sse"
echo ""
echo "Claude Code config (~/.claude/settings.json):"
echo '  {"mcpServers": {"jarvis": {"type": "sse", "url": "http://localhost:7709/sse"}}}'
echo ""
echo "Logs: docker compose -f docker-compose.prod.yaml logs -f"
echo "Stop: docker compose -f docker-compose.prod.yaml down"
