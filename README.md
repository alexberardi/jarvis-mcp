# jarvis-mcp

MCP (Model Context Protocol) server for jarvis. Exposes jarvis services as tools for Claude Code.

## Architecture

```
Claude Code ◄──MCP (SSE/HTTP)──► jarvis-mcp (8011) ──HTTP──► jarvis services
                                       │
                                       ├──► jarvis-logs (8006)
                                       ├──► jarvis-auth (8007)
                                       ├──► jarvis-recipes (8001)
                                       └──► jarvis-command-center (8002)
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Start with docker-compose
docker-compose up -d

# Or alongside jarvis-logs stack
cd ../jarvis-logs && docker-compose up -d
cd ../jarvis-mcp && docker-compose up -d
```

### Option 2: Local Development

```bash
# Install
pip install -e .

# Run
python -m jarvis_mcp
# or
jarvis-mcp
```

## Claude Code Configuration

Add to your `~/.claude.json` or project `.claude/settings.json`:

```json
{
  "mcpServers": {
    "jarvis": {
      "type": "sse",
      "url": "http://localhost:8011/sse"
    }
  }
}
```

Or use the CLI:

```bash
claude mcp add --transport sse jarvis http://localhost:8011/sse
```

For Docker deployment (different host):

```json
{
  "mcpServers": {
    "jarvis": {
      "type": "sse",
      "url": "http://your-server:8011/sse"
    }
  }
}
```

## Available Tool Groups

| Group | Tools | Description |
|-------|-------|-------------|
| `logs` | `logs_query`, `logs_tail`, `logs_errors`, `logs_services` | Query and search jarvis logs |
| `debug` | `debug_health`, `debug_service_info` | Debug and monitor jarvis services |

### Logs Tools

| Tool | Description |
|------|-------------|
| `logs_query` | Query logs with filters (service, level, search, time range) |
| `logs_tail` | Get recent logs from a specific service |
| `logs_errors` | Find recent errors across all services |
| `logs_services` | List all services that have sent logs |

### Debug Tools

| Tool | Description |
|------|-------------|
| `debug_health` | Check health status of jarvis services |
| `debug_service_info` | Get detailed info about a specific service |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_MCP_HOST` | `localhost` | Host to bind to |
| `JARVIS_MCP_PORT` | `8011` | Port to listen on |
| `JARVIS_MCP_TOOLS` | `logs,debug` | Comma-separated tool groups to enable |
| `JARVIS_LOGS_URL` | `http://localhost:8006` | jarvis-logs server URL |
| `JARVIS_AUTH_URL` | `http://localhost:8007` | jarvis-auth server URL |
| `JARVIS_RECIPES_URL` | `http://localhost:8001` | jarvis-recipes server URL |
| `JARVIS_COMMAND_CENTER_URL` | `http://localhost:8002` | jarvis-command-center URL |

### Docker Configuration

```bash
# Change port
JARVIS_MCP_PORT=9100 docker-compose up -d

# Enable more tool groups
JARVIS_MCP_TOOLS=logs,debug,recipes docker-compose up -d
```

## Usage Examples

Once configured, Claude Code can use these tools directly:

```
User: "Show me recent errors from llm-proxy"
Claude: [calls logs_errors with service="llm-proxy"]

User: "Are all services healthy?"
Claude: [calls debug_health]

User: "Tail the logs from command-center"
Claude: [calls logs_tail with service="command-center"]
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /sse` | SSE connection endpoint for MCP clients |
| `POST /messages` | Message endpoint for MCP protocol |

## Adding New Tool Groups

1. Create a new module in `jarvis_mcp/tools/`:

```python
# jarvis_mcp/tools/recipes.py
from mcp.types import Tool, TextContent

RECIPES_TOOLS = [
    Tool(
        name="recipes_search",
        description="Search for recipes",
        inputSchema={...}
    ),
]

async def handle_recipes_tool(name: str, arguments: dict) -> list[TextContent]:
    ...
```

2. Register in `jarvis_mcp/tools/__init__.py`

3. Add to `server.py`:
```python
if config.is_enabled("recipes"):
    tools.extend(RECIPES_TOOLS)
```

4. Enable in config:
```bash
JARVIS_MCP_TOOLS=logs,debug,recipes
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run locally
python -m jarvis_mcp

# Build Docker image
docker build -t jarvis-mcp .

# Run with Docker
docker run -p 8011:8011 jarvis-mcp
```
