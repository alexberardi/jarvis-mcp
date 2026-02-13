"""Tests for database tools."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from jarvis_mcp.tools import database as db_tools


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.query = None
        self.params = None

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConn:
    def __init__(self, rows):
        self._rows = rows
        self.closed = False

    def cursor(self, cursor_factory=None):
        return FakeCursor(self._rows)

    def set_session(self, readonly=True, autocommit=True):
        return None

    def close(self):
        self.closed = True


class TestDbToolsDefinition:
    def test_tools_count(self):
        assert len(db_tools.DB_TOOLS) == 5

    def test_tool_names(self):
        names = [t.name for t in db_tools.DB_TOOLS]
        assert "db_list_databases" in names
        assert "db_list_schemas" in names
        assert "db_list_tables" in names
        assert "db_describe_table" in names
        assert "db_query" in names


class TestReadonlyValidation:
    def test_rejects_non_select(self):
        assert db_tools._validate_readonly("UPDATE users SET x=1") is not None

    def test_rejects_multiple_statements(self):
        assert db_tools._validate_readonly("SELECT 1; SELECT 2") is not None

    def test_accepts_select(self):
        assert db_tools._validate_readonly("SELECT 1") is None


class TestDbQueries:
    def test_list_databases(self):
        fake_conn = FakeConn([("db1",), ("db2",)])
        with patch("jarvis_mcp.tools.database._connect", return_value=fake_conn):
            result = db_tools._db_list_databases()
            assert "db1" in result[0].text
            assert "db2" in result[0].text

    def test_describe_table(self):
        rows = [
            {
                "column_name": "id",
                "data_type": "uuid",
                "is_nullable": "NO",
                "column_default": None,
            }
        ]
        fake_conn = FakeConn(rows)
        with patch("jarvis_mcp.tools.database._connect", return_value=fake_conn):
            result = db_tools._db_describe_table({"schema": "public", "table": "users"})
            assert "Table Description" in result[0].text
            assert "column_name" in result[0].text

    def test_query_applies_limit(self):
        rows = [{"value": 1}]
        fake_conn = FakeConn(rows)
        with patch("jarvis_mcp.tools.database._connect", return_value=fake_conn):
            result = db_tools._db_query({"query": "SELECT 1"})
            assert "Rows: 1" in result[0].text
