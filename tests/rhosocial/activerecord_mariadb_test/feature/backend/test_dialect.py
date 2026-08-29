# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_dialect.py
"""
MariaDB backend dialect tests using real database connection.

This module tests MySQL dialect formatting using real database.
Each test has sync and async versions for complete coverage.
"""
import pytest
import pytest_asyncio


class TestMariaDBDialectBackend:
    """Synchronous dialect tests for MariaDB backend."""

    def test_format_identifier(self, mariadb_backend):
        """Test identifier formatting."""
        dialect = mariadb_backend.dialect

        result = dialect.format_identifier("test_table")
        assert result == "`test_table`"

        result = dialect.format_identifier("user_name")
        assert result == "`user_name`"

    def test_quote_parameter(self, mariadb_backend):
        """Test parameter quoting for MySQL."""
        sql = "SELECT * FROM users WHERE name = %s"
        params = ("John",)

        result_sql, result_params = mariadb_backend._prepare_sql_and_params(sql, params)

        assert "%s" in result_sql or "?" in result_sql


class TestAsyncMariaDBDialectBackend:
    """Asynchronous dialect tests for MariaDB backend."""

    @pytest.mark.asyncio
    async def test_async_format_identifier(self, async_mariadb_backend):
        """Test identifier formatting (async)."""
        dialect = async_mariadb_backend.dialect

        result = dialect.format_identifier("test_table")
        assert result == "`test_table`"

        result = dialect.format_identifier("user_name")
        assert result == "`user_name`"

    @pytest.mark.asyncio
    async def test_async_quote_parameter(self, async_mariadb_backend):
        """Test parameter quoting for MySQL (async)."""
        sql = "SELECT * FROM users WHERE name = %s"
        params = ("John",)

        result_sql, result_params = async_mariadb_backend._prepare_sql_and_params(sql, params)

        assert "%s" in result_sql or "?" in result_sql
