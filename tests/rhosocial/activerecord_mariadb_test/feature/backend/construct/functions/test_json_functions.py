# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/functions/test_json_functions.py
"""
MySQL JSON function support tests.

This module tests MariaDB-specific JSON function functionality including:
- Function version detection
- JSON_EXTRACT formatting
- JSON_UNQUOTE formatting
- JSON_OBJECT formatting
- JSON_ARRAY formatting
- JSON_CONTAINS formatting
- JSON_SET formatting
- JSON_REMOVE formatting
- JSON_TYPE formatting
- JSON_VALID formatting
- JSON_SEARCH formatting
"""
import pytest
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.json import (
    MariaDBJSONExtractExpression,
    MariaDBJSONObjectExpression,
    MariaDBJSONArrayExpression,
    MariaDBJSONContainsExpression,
)


class TestJSONFunctionProtocol:
    """Test JSON function protocol implementation."""

    def test_supports_json_type_and_path_basic(self):
        """Test the JSON family gate (MariaDB 10.2.3+)."""
        dialect_102 = MariaDBDialect(version=(10, 2, 0))
        assert not dialect_102.supports_json_type()
        assert not dialect_102.supports_json_path()

        dialect_1023 = MariaDBDialect(version=(10, 2, 3))
        assert dialect_1023.supports_json_type()
        assert dialect_1023.supports_json_path()

        dialect_103 = MariaDBDialect(version=(10, 3, 0))
        assert dialect_103.supports_json_type()

    def test_supports_json_table(self):
        """JSON_TABLE arrives with MariaDB 10.6, later than the function family."""
        dialect_103 = MariaDBDialect(version=(10, 3, 0))
        assert not dialect_103.supports_json_table()

        dialect_105 = MariaDBDialect(version=(10, 5, 0))
        assert not dialect_105.supports_json_table()

        dialect_106 = MariaDBDialect(version=(10, 6, 0))
        assert dialect_106.supports_json_table()

    def test_json_family_names_are_version_gated_internally(self):
        """Per-name answers live in the function table, not in a support switch."""
        dialect_102 = MariaDBDialect(version=(10, 2, 0))
        assert not dialect_102._is_mariadb_function_supported("json_extract")

        dialect_1023 = MariaDBDialect(version=(10, 2, 3))
        assert dialect_1023._is_mariadb_function_supported("json_extract")
        assert dialect_1023._is_mariadb_function_supported("json_value")

    def test_format_json_extract_single_path(self):
        """Test JSON_EXTRACT with single path."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        expr = MariaDBJSONExtractExpression(dialect, 'data', '$.name')
        sql, params = expr.to_sql()

        assert sql == 'JSON_EXTRACT(data, %s)'
        assert params == ('$.name',)

    def test_format_json_extract_multiple_paths(self):
        """Test JSON_EXTRACT with multiple paths."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect._format_json_extract_parts('data', '$.name', ['$.age', '$.city'])

        assert sql == 'JSON_EXTRACT(data, %s, %s, %s)'
        assert params == ('$.name', '$.age', '$.city')

    def test_format_json_unquote(self):
        """Test JSON_UNQUOTE function."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect.render_json_unquote('data->"$.name"')

        assert sql == 'JSON_UNQUOTE(data->"$.name")'
        assert params == ()

    def test_format_json_object_empty(self):
        """Test JSON_OBJECT with no arguments."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONObjectExpression(dialect, []).to_sql()

        assert sql == 'JSON_OBJECT()'
        assert params == ()

    def test_format_json_object_single_pair(self):
        """Test JSON_OBJECT with single key-value pair."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONObjectExpression(dialect, [('name', 'John')]).to_sql()

        assert sql == 'JSON_OBJECT(%s, %s)'
        assert params == ('name', 'John')

    def test_format_json_object_multiple_pairs(self):
        """Test JSON_OBJECT with multiple key-value pairs."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONObjectExpression(
            dialect, [('name', 'John'), ('age', 30), ('city', 'NYC')]
        ).to_sql()

        assert sql == 'JSON_OBJECT(%s, %s, %s, %s, %s, %s)'
        assert params == ('name', 'John', 'age', 30, 'city', 'NYC')

    def test_format_json_array_empty(self):
        """Test JSON_ARRAY with no arguments."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONArrayExpression(dialect, []).to_sql()

        assert sql == 'JSON_ARRAY()'
        assert params == ()

    def test_format_json_array_single_value(self):
        """Test JSON_ARRAY with single value."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONArrayExpression(dialect, [1]).to_sql()

        assert sql == 'JSON_ARRAY(%s)'
        assert params == (1,)

    def test_format_json_array_multiple_values(self):
        """Test JSON_ARRAY with multiple values."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONArrayExpression(dialect, [1, 'hello', None, True]).to_sql()

        assert sql == 'JSON_ARRAY(%s, %s, %s, %s)'
        assert params == (1, 'hello', None, True)

    def test_format_json_contains_no_path(self):
        """Test JSON_CONTAINS without path."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONContainsExpression(
            dialect, 'data', '{"name": "John"}'
        ).to_sql()

        assert sql == 'JSON_CONTAINS(data, %s)'
        assert params == ('{"name": "John"}',)

    def test_format_json_contains_with_path(self):
        """Test JSON_CONTAINS with path."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONContainsExpression(
            dialect, 'data', '"John"', '$.name'
        ).to_sql()

        assert sql == 'JSON_CONTAINS(data, %s, %s)'
        assert params == ('"John"', '$.name')

    def test_format_json_set_single_pair(self):
        """Test JSON_SET with single path-value pair."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect._format_json_set_parts('data', '$.name', 'John')

        assert sql == 'JSON_SET(data, %s, %s)'
        assert params == ('$.name', 'John')

    def test_format_json_set_multiple_pairs(self):
        """Test JSON_SET with multiple path-value pairs."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect._format_json_set_parts(
            'data', '$.name', 'John',
            path_value_pairs=[('$.age', 30), ('$.city', 'NYC')]
        )

        assert sql == 'JSON_SET(data, %s, %s, %s, %s, %s, %s)'
        assert params == ('$.name', 'John', '$.age', 30, '$.city', 'NYC')

    def test_format_json_remove_single_path(self):
        """Test JSON_REMOVE with single path."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect._format_json_remove_parts('data', '$.temp')

        assert sql == 'JSON_REMOVE(data, %s)'
        assert params == ('$.temp',)

    def test_format_json_remove_multiple_paths(self):
        """Test JSON_REMOVE with multiple paths."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect._format_json_remove_parts('data', '$.temp', paths=['$.cache', '$.old'])

        assert sql == 'JSON_REMOVE(data, %s, %s, %s)'
        assert params == ('$.temp', '$.cache', '$.old')

    def test_format_json_type(self):
        """Test JSON_TYPE function."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect.render_json_type('data')

        assert sql == 'JSON_TYPE(data)'
        assert params == ()

    def test_format_json_valid(self):
        """Test JSON_VALID function."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect.render_json_valid('data')

        assert sql == 'JSON_VALID(data)'
        assert params == ()

    def test_format_json_search_one(self):
        """Test JSON_SEARCH with 'one' mode."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect._format_json_search_parts('data', 'John', all_=False)

        assert "JSON_SEARCH(data, 'one', %s)" in sql
        assert params == ('John',)

    def test_format_json_search_all(self):
        """Test JSON_SEARCH with 'all' mode."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect._format_json_search_parts('data', 'John', all_=True)

        assert "JSON_SEARCH(data, 'all', %s)" in sql
        assert params == ('John',)

    def test_format_json_search_with_path(self):
        """Test JSON_SEARCH with path."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect._format_json_search_parts('data', 'John', path='$.users', all_=True)

        assert "JSON_SEARCH(data, 'all', %s, NULL, %s)" in sql
        assert params == ('John', '$.users')


class TestAsyncJSONFunctionProtocol:
    """Test async JSON function protocol (same as sync, but verifies parity)."""

    @pytest.mark.asyncio
    async def test_async_supports_json_type(self):
        """Test async version of the JSON family gate."""
        dialect = MariaDBDialect(version=(10, 2, 3))
        assert dialect.supports_json_type()
        assert dialect.supports_json_path()

    @pytest.mark.asyncio
    async def test_async_format_json_extract(self):
        """Test async version of JSON_EXTRACT formatting."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        expr = MariaDBJSONExtractExpression(dialect, 'data', '$.name')
        sql, params = expr.to_sql()

        assert 'JSON_EXTRACT' in sql
        assert params == ('$.name',)

    @pytest.mark.asyncio
    async def test_async_format_json_object(self):
        """Test async version of JSON_OBJECT formatting."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONObjectExpression(dialect, [('key', 'value')]).to_sql()

        assert 'JSON_OBJECT' in sql
        assert params == ('key', 'value')

    @pytest.mark.asyncio
    async def test_async_format_json_array(self):
        """Test async version of JSON_ARRAY formatting."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONArrayExpression(dialect, [1, 2, 3]).to_sql()

        assert 'JSON_ARRAY' in sql
        assert params == (1, 2, 3)

    @pytest.mark.asyncio
    async def test_async_format_json_contains(self):
        """Test async version of JSON_CONTAINS formatting."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = MariaDBJSONContainsExpression(
            dialect, 'data', '"value"', '$.path'
        ).to_sql()

        assert 'JSON_CONTAINS' in sql
        assert '"value"' in params

    @pytest.mark.asyncio
    async def test_async_format_json_set(self):
        """Test async version of JSON_SET formatting."""
        dialect = MariaDBDialect(version=(10, 2, 3))

        sql, params = dialect._format_json_set_parts('data', '$.key', 'value')

        assert 'JSON_SET' in sql
        assert '$.key' in params
