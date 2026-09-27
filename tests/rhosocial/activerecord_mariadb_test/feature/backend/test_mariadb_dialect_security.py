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
from rhosocial.activerecord.backend.expression import ColumnCommentClause, TableCommentClause
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


@pytest.fixture
def json_table_dialect():
    """An adapted dialect on a version that supports JSON_TABLE (10.6+).

    The plain ``dialect`` fixture is unadapted, so any version gate raises
    DialectNotAdaptedException before it can return. The JSON_TABLE tests
    need a concrete version.
    """
    return MariaDBDialect(version=(10, 6, 0))


def test_mysql_format_column_definition_default_string_escaping(dialect):
    """Test DEFAULT constraint string is escaped in MySQL."""
    constraint = ColumnConstraint(
        dialect,
        constraint_type=ColumnConstraintType.DEFAULT,
        default_value="test's value",
    )

    col_def = ColumnDefinition(
        dialect,
        name="test_col",
        data_type=VarCharType(dialect, 255),
        constraints=[constraint],
    )

    sql, params = dialect.format_column_definition(col_def)
    assert "test''s value" in sql


def test_mysql_format_column_definition_comment_string_escaping(dialect):
    """Test COMMENT string is escaped in MySQL column definition."""
    col_def = ColumnDefinition(
        dialect,
        name="test_col",
        data_type=VarCharType(dialect, 255),
        comment=ColumnCommentClause(dialect, "Comment with 'single quote'"),
    )

    sql, params = dialect.format_column_definition(col_def)
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
        dialect,
        name="test_col",
        data_type=VarCharType(dialect, 255),
    )

    sql, params = dialect.format_column_definition(col_def)
    assert "VARCHAR(255)" in sql


def test_mysql_format_column_definition_data_type_rejects_injection(dialect):
    """Test that malicious data_type is rejected at construction time."""
    with pytest.raises(TypeError, match="data_type must be a DataType instance"):
        ColumnDefinition(
            dialect,
            name="test_col",
            data_type="VARCHAR(255); DROP TABLE users--",
        )

def test_mysql_json_table_path_escaping(json_table_dialect):
    """A single quote in the JSON_TABLE path is escaped, not injected.

    This test used to assert UnsupportedFeatureError on the belief that
    MariaDB lacks JSON_TABLE, which meant the escaping was never checked.
    """
    dialect = json_table_dialect
    expr = MariaDBJSONTableExpression(
        dialect=dialect,
        json_doc='{"key": "value"}',
        path="$.key's",
        columns=[JSONTableColumn(name="col1", type="VARCHAR(255)", path="$.name")],
    )

    sql, _ = dialect.format_json_table_expression(expr)
    assert "$.key''s" in sql
    assert "key's" not in sql


def test_mysql_json_table_column_path_escaping(json_table_dialect):
    """A single quote in a column path is escaped."""
    dialect = json_table_dialect
    expr = MariaDBJSONTableExpression(
        dialect=dialect,
        json_doc='{"data": "test"}',
        path="$.data",
        columns=[JSONTableColumn(name="col1", type="VARCHAR(255)", path="$.field's")],
    )

    sql, _ = dialect.format_json_table_expression(expr)
    assert "$.field''s" in sql
    assert "field's" not in sql


def test_mysql_json_table_json_doc_escaped(json_table_dialect):
    """A json_doc string is emitted as a quoted literal, not raw SQL."""
    dialect = json_table_dialect
    expr = MariaDBJSONTableExpression(
        dialect=dialect,
        json_doc="""{"a": "b'; DROP TABLE users--"}""",
        path="$.a",
        columns=[JSONTableColumn(name="col1", type="VARCHAR(255)", path="$.col1")],
    )

    sql, _ = dialect.format_json_table_expression(expr)
    assert "DROP TABLE users--" in sql
    # The quote is doubled, so the literal cannot be terminated early.
    assert "b''; DROP TABLE users--" in sql


def test_mysql_json_table_alias_quoted(json_table_dialect):
    """The JSON_TABLE alias is emitted as a quoted identifier."""
    dialect = json_table_dialect
    expr = MariaDBJSONTableExpression(
        dialect=dialect,
        json_doc='{"data": "test"}',
        path="$.data",
        columns=[JSONTableColumn(name="col1", type="VARCHAR(255)", path="$.col1")],
        alias="test_alias",
    )

    sql, _ = dialect.format_json_table_expression(expr)
    assert sql.endswith("AS `test_alias`")


class TestMySQLJSONTableVersionGate:
    """JSON_TABLE requires MariaDB 10.6."""

    def test_rejected_below_10_6(self):
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )
        old = MariaDBDialect(version=(10, 5, 9))
        expr = MariaDBJSONTableExpression(
            dialect=old,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[JSONTableColumn(name="col1", type="VARCHAR(255)", path="$.col1")],
        )
        with pytest.raises(UnsupportedFeatureError, match="10.6"):
            old.format_json_table_expression(expr)

    @pytest.mark.parametrize("version", [(10, 6, 0), (12, 3, 3), (13, 0, 2), (13, 1, 1)])
    def test_accepted_from_10_6(self, version):
        dialect = MariaDBDialect(version=version)
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[JSONTableColumn(name="col1", type="VARCHAR(255)", path="$.col1")],
        )
        sql, params = dialect.format_json_table_expression(expr)
        assert sql.startswith("JSON_TABLE(")
        assert params == ()


class TestMySQLJSONTableTypeValidation:
    """JSON_TABLE column types are interpolated, so they are allow-listed."""

    def test_plain_type_accepted(self, json_table_dialect):
        dialect = json_table_dialect
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[JSONTableColumn(name="col1", type="VARCHAR(255)", path="$.col1")],
        )
        sql, _ = dialect.format_json_table_expression(expr)
        assert "`col1` VARCHAR(255) PATH '$.col1'" in sql

    def test_injected_type_rejected(self, json_table_dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )
        dialect = json_table_dialect
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
    """JSON_TABLE ON EMPTY / ON ERROR rendering and validation."""

    def _expr(self, dialect, error_handling, default_value=None):
        return MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc='{"data": "test"}',
            path="$.data",
            columns=[
                JSONTableColumn(
                    name="col1",
                    type="VARCHAR(255)",
                    path="$.col1",
                    error_handling=error_handling,
                    default_value=default_value,
                ),
            ],
        )

    def test_null_on_empty_and_error(self, json_table_dialect):
        sql, _ = json_table_dialect.format_json_table_expression(
            self._expr(json_table_dialect, "NULL")
        )
        assert "PATH '$.col1' NULL ON EMPTY NULL ON ERROR" in sql

    def test_default_on_empty_and_error(self, json_table_dialect):
        sql, _ = json_table_dialect.format_json_table_expression(
            self._expr(json_table_dialect, "DEFAULT", default_value="fallback")
        )
        assert (
            "PATH '$.col1' DEFAULT 'fallback' ON EMPTY DEFAULT 'fallback' ON ERROR"
            in sql
        )

    def test_default_value_is_escaped(self, json_table_dialect):
        sql, _ = json_table_dialect.format_json_table_expression(
            self._expr(json_table_dialect, "DEFAULT", default_value="a'; DROP TABLE t--")
        )
        assert "a''; DROP TABLE t--" in sql

    def test_unknown_error_handling_rejected(self, json_table_dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )
        with pytest.raises(UnsupportedFeatureError, match="error handling"):
            json_table_dialect.format_json_table_expression(
                self._expr(json_table_dialect, "INVALID")
            )


class TestMySQLJSONTableColumnOptions:
    """FOR ORDINALITY, EXISTS and NESTED PATH rendering."""

    def test_ordinality_takes_no_type_or_path(self, json_table_dialect):
        dialect = json_table_dialect
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc="doc",
            path="$[*]",
            columns=[JSONTableColumn(name="row_n", type="INT", path="$.n", ordinality=True)],
        )
        sql, _ = dialect.format_json_table_expression(expr)
        assert "`row_n` FOR ORDINALITY" in sql

    def test_exists_sits_between_type_and_path(self, json_table_dialect):
        dialect = json_table_dialect
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc="doc",
            path="$[*]",
            columns=[JSONTableColumn(name="has", type="INT", path="$.h", exists=True)],
        )
        sql, _ = dialect.format_json_table_expression(expr)
        assert "`has` INT EXISTS PATH '$.h'" in sql

    def test_nested_path_rendered(self, json_table_dialect):
        from rhosocial.activerecord.backend.impl.mariadb.expression.json_table import (
            NestedPath,
        )
        dialect = json_table_dialect
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc="doc",
            path="$[*]",
            columns=[JSONTableColumn(name="a", type="INT", path="$.a")],
            nested_paths=[NestedPath("$.n", [JSONTableColumn(name="b", type="INT", path="$.b")], alias="np")],
        )
        sql, _ = dialect.format_json_table_expression(expr)
        # MariaDB's grammar has no alias on NESTED PATH; emitting one is a
        # syntax error, so it is dropped even when the node carries an alias.
        assert "NESTED PATH '$.n' COLUMNS(`b` INT PATH '$.b')" in sql
        assert "np" not in sql

    def test_column_name_quoted(self, json_table_dialect):
        dialect = json_table_dialect
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc="doc",
            path="$[*]",
            columns=[JSONTableColumn(name="select", type="INT", path="$.s")],
        )
        sql, _ = dialect.format_json_table_expression(expr)
        assert "`select`" in sql


class TestMySQLJSONTableJsonDocTypeValidation:
    """json_doc must be a string literal or an expression."""

    def test_expression_accepted(self, json_table_dialect):
        from rhosocial.activerecord.backend.expression import TableExpression
        dialect = json_table_dialect
        expr = MariaDBJSONTableExpression(
            dialect=dialect,
            json_doc=TableExpression(dialect, "t", alias="j"),
            path="$[*]",
            columns=[JSONTableColumn(name="a", type="INT", path="$.a")],
        )
        sql, params = dialect.format_json_table_expression(expr)
        assert sql.startswith("JSON_TABLE(")
        assert "`t`" in sql or "t" in sql

    @pytest.mark.parametrize("bad", [123, None, ["x"], {"a": 1}])
    def test_non_string_non_expression_rejected(self, json_table_dialect, bad):
        with pytest.raises(TypeError):
            json_table_dialect.format_json_table_expression(
                MariaDBJSONTableExpression(
                    dialect=json_table_dialect,
                    json_doc=bad,
                    path="$[*]",
                    columns=[JSONTableColumn(name="a", type="INT", path="$.a")],
                )
            )


class TestMySQLCreateTableCommentEscaping:
    """Tests for CREATE TABLE COMMENT escaping."""

    def test_create_table_comment_escaped(self, dialect):
        """Test table-level COMMENT is properly escaped."""
        from rhosocial.activerecord.backend.expression.statements import (
            CreateTableExpression,
            CreateTableOptions,
        )

        expr = CreateTableExpression(
            dialect=dialect,
            table="test_table",
            columns=[],
            table_options=CreateTableOptions(
                dialect, comment=TableCommentClause(dialect, "Table's comment with 'quotes'")
            ),
        )

        sql, params = dialect.format_create_table_statement(expr)

        assert "Table''s comment" in sql
        assert "quotes''" in sql
        assert "'; DROP" not in sql

    def test_create_table_comment_with_backslash(self, dialect):
        """Test table-level COMMENT with backslash is properly escaped."""
        from rhosocial.activerecord.backend.expression.statements import (
            CreateTableExpression,
            CreateTableOptions,
        )

        expr = CreateTableExpression(
            dialect=dialect,
            table="test_table",
            columns=[],
            table_options=CreateTableOptions(dialect, comment=TableCommentClause(dialect, "Test\\value")),
        )

        sql, params = dialect.format_create_table_statement(expr)

        assert "\\\\" in sql


# ============================================================
# _format_storage_options — key quoting and value escaping
# ============================================================

def test_storage_options_normal_key_and_value(dialect):
    """Normal storage option key is plain, string value is quoted and escaped."""
    sql = dialect._format_storage_options({"ENGINE": "InnoDB"})
    assert "ENGINE='InnoDB'" in sql


def test_storage_options_string_value_escaped(dialect):
    """String value with single quote is properly escaped."""
    sql = dialect._format_storage_options({"ENGINE": "It's"})
    assert "It''s" in sql


def test_storage_options_int_value(dialect):
    """Integer value is not quoted."""
    sql = dialect._format_storage_options({"AUTO_INCREMENT": 1000})
    assert "AUTO_INCREMENT=1000" in sql


def test_storage_options_string_injection_value_escaped(dialect):
    """String value with injection payload is safely escaped inside quotes."""
    sql = dialect._format_storage_options({"ENGINE": "x'; DROP TABLE t--"})
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