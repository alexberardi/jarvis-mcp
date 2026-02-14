# jarvis-mcp

MCP (Model Context Protocol) server exposing jarvis services as tools for Claude Code.

## Quick Reference

```bash
# Setup
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Run
.venv/bin/python -m jarvis_mcp

# Or with Docker
docker-compose up -d

# Test
.venv/bin/pytest
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
| `JARVIS_CONFIG_URL` | - | Config service URL (preferred) |
| `JARVIS_CONFIG_URL_STYLE` | - | Set to `dockerized` in Docker |
| `JARVIS_LOGS_URL` | http://localhost:8006 | Fallback: Logs service URL |
| `JARVIS_AUTH_URL` | http://localhost:8007 | Fallback: Auth service URL |

## Service Discovery

Service URLs are fetched from `jarvis-config-service` at startup:
1. If `JARVIS_CONFIG_URL` is set, URLs are fetched from config service
2. If config service unavailable, falls back to `JARVIS_*_URL` env vars
3. Background refresh every 5 minutes

For Docker: Set `JARVIS_CONFIG_URL_STYLE=dockerized` to get `host.docker.internal` URLs.

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

- `GET /health` → Health check (returns JSON with status, enabled tools, service discovery state)
- `GET /sse` → SSE connection for MCP clients
- `POST /messages` → MCP message endpoint

## Dependencies

**Python Libraries:**
- mcp (Model Context Protocol)
- starlette, sse-starlette
- httpx

**Service Dependencies:**
- ✅ **Required**: `jarvis-config-service` (8013) - Service discovery (preferred)
- ⚠️ **Optional**: `jarvis-logs` (8006) - Log querying tools
- ⚠️ **Optional**: `jarvis-auth` (8007) - Health checks and service info
- Fallback to env vars if config-service unavailable

**Used By:**
- Claude Code (development environment)

**Impact if Down:**
- ⚠️ No Claude Code integration tools
- ⚠️ Manual service interaction required
- ✅ Services continue running normally
