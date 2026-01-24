#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Starting jarvis-mcp..."
docker compose up --build -d

echo ""
echo "Service started:"
echo "  - jarvis-mcp: http://localhost:${JARVIS_MCP_PORT:-8011}/sse"
echo ""
echo "Claude Code config (~/.claude.json):"
echo '  {"mcpServers": {"jarvis": {"url": "http://localhost:8011/sse"}}}'
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop:      docker compose down"
