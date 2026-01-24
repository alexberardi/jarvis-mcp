#!/bin/bash
set -e

cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Starting jarvis-mcp locally..."
echo "  Port: ${JARVIS_MCP_PORT:-8011}"
echo "  Tools: ${JARVIS_MCP_TOOLS:-logs,debug}"
echo ""
python -m jarvis_mcp
