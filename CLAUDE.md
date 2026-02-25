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
      "url": "http://localhost:7709/sse"
    }
  }
}
```

## Architecture

```
jarvis_mcp/
├── __main__.py        # Entry point
├── server.py          # SSE server, MCP protocol, tool routing
├── config.py          # Environment configuration
├── services/
│   ├── command_service.py      # E2E command testing via JCC
│   ├── command_definitions.py  # Built-in test cases
│   ├── conversion_service.py   # Unit conversion logic
│   ├── datetime_service.py     # Date/time resolution
│   ├── docker_service.py       # Docker container management
│   ├── math_service.py         # Math evaluation
│   └── settings_*.py           # Settings service
└── tools/
    ├── logs.py        # logs_query, logs_tail, logs_errors, logs_services
    ├── debug.py       # debug_health, debug_service_info
    ├── health.py      # health_check, health_service
    ├── database.py    # db_list_databases, db_query, etc.
    ├── datetime.py    # datetime_resolve, datetime_context
    ├── math.py        # math_evaluate
    ├── conversion.py  # unit_convert
    ├── command.py     # command_test, command_test_suite, command_test_list
    ├── docker.py      # docker_ps, docker_logs, docker_restart, etc.
    └── tests.py       # run_tests
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_MCP_HOST` | localhost | Server host |
| `JARVIS_MCP_PORT` | 7709 | Server port |
| `JARVIS_MCP_TOOLS` | logs,debug,health,datetime,math,conversion,command,docker | Enabled tool groups |
| `JARVIS_ROOT` | /Users/alexanderberardi/jarvis | Root dir for compose file discovery |
| `JARVIS_CONFIG_URL` | - | Config service URL (preferred) |
| `JARVIS_CONFIG_URL_STYLE` | - | Set to `dockerized` in Docker |
| `JARVIS_LOGS_URL` | http://localhost:7702 | Fallback: Logs service URL |
| `JARVIS_AUTH_URL` | http://localhost:7701 | Fallback: Auth service URL |

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

**Health:**
- `health_check` → Check health of all/specific services
- `health_service` → Detailed health for one service

**Database (read-only):**
- `db_list_databases` → List PostgreSQL databases
- `db_list_schemas` → List schemas
- `db_list_tables` → List tables
- `db_describe_table` → Describe columns
- `db_query` → Run read-only SELECT queries

**Datetime:**
- `datetime_resolve` → Resolve relative dates ("tomorrow morning" → ISO)
- `datetime_context` → Get current date/time context

**Math:**
- `math_evaluate` → Evaluate math expressions

**Conversion:**
- `unit_convert` → Convert units (temperature, weight, volume, length)

**Command Testing:**
- `command_test` → Test a single voice command through JCC pipeline
- `command_test_suite` → Run batch of command tests with validation
- `command_test_list` → List built-in test cases

**Docker:**
- `docker_ps` → List jarvis containers (name, status, image, ports)
- `docker_logs` → Get recent logs from a container (partial name match)
- `docker_restart` → Restart a container
- `docker_stop` → Stop a running container
- `docker_start` → Start a stopped container
- `docker_compose_up` → `docker compose up -d` for a jarvis service
- `docker_compose_down` → `docker compose down` for a jarvis service
- `docker_compose_list` → List services with compose files

**Tests:**
- `run_tests` → Run pytest for a service

## API Endpoints

- `GET /health` → Health check (returns JSON with status, enabled tools, service discovery state)
- `GET /sse` → SSE connection for MCP clients
- `POST /messages` → MCP message endpoint

## Dependencies

**Python Libraries:**
- mcp (Model Context Protocol)
- starlette, sse-starlette
- httpx
- docker (Docker SDK for Python)

**Service Dependencies:**
- ✅ **Required**: `jarvis-config-service` (7700) - Service discovery (preferred)
- ⚠️ **Optional**: `jarvis-logs` (7702) - Log querying tools
- ⚠️ **Optional**: `jarvis-auth` (7701) - Health checks and service info
- Fallback to env vars if config-service unavailable

**Used By:**
- Claude Code (development environment)

**Impact if Down:**
- ⚠️ No Claude Code integration tools
- ⚠️ Manual service interaction required
- ✅ Services continue running normally
