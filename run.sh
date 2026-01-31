#!/bin/bash
# Development server
# Usage: ./run.sh [--docker]

set -e
cd "$(dirname "$0")"

if [[ "$1" == "--docker" ]]; then
    # Docker development mode
    BUILD_FLAGS=""
    if [[ "$2" == "--rebuild" ]]; then
        docker compose -f docker-compose.dev.yaml build --no-cache
        BUILD_FLAGS="--build"
    elif [[ "$2" == "--build" ]]; then
        BUILD_FLAGS="--build"
    fi

    echo "Starting jarvis-mcp in Docker..."
    docker compose -f docker-compose.dev.yaml up $BUILD_FLAGS
else
    # Local development mode
    # Load environment variables
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi

    echo "Starting jarvis-mcp locally..."
    echo "  Port: ${JARVIS_MCP_PORT:-8011}"
    echo "  Tools: ${JARVIS_MCP_TOOLS:-logs,debug}"
    echo ""
    python -m jarvis_mcp
fi
