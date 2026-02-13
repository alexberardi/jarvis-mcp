"""Database tools for read-only PostgreSQL access."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from mcp.types import Tool, TextContent

from jarvis_mcp.config import config

_MAX_OUTPUT_CHARS = 6000
_MAX_ROWS_DEFAULT = 100
_MAX_ROWS_LIMIT = 500
_STATEMENT_TIMEOUT_MS = 5000
_LOCK_TIMEOUT_MS = 2000

_READONLY_BLOCKLIST = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "commit",
    "rollback",
    "vacuum",
    "analyze",
    "refresh",
    "execute",
    "call",
    "do",
    "set",
    "copy",
    "lock",
    "for update",
]

DB_TOOLS: list[Tool] = [
    Tool(
        name="db_list_databases",
        description="List available PostgreSQL databases (read-only).",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="db_list_schemas",
        description="List schemas for a database (read-only).",
        inputSchema={
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "Database name"},
            },
        },
    ),
    Tool(
        name="db_list_tables",
        description="List tables for a database (optionally filter by schema).",
        inputSchema={
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "Database name"},
                "schema": {"type": "string", "description": "Schema name (default: all)"},
            },
        },
    ),
    Tool(
        name="db_describe_table",
        description="Describe a table (columns, types, nullability, defaults).",
        inputSchema={
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "Database name"},
                "schema": {"type": "string", "description": "Schema name"},
                "table": {"type": "string", "description": "Table name"},
            },
            "required": ["schema", "table"],
        },
    ),
    Tool(
        name="db_query",
        description="Run a read-only SELECT query with safety limits.",
        inputSchema={
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "Database name"},
                "query": {"type": "string", "description": "SELECT query to execute"},
                "max_rows": {
                    "type": "integer",
                    "description": "Maximum rows to return (default: 100, max: 500)",
                    "default": _MAX_ROWS_DEFAULT,
                },
            },
            "required": ["query"],
        },
    ),
]


def _connect(database: str | None) -> psycopg2.extensions.connection:
    dbname = database or config.postgres_db
    conn = psycopg2.connect(
        host=config.postgres_host,
        port=config.postgres_port,
        user=config.postgres_user,
        password=config.postgres_password,
        dbname=dbname,
    )
    conn.set_session(readonly=True, autocommit=True)
    return conn


def _set_timeouts(cursor) -> None:
    cursor.execute("SET statement_timeout TO %s", (_STATEMENT_TIMEOUT_MS,))
    cursor.execute("SET lock_timeout TO %s", (_LOCK_TIMEOUT_MS,))


def _validate_readonly(query: str) -> str | None:
    stripped = query.strip()
    if not stripped:
        return "Query is empty."
    if ";" in stripped:
        return "Multiple statements are not allowed."

    normalized = re.sub(r"\\s+", " ", stripped).lower()
    if not (normalized.startswith("select") or normalized.startswith("with")):
        return "Only SELECT queries are allowed."

    for keyword in _READONLY_BLOCKLIST:
        if re.search(rf"\\b{re.escape(keyword)}\\b", normalized):
            return f"Query contains forbidden keyword: {keyword}"
    return None


def _wrap_with_limit(query: str, max_rows: int) -> str:
    return f"SELECT * FROM ({query}) AS _jarvis_sub LIMIT {max_rows}"


def _format_output(header: list[str], payload: Any) -> str:
    text = "\n".join(header) + "\n\n" + payload
    if len(text) <= _MAX_OUTPUT_CHARS:
        return text
    return text[:_MAX_OUTPUT_CHARS] + "\n... [truncated]"


def _rows_to_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No rows returned."
    return json.dumps(rows, indent=2, default=str)


async def handle_db_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "db_list_databases":
        return _db_list_databases()
    if name == "db_list_schemas":
        return _db_list_schemas(arguments)
    if name == "db_list_tables":
        return _db_list_tables(arguments)
    if name == "db_describe_table":
        return _db_describe_table(arguments)
    if name == "db_query":
        return _db_query(arguments)
    return [TextContent(type="text", text=f"Unknown db tool: {name}")]


def _db_list_databases() -> list[TextContent]:
    start = time.monotonic()
    conn = _connect("postgres")
    try:
        with conn.cursor() as cursor:
            _set_timeouts(cursor)
            cursor.execute(
                """
                SELECT datname
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY datname
                """
            )
            rows = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

    elapsed_ms = int((time.monotonic() - start) * 1000)
    header = [
        "=== Databases ===",
        f"Elapsed: {elapsed_ms}ms",
        f"Count: {len(rows)}",
    ]
    payload = "\n".join(rows) if rows else "No databases found."
    return [TextContent(type="text", text=_format_output(header, payload))]


def _db_list_schemas(args: dict[str, Any]) -> list[TextContent]:
    database = args.get("database")
    start = time.monotonic()
    conn = _connect(database)
    try:
        with conn.cursor() as cursor:
            _set_timeouts(cursor)
            cursor.execute(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schema_name
                """
            )
            rows = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

    elapsed_ms = int((time.monotonic() - start) * 1000)
    header = [
        "=== Schemas ===",
        f"Database: {database or config.postgres_db}",
        f"Elapsed: {elapsed_ms}ms",
        f"Count: {len(rows)}",
    ]
    payload = "\n".join(rows) if rows else "No schemas found."
    return [TextContent(type="text", text=_format_output(header, payload))]


def _db_list_tables(args: dict[str, Any]) -> list[TextContent]:
    database = args.get("database")
    schema = args.get("schema")
    start = time.monotonic()
    conn = _connect(database)
    try:
        with conn.cursor() as cursor:
            _set_timeouts(cursor)
            if schema:
                cursor.execute(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                      AND table_schema = %s
                    ORDER BY table_schema, table_name
                    """,
                    (schema,),
                )
            else:
                cursor.execute(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                      AND table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_schema, table_name
                    """
                )
            rows = [f"{row[0]}.{row[1]}" for row in cursor.fetchall()]
    finally:
        conn.close()

    elapsed_ms = int((time.monotonic() - start) * 1000)
    header = [
        "=== Tables ===",
        f"Database: {database or config.postgres_db}",
        f"Schema: {schema or 'all'}",
        f"Elapsed: {elapsed_ms}ms",
        f"Count: {len(rows)}",
    ]
    payload = "\n".join(rows) if rows else "No tables found."
    return [TextContent(type="text", text=_format_output(header, payload))]


def _db_describe_table(args: dict[str, Any]) -> list[TextContent]:
    database = args.get("database")
    schema = args["schema"]
    table = args["table"]
    start = time.monotonic()
    conn = _connect(database)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            _set_timeouts(cursor)
            cursor.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema, table),
            )
            rows = cursor.fetchall()
    finally:
        conn.close()

    elapsed_ms = int((time.monotonic() - start) * 1000)
    header = [
        "=== Table Description ===",
        f"Database: {database or config.postgres_db}",
        f"Table: {schema}.{table}",
        f"Elapsed: {elapsed_ms}ms",
        f"Columns: {len(rows)}",
    ]
    payload = _rows_to_text(rows)
    return [TextContent(type="text", text=_format_output(header, payload))]


def _db_query(args: dict[str, Any]) -> list[TextContent]:
    database = args.get("database")
    query = args["query"]
    max_rows = min(int(args.get("max_rows", _MAX_ROWS_DEFAULT)), _MAX_ROWS_LIMIT)

    error = _validate_readonly(query)
    if error:
        return [TextContent(type="text", text=f"Query rejected: {error}")]

    safe_query = _wrap_with_limit(query, max_rows)

    start = time.monotonic()
    conn = _connect(database)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            _set_timeouts(cursor)
            cursor.execute(safe_query)
            rows = cursor.fetchall()
    finally:
        conn.close()

    elapsed_ms = int((time.monotonic() - start) * 1000)
    header = [
        "=== Query Result ===",
        f"Database: {database or config.postgres_db}",
        f"Elapsed: {elapsed_ms}ms",
        f"Rows: {len(rows)} (max {max_rows})",
    ]
    payload = _rows_to_text(rows)
    return [TextContent(type="text", text=_format_output(header, payload))]
