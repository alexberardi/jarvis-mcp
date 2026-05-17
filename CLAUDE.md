# jarvis-mcp

> **⚠️ Potentially deprecated — do not extend.**
>
> The MCP surface is still **actively used** today (Claude Code integration + command-center optional tool injection via `jarvis-mcp-client`), but the architecture is under review. **Don't pour effort into adding new tools or extending this service.** If you need to expose new capabilities to Claude Code or to the LLM, raise the question before working here.
>
> Existing tools continue to work; the deprecation note is forward-looking.

---

## What it is

A SSE-based MCP (Model Context Protocol) server exposing jarvis service capabilities as tools. Two consumers:

1. **Claude Code** — connects via `~/.claude/settings.json` MCP config; gives the developer (you) access to ~30 tools: `query_logs`, `debug_health`, `docker_ps`, `db_query`, `datetime_resolve`, `command_test`, etc.
2. **command-center** — optionally connects via `jarvis-mcp-client` at startup (`JARVIS_MCP_URL`); if connected, surfaces MCP tools as LLM-callable tools in the voice pipeline. Non-fatal if unavailable.

Port: **7709**.

## Quick Reference

```bash
# Run
.venv/bin/python -m jarvis_mcp

# Or Docker
docker-compose up -d

# Test
.venv/bin/pytest
```

Claude Code config:
```json
{
  "mcpServers": {
    "jarvis": { "type": "sse", "url": "http://localhost:7709/sse" }
  }
}
```

## Tool inventory (for triage / discovery)

| Group | Tools |
|---|---|
| **Logs** | `logs_query`, `logs_tail`, `logs_errors`, `logs_services` |
| **Debug** | `debug_health`, `debug_service_info` |
| **Health** | `health_check`, `health_service` |
| **Database** (read-only) | `db_list_databases`, `db_list_schemas`, `db_list_tables`, `db_describe_table`, `db_query` |
| **Datetime** | `datetime_resolve`, `datetime_context` |
| **Math** | `math_evaluate` |
| **Conversion** | `unit_convert` |
| **Command testing** | `command_test`, `command_test_suite`, `command_test_list` (E2E through command-center) |
| **Docker** | `docker_ps`, `docker_logs`, `docker_restart`, `docker_stop`, `docker_start`, `docker_compose_{up,down,list}` |
| **Tests** | `run_tests` |

Enable subset via `JARVIS_MCP_TOOLS` (comma list).

## Config surface (env, no DB)

| Variable | Default | Purpose |
|---|---|---|
| `JARVIS_MCP_HOST` | `localhost` | Bind |
| `JARVIS_MCP_PORT` | `7709` | Port |
| `JARVIS_MCP_TOOLS` | `logs,debug,health,datetime,math,conversion,command,docker` | Enabled tool groups |
| `JARVIS_ROOT` | (env) | Compose-file discovery root |
| `JARVIS_CONFIG_URL` | — | Service discovery |
| `JARVIS_CONFIG_URL_STYLE` | — | Set to `dockerized` in Docker |
| `JARVIS_LOGS_URL` / `JARVIS_AUTH_URL` | — | Legacy fallbacks if config-service unavailable |

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Status + enabled tools + service discovery state |
| GET | `/sse` | MCP SSE stream |
| POST | `/messages` | MCP message endpoint |

## Dependency graph

**Upstream:** `jarvis-config-service` (service discovery, preferred), `jarvis-logs`, `jarvis-auth`, the Docker daemon (for docker_* tools), Postgres (for db_* tools)

**Downstream:**
- **Claude Code** (you, the developer)
- **command-center** — optional, via `jarvis-mcp-client.init()`. Logged as non-fatal if missing.

## If you must work here

- Tool implementations live in `jarvis_mcp/tools/*.py` and `jarvis_mcp/services/*.py`.
- New tools must be added to the `JARVIS_MCP_TOOLS` group default or the SSE handshake won't surface them.
- Don't add settings DB tables here — keep it stateless.
- Don't add write-tools (e.g. `db_insert`). Database access is intentionally read-only.
- Don't break the SSE contract — Claude Code's reconnect logic depends on stable framing.

Because the service is on the deprecation watch-list, prefer fixing bugs over adding capability. New capability requests should be discussed first.
