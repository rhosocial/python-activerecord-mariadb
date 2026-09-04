# tests/rhosocial/activerecord_mariadb_test/feature/backend/dialect/test_dialect_security.py
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
from rhosocial.activerecord.backend.expression.types import VarCharType
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
        data_type=VarCharType(length=255),
        constraints=[constraint],
    )

    sql, params = dialect.format_column_definition(col_def, ColumnConstraintType)
    assert "test''s value" in sql


def test_mysql_format_column_definition_comment_string_escaping(dialect):
    """Test COMMENT string is escaped in MySQL column definition."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type=VarCharType(length=255),
        comment="Comment with 'single quote'",
    )

    sql, params = dialect.format_column_definition(col_def, ColumnConstraintType)
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
        data_type=VarCharType(length=255),
    )

    sql, params = dialect.format_column_definition(col_def)
    assert "VARCHAR(255)" in sql


def test_mysql_format_column_definition_data_type_rejects_injection(dialect):
    """Test that malicious data_type is rejected at construction time."""
    with pytest.raises(TypeError, match="data_type must be a DataType instance"):
        ColumnDefinition(
            name="test_col",
            data_type="VARCHAR(255); DROP TABLE users--",
        )


def test_mysql_json_table_path_escaping(dialect):
    """Test JSON_TABLE raises UnsupportedFeatureError on MariaDB (path escaping)."""
    from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

    with pytest.raises(UnsupportedFeatureError):
        dialect.format_json_table_expression(expr)


def test_mysql_json_table_column_path_escaping(dialect):
    """Test JSON_TABLE raises UnsupportedFeatureError on MariaDB (column path escaping)."""
    from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

    with pytest.raises(UnsupportedFeatureError):
        dialect.format_json_table_expression(expr)


def test_mysql_json_table_alias_quoted(dialect):
    """Test JSON_TABLE raises UnsupportedFeatureError on MariaDB (alias quoting)."""
    from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

    with pytest.raises(UnsupportedFeatureError):
        dialect.format_json_table_expression(expr)


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
    """Tests for JSON_TABLE col.type validation.

    MariaDB does NOT support JSON_TABLE, so format_json_table_expression
    always raises UnsupportedFeatureError.
    """

    def test_json_table_raises_unsupported_feature(self, dialect):
        """Test format_json_table_expression raises UnsupportedFeatureError on MariaDB."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)

    def test_json_table_invalid_data_type_rejected(self, dialect):
        """Test invalid data type in JSON_TABLE column raises UnsupportedFeatureError."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)


class TestMySQLJSONTableErrorHandling:
    """Tests for JSON_TABLE col.error_handling validation.

    MariaDB does NOT support JSON_TABLE, so format_json_table_expression
    always raises UnsupportedFeatureError.
    """

    def test_json_table_valid_error_handling_null(self, dialect):
        """Test JSON_TABLE raises UnsupportedFeatureError on MariaDB."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)

    def test_json_table_valid_error_handling_error(self, dialect):
        """Test JSON_TABLE raises UnsupportedFeatureError on MariaDB."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)

    def test_json_table_valid_error_handling_default(self, dialect):
        """Test JSON_TABLE raises UnsupportedFeatureError on MariaDB."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)

    def test_json_table_invalid_error_handling_rejected(self, dialect):
        """Test JSON_TABLE raises UnsupportedFeatureError on MariaDB."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)


class TestMySQLJSONTableDefaultValueEscaping:
    """Tests for JSON_TABLE col.default_value escaping.

    MariaDB does NOT support JSON_TABLE, so format_json_table_expression
    always raises UnsupportedFeatureError.
    """

    def test_json_table_default_value_escaped(self, dialect):
        """Test JSON_TABLE raises UnsupportedFeatureError on MariaDB."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)


class TestMySQLJSONTableJsonDocSecurity:
    """Tests for JSON_TABLE json_doc type validation.

    MariaDB does NOT support JSON_TABLE, so format_json_table_expression
    always raises UnsupportedFeatureError.
    """

    def test_json_table_json_doc_string(self, dialect):
        """Test JSON_TABLE raises UnsupportedFeatureError on MariaDB."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)

    def test_json_table_json_doc_to_sql_protocol_rejected_by_validate(self, dialect):
        """Test json_doc as ToSQLProtocol raises UnsupportedFeatureError on MariaDB."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_json_table_expression(expr)

    def test_json_table_json_doc_invalid_type_rejected(self, dialect):
        """Test json_doc with invalid type raises UnsupportedFeatureError on MariaDB."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
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

        with pytest.raises(UnsupportedFeatureError):
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


# ============================================================
# format_storage_options — key quoting and value escaping
# ============================================================

def test_storage_options_normal_key_and_value(dialect):
    """Normal storage option key is plain, string value is quoted and escaped."""
    sql = dialect.format_storage_options({"ENGINE": "InnoDB"})
    assert "ENGINE='InnoDB'" in sql


def test_storage_options_string_value_escaped(dialect):
    """String value with single quote is properly escaped."""
    sql = dialect.format_storage_options({"ENGINE": "It's"})
    assert "It''s" in sql


def test_storage_options_int_value(dialect):
    """Integer value is not quoted."""
    sql = dialect.format_storage_options({"AUTO_INCREMENT": 1000})
    assert "AUTO_INCREMENT=1000" in sql


def test_storage_options_string_injection_value_escaped(dialect):
    """String value with injection payload is safely escaped inside quotes."""
    sql = dialect.format_storage_options({"ENGINE": "x'; DROP TABLE t--"})
    assert "'x''; DROP TABLE t--'" in sql
    assert sql.count("'") % 2 == 0, f"Unbalanced quotes: {sql}"


# ============================================================
# format_identifier — identifier quoting equivalence and injection immunity
# ============================================================

def test_format_identifier_normal(dialect):
    """Normal identifier is backtick-quoted."""
    result = dialect.format_identifier("users")
    assert result == "`users`"


def test_format_identifier_with_backtick(dialect):
    """Identifier with embedded backtick is properly escaped."""
    result = dialect.format_identifier("table`name")
    assert result == "`table``name`"


def test_format_identifier_injection_payload(dialect):
    """Identifier with injection payload is safely contained (balanced backticks)."""
    payload = "users`; DROP TABLE users--"
    result = dialect.format_identifier(payload)
    assert result.count('`') % 2 == 0, f"Unbalanced backticks: {result}"
    assert result == "`users``; DROP TABLE users--`"


def test_format_identifier_naive_vs_proper_safe(dialect):
    """For safe input, naive and proper quoting produce same structure."""
    names = ["users", "orders", "products", "table_1", "camelCase"]
    for name in names:
        naive = f"`{name}`"
        proper = dialect.format_identifier(name)
        assert naive == proper, f"Mismatch for '{name}': naive={naive}, proper={proper}"


def test_format_identifier_naive_vs_proper_malicious(dialect):
    """For malicious input, proper quoting prevents breakout that naive allows."""
    payloads = [
        'x`; DROP TABLE users--',
        'y`; DELETE FROM t--',
        'z`; UPDATE t SET a=1--',
    ]
    for payload in payloads:
        naive = f"`{payload}`"
        proper = dialect.format_identifier(payload)

        assert naive.count('`') % 2 != 0, \
            f"Naive should unbalance backticks for '{payload}': {naive}"
        assert proper.count('`') % 2 == 0, \
            f"Proper should balance backticks for '{payload}': {proper}"


def test_format_identifier_empty_string(dialect):
    """Empty identifier produces empty backticks."""
    assert dialect.format_identifier("") == "``"


# ── Savepoint identifier escaping ─────────────────────────────────────


def test_savepoint_name_escaped_via_format_identifier():
    """savepoint name must be escaped via format_identifier to prevent injection.

    Regression guard: MariaDB transaction.py's _do_create_savepoint /
    _do_release_savepoint / _do_rollback_savepoint must use
    format_identifier(name) instead of bare name concatenation.
    """
    from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
    d = MariaDBDialect()

    # Normal savepoint name
    assert d.format_identifier("sp1") == "`sp1`"

    # Name with embedded backtick — must be escaped via double-backtick
    escaped = d.format_identifier("sp`1")
    assert escaped == "`sp``1`"
    # In MariaDB backticks are escaped by doubling
    assert escaped.count("`") % 2 == 0, "balanced backticks"

    # Name with spaces
    assert d.format_identifier("my savepoint") == "`my savepoint`"

    # Name with SQL keyword — format_identifier must quote it
    assert d.format_identifier("DROP TABLE") == "`DROP TABLE`"

    # Empty string
    assert d.format_identifier("") == "``"


def test_savepoint_direct_concat_rejected():
    """Verify that naive backtick concatenation is unsafe.

    This is a negative test: format_identifier must NOT produce unbalanced
    backticks.  A naive ``f"`{name}`"`` would be vulnerable.
    """
    from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
    d = MariaDBDialect()

    payloads = [
        "sp`; DROP TABLE users--",
        "sp`; DELETE FROM t--",
    ]
    for payload in payloads:
        proper = d.format_identifier(payload)
        assert proper.count("`") % 2 == 0, \
            f"format_identifier must produce balanced backticks for '{payload}': {proper}"