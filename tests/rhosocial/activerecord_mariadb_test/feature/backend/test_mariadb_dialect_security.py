# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_dialect_security.py
"""
Tests for MySQL dialect SQL injection security fixes.

This test module verifies that string escaping and validation
methods properly sanitize user input to prevent SQL injection.
Tests are run against the actual MySQL dialect.
"""
import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.json_table import (
    MariaDBJSONTableExpression,
    JSONTableColumn,
)


@pytest.fixture
def dialect():
    """Create a MySQL test dialect."""
    return MariaDBDialect()


def test_mysql_format_column_definition_default_string_escaping(dialect):
    """Test DEFAULT constraint string is escaped in MySQL."""
    constraint = ColumnConstraint(
        constraint_type=ColumnConstraintType.DEFAULT,
        default_value="test's value",
    )

    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255)",
        constraints=[constraint],
    )

    sql, params = dialect._format_column_definition_mariadb(col_def, ColumnConstraintType)
    assert "test''s value" in sql


def test_mysql_format_column_definition_comment_string_escaping(dialect):
    """Test COMMENT string is escaped in MySQL column definition."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255)",
        comment="Comment with 'single quote'",
    )

    sql, params = dialect._format_column_definition_mariadb(col_def, ColumnConstraintType)
    assert "Comment with ''single quote''" in sql


def test_mysql_escape_sql_string(dialect):
    """Test MySQL inherits _escape_sql_string."""
    result = dialect._escape_sql_string("Table's comment")
    assert result == "Table''s comment"


def test_mysql_validate_data_type(dialect):
    """Test MySQL inherits _validate_data_type."""
    assert dialect._validate_data_type("VARCHAR(255)")
    assert dialect._validate_data_type("INT")
    assert dialect._validate_data_type("BIGINT")
    assert not dialect._validate_data_type("INT; DROP TABLE users--")


def test_mysql_format_column_definition_data_type_validation(dialect):
    """Test column definition validates data_type."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255)",
    )

    sql, params = dialect.format_column_definition(col_def)
    assert "VARCHAR(255)" in sql


def test_mysql_format_column_definition_data_type_rejects_injection(dialect):
    """Test that malicious data_type is rejected."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255); DROP TABLE users--",
    )

    with pytest.raises(ValueError, match="Invalid data type"):
        dialect.format_column_definition(col_def)


def test_mysql_json_table_path_escaping(dialect):
    """Test JSON_TABLE path is escaped."""
    expr = MariaDBJSONTableExpression(
        dialect=dialect,
        json_doc='{"key": "value"}',
        path="$.key's",
        columns=[
            JSONTableColumn(
                name="col1",
                type="VARCHAR(255)",
                path="$.name",
            ),
        ],
    )

    sql, params = dialect.format_json_table_expression(expr)

    assert "key''s" in sql
    assert "'; DROP" not in sql


def test_mysql_json_table_column_path_escaping(dialect):
    """Test JSON_TABLE column path is escaped."""
    expr = MariaDBJSONTableExpression(
        dialect=dialect,
        json_doc='{"data": "test"}',
        path="$.data",
        columns=[
            JSONTableColumn(
                name="col1",
                type="VARCHAR(255)",
                path="$.field's",
            ),
        ],
    )

    sql, params = dialect.format_json_table_expression(expr)

    assert "field''s" in sql


def test_mysql_json_table_alias_quoted(dialect):
    """Test JSON_TABLE alias uses format_identifier (backticks for MySQL)."""
    expr = MariaDBJSONTableExpression(
        dialect=dialect,
        json_doc='{"data": "test"}',
        path="$.data",
        columns=[
            JSONTableColumn(
                name="col1",
                type="VARCHAR(255)",
                path="$.col1",
            ),
        ],
        alias="test_alias",
    )

    sql, params = dialect.format_json_table_expression(expr)

    # MySQL uses backticks for identifier quotes
    assert "`test_alias`" in sql


def test_mysql_format_cast_expression_valid(dialect):
    """Test that CAST expression validates target_type."""
    sql, params = dialect.format_cast_expression("column", "INTEGER", (), None)
    assert "INTEGER" in sql


def test_mysql_format_cast_expression_rejects_injection(dialect):
    """Test that malicious target_type is rejected."""
    with pytest.raises(ValueError, match="Invalid target type"):
        dialect.format_cast_expression("column", "INTEGER; DROP TABLE users--", (), None)


class TestMySQLEscapeSqlStringBackslash:
    """Tests for MySQL _escape_sql_string with backslash escaping."""

    def test_escape_sql_string_backslash_escaped(self, dialect):
        """Test backslash is properly escaped in MySQL."""
        result = dialect._escape_sql_string("test\\value")
        assert "\\\\" in result

    def test_escape_sql_string_backslash_and_quote(self, dialect):
        """Test both backslash and single quote are escaped."""
        result = dialect._escape_sql_string("test\\'value")
        assert "\\\\" in result
        assert "''" in result

    def test_escape_sql_string_preserves_others(self, dialect):
        """Test other characters are preserved."""
        result = dialect._escape_sql_string('test"double"value')
        assert "test\"double\"value" in result


class TestMySQLJSONTableTypeValidation:
    """Tests for JSON_TABLE col.type validation."""

    def test_json_table_valid_data_type(self, dialect):
        """Test valid data type in JSON_TABLE column."""
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                ),
            ],
        )

        sql, params = dialect.format_json_table_expression(expr)
        assert "VARCHAR(255)" in sql

    def test_json_table_invalid_data_type_rejected(self, dialect):
        """Test invalid data type in JSON_TABLE column is rejected."""
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255); DROP TABLE users--",
                    path="$.col1",
                ),
            ],
        )

        with pytest.raises(ValueError, match="Invalid data type"):
            dialect.format_json_table_expression(expr)


class TestMySQLJSONTableErrorHandling:
    """Tests for JSON_TABLE col.error_handling validation."""

    def test_json_table_valid_error_handling_null(self, dialect):
        """Test valid error_handling: NULL."""
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                    error_handling="NULL",
                ),
            ],
        )

        sql, params = dialect.format_json_table_expression(expr)
        assert "NULL ON ERROR" in sql

    def test_json_table_valid_error_handling_error(self, dialect):
        """Test valid error_handling: ERROR."""
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                    error_handling="ERROR",
                ),
            ],
        )

        sql, params = dialect.format_json_table_expression(expr)
        assert "ERROR ON ERROR" in sql

    def test_json_table_valid_error_handling_default(self, dialect):
        """Test valid error_handling: DEFAULT with default_value."""
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                    error_handling="DEFAULT",
                    default_value="fallback",
                ),
            ],
        )

        sql, params = dialect.format_json_table_expression(expr)
        assert "DEFAULT" in sql
        assert "fallback" in sql

    def test_json_table_invalid_error_handling_rejected(self, dialect):
        """Test invalid error_handling is rejected."""
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                    error_handling="INVALID",
                ),
            ],
        )

        with pytest.raises(ValueError, match="Invalid error_handling"):
            dialect.format_json_table_expression(expr)


class TestMySQLJSONTableDefaultValueEscaping:
    """Tests for JSON_TABLE col.default_value escaping."""

    def test_json_table_default_value_escaped(self, dialect):
        """Test default_value with single quotes is escaped."""
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                    error_handling="DEFAULT",
                    default_value="it's broken",
                ),
            ],
        )

        sql, params = dialect.format_json_table_expression(expr)
        assert "it''s broken" in sql
        assert "'; DROP" not in sql


class TestMySQLJSONTableJsonDocSecurity:
    """Tests for JSON_TABLE json_doc type validation."""

    def test_json_table_json_doc_string(self, dialect):
        """Test json_doc as string is properly escaped."""
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"key": "value"}',
            path="$.key",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                ),
            ],
        )

        sql, params = dialect.format_json_table_expression(expr)
        assert "key" in sql

    def test_json_table_json_doc_to_sql_protocol_rejected_by_validate(self, dialect):
        """Test json_doc as ToSQLProtocol is rejected by validate in strict mode.

        Note: This test demonstrates the current limitation - the dialect code at
        lines 1614-1616 supports ToSQLProtocol, but validate() at line 1605 rejects
        it in strict mode. To enable ToSQLProtocol support, validate() needs modification.
        """
        from rhosocial.activerecord.backend.expression.bases import BaseExpression

        class MockExpression(BaseExpression):
            def __init__(self):
                self._sql = "JSON_COLUMN"
                self._params = ()

            def to_sql(self):
                return self._sql, self._params

        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc=MockExpression(),
            path="$.key",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                ),
            ],
        )

        with pytest.raises(TypeError, match="json_doc must be str"):
            dialect.format_json_table_expression(expr)

    def test_json_table_json_doc_invalid_type_rejected(self, dialect):
        """Test json_doc with invalid type is rejected (raises before our check)."""
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc={"key": "value"},
            path="$.key",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                ),
            ],
        )

        with pytest.raises(TypeError, match="json_doc must be str"):
            dialect.format_json_table_expression(expr)


class TestMySQLCreateTableCommentEscaping:
    """Tests for CREATE TABLE COMMENT escaping."""

    def test_create_table_comment_escaped(self, dialect):
        """Test table-level COMMENT is properly escaped."""
        from rhosocial.activerecord.backend.expression.statements import CreateTableExpression

        expr = CreateTableExpression(
            dialect=dialect,
            table="test_table",
            columns=[],
            dialect_options={
                "comment": "Table's comment with 'quotes'",
            },
        )

        sql, params = dialect.format_create_table_statement(expr)

        assert "Table''s comment" in sql
        assert "quotes''" in sql
        assert "'; DROP" not in sql

    def test_create_table_comment_with_backslash(self, dialect):
        """Test table-level COMMENT with backslash is properly escaped."""
        from rhosocial.activerecord.backend.expression.statements import CreateTableExpression

        expr = CreateTableExpression(
            dialect=dialect,
            table="test_table",
            columns=[],
            dialect_options={
                "comment": "Test\\value",
            },
        )

        sql, params = dialect.format_create_table_statement(expr)

        assert "\\\\" in sql