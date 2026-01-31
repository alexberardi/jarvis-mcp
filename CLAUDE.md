# jarvis-mcp

MCP (Model Context Protocol) server exposing jarvis services as tools for Claude Code.

## Quick Reference

```bash
# Run
pip install -e .
python -m jarvis_mcp

# Or with Docker
docker-compose up -d

# Test
poetry run pytest
```

## Claude Code Integration

Add to `~/.claude/settings.json`:
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

## Architecture

```
jarvis_mcp/
├── __main__.py    # Entry point
├── server.py      # SSE server, MCP protocol
├── config.py      # Environment configuration
└── tools/
    ├── logs.py    # logs_query, logs_tail, logs_errors, logs_services
    └── debug.py   # debug_health, debug_service_info
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_MCP_HOST` | localhost | Server host |
| `JARVIS_MCP_PORT` | 8011 | Server port |
| `JARVIS_MCP_TOOLS` | logs,debug | Enabled tool groups |
| `JARVIS_LOGS_URL` | http://localhost:8006 | Logs service URL |
| `JARVIS_AUTH_URL` | http://localhost:8007 | Auth service URL |
| `JARVIS_COMMAND_CENTER_URL` | http://localhost:8002 | Command center URL |

## Available Tools

**Logs:**
- `logs_query` → Query logs with filters
- `logs_tail` → Recent logs from service
- `logs_errors` → Find recent errors
- `logs_services` → List services with logs

**Debug:**
- `debug_health` → Check service health
- `debug_service_info` → Get service details

## API Endpoints

- `GET /sse` → SSE connection for MCP clients
- `POST /messages` → MCP message endpoint

## Dependencies

- mcp (Model Context Protocol)
- starlette, sse-starlette
- httpx
