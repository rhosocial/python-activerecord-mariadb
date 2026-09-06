# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_show_introspector.py
"""Offline coverage for the MySQL SHOW sub-introspector.

SyncShowIntrospector builds SHOW expressions and parses rows through pure
_parse_* helpers; feeding a mock executor lets every public method be
exercised without a live server. Each test asserts both the generated SQL
and the parsed result fields.
"""

from unittest.mock import MagicMock

import pytest

from rhosocial.activerecord.backend.impl.mariadb.introspection.show_introspector import (
    SyncShowIntrospector,
)


@pytest.fixture
def introspector():
    """Build a SyncShowIntrospector over a mock executor capturing SQL.

    The backend mock carries a *real* MariaDBDialect so expression to_sql()
    returns genuine (sql, params) tuples — only the executor is faked.
    """
    executor = MagicMock()
    executor.execute.return_value = []
    backend = MagicMock()
    from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
    backend.dialect = MariaDBDialect()
    return SyncShowIntrospector(backend, executor), executor


def _set_rows(executor, rows):
    executor.execute.return_value = rows


class TestShowIntrospectorSQL:
    """Each public method must issue the expected SHOW statement."""

    def test_create_table_sql(self, introspector):
        """create_table issues SHOW CREATE TABLE with optional schema."""
        intr, executor = introspector
        _set_rows(executor, [{"Table": "users", "Create Table": "CREATE TABLE `users` (id INT)"}])

        result = intr.create_table("users")
        sql, params = executor.execute.call_args[0]
        assert sql == "SHOW CREATE TABLE `users`", f"unexpected SQL: {sql}"
        assert params == (), "no params for SHOW CREATE TABLE"
        assert result.table_name == "users", "parsed table name should match"
        assert "CREATE TABLE" in result.create_statement, "create statement should be parsed"

    def test_create_table_with_schema(self, introspector):
        """Schema-qualified create_table prefixes the schema name."""
        intr, executor = introspector
        _set_rows(executor, [{"Table": "users", "Create Table": "CREATE TABLE `users` (id INT)"}])

        intr.create_table("users", schema="shop")
        sql, _ = executor.execute.call_args[0]
        # MySQL SHOW statements do not embed the schema; the connector's
        # current database scopes the name.
        assert sql == "SHOW CREATE TABLE `users`", f"schema must not alter SQL: {sql}"

    def test_create_table_missing_returns_none(self, introspector):
        """An empty result means the table does not exist — parse returns None."""
        intr, executor = introspector
        _set_rows(executor, [])
        assert intr.create_table("ghost") is None, "missing table should parse to None"

    def test_create_view_sql(self, introspector):
        """create_view issues SHOW CREATE VIEW and parses the statement."""
        intr, executor = introspector
        _set_rows(executor, [{"View": "v_users", "Create View": "CREATE VIEW `v_users` AS SELECT 1"}])

        result = intr.create_view("v_users")
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW CREATE VIEW `v_users`", f"unexpected SQL: {sql}"
        assert result.view_name == "v_users", "parsed view name should match"
        assert "CREATE VIEW" in result.create_statement, "create statement should be parsed"

    def test_columns_sql(self, introspector):
        """columns issues SHOW FULL COLUMNS and parses fields."""
        intr, executor = introspector
        _set_rows(executor, [
            {"Field": "id", "Type": "int", "Null": "NO", "Key": "PRI", "Default": None, "Extra": ""},
        ])

        columns = intr.columns("users")
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW COLUMNS FROM `users`", f"unexpected SQL: {sql}"
        assert columns[0].field == "id", "parsed column field should match"
        assert columns[0].type == "int", "parsed column type should match"

    def test_indexes_sql(self, introspector):
        """indexes issues SHOW INDEX and parses key metadata."""
        intr, executor = introspector
        _set_rows(executor, [{
            "Table": "users", "Non_unique": 0, "Key_name": "PRIMARY",
            "Seq_in_index": 1, "Column_name": "id", "Index_type": "BTREE",
        }])

        indexes = intr.indexes("users")
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW INDEX FROM `users`", f"unexpected SQL: {sql}"
        assert indexes[0].key_name == "PRIMARY", "parsed key name should match"

    def test_tables_sql(self, introspector):
        """tables issues SHOW FULL TABLES and parses names/types."""
        intr, executor = introspector
        _set_rows(executor, [{"Tables_in_shop": "users", "Table_type": "BASE TABLE"}])

        tables = intr.tables(schema="shop", full=True)
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW FULL TABLES", f"unexpected SQL: {sql}"
        assert tables[0].name == "users", "parsed table name should match"
        assert tables[0].table_type == "BASE TABLE", "parsed table type should match"

    def test_databases_sql(self, introspector):
        """databases issues SHOW DATABASES with optional LIKE."""
        intr, executor = introspector
        _set_rows(executor, [{"Database": "shop"}])

        databases = intr.databases()
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW DATABASES", f"unexpected SQL: {sql}"
        assert databases[0].name == "shop", "parsed database name should match"

    def test_databases_like(self, introspector):
        """A LIKE pattern is appended to SHOW DATABASES."""
        intr, executor = introspector
        _set_rows(executor, [])
        intr.databases(like="shop%")
        sql, params = executor.execute.call_args[0]
        assert sql == "SHOW DATABASES LIKE %s", f"LIKE should be appended: {sql}"
        assert params == ("shop%",), "LIKE pattern should be a bound parameter"

    def test_table_status_sql(self, introspector):
        """table_status issues SHOW TABLE STATUS and parses engine fields."""
        intr, executor = introspector
        _set_rows(executor, [{"Name": "users", "Engine": "InnoDB", "Rows": 10}])

        status = intr.table_status(schema="shop")
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW TABLE STATUS", f"unexpected SQL: {sql}"
        assert status[0].name == "users", "parsed name should match"
        assert status[0].engine == "InnoDB", "parsed engine should match"

    def test_triggers_sql(self, introspector):
        """triggers issues SHOW TRIGGERS and parses trigger metadata."""
        intr, executor = introspector
        _set_rows(executor, [{"Trigger": "trg", "Event": "INSERT", "Table": "users"}])

        triggers = intr.triggers(schema="shop")
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW TRIGGERS", f"unexpected SQL: {sql}"
        assert triggers[0].trigger_name == "trg", "parsed trigger name should match"

    def test_create_trigger_sql(self, introspector):
        """create_trigger issues SHOW CREATE TRIGGER."""
        intr, executor = introspector
        _set_rows(executor, [{"Trigger": "trg", "SQL Original Statement": "CREATE TRIGGER trg ..."}])

        result = intr.create_trigger("trg")
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW CREATE TRIGGER `trg`", f"unexpected SQL: {sql}"
        assert result.trigger_name == "trg", "parsed trigger name should match"

    def test_variables_sql(self, introspector):
        """variables issues SHOW VARIABLES with optional LIKE."""
        intr, executor = introspector
        _set_rows(executor, [{"Variable_name": "max_connections", "Value": "151"}])

        variables = intr.variables(like="max_%")
        sql, params = executor.execute.call_args[0]
        assert sql == "SHOW VARIABLES LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("max_%",), "LIKE pattern should be a bound parameter"
        assert variables[0].variable_name == "max_connections", "parsed name should match"
        assert variables[0].value == "151", "parsed value should match"

    def test_status_sql_session(self, introspector):
        """status defaults to the session scope."""
        intr, executor = introspector
        _set_rows(executor, [{"Variable_name": "Uptime", "Value": "100"}])

        intr.status()
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW STATUS", f"session default renders bare SHOW STATUS: {sql}"

    def test_status_sql_global(self, introspector):
        """status(session=False) issues SHOW GLOBAL STATUS."""
        intr, executor = introspector
        _set_rows(executor, [])
        intr.status(session=False)
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW GLOBAL STATUS", f"global scope expected: {sql}"

    def test_processlist_sql(self, introspector):
        """processlist issues SHOW PROCESSLIST (FULL when requested)."""
        intr, executor = introspector
        _set_rows(executor, [])
        intr.processlist()
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW PROCESSLIST", f"unexpected SQL: {sql}"

        intr.processlist(full=True)
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW FULL PROCESSLIST", "FULL variant expected"

    def test_warnings_and_errors_sql(self, introspector):
        """warnings/errors issue SHOW WARNINGS/ERRORS with LIMIT."""
        intr, executor = introspector
        _set_rows(executor, [])
        intr.warnings(limit=5)
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW WARNINGS LIMIT 5", f"LIMIT should be appended: {sql}"

        intr.errors()
        sql, _ = executor.execute.call_args[0]
        assert sql == "SHOW ERRORS", f"unexpected SQL: {sql}"

    def test_engines_charset_collation_plugins_sql(self, introspector):
        """engines/charset/collation/plugins issue their SHOW statements."""
        intr, executor = introspector
        _set_rows(executor, [])
        intr.engines()
        assert executor.execute.call_args[0][0] == "SHOW ENGINES", "engines SQL expected"
        intr.charset(like="utf8%")
        assert executor.execute.call_args[0][0] == "SHOW CHARACTER SET LIKE %s", "charset SQL expected"
        assert executor.execute.call_args[0][1] == ("utf8%",), "charset LIKE should be a bound parameter"
        intr.collation()
        assert executor.execute.call_args[0][0] == "SHOW COLLATION", "collation SQL expected"
        intr.plugins()
        assert executor.execute.call_args[0][0] == "SHOW PLUGINS", "plugins SQL expected"

    def test_grants_sql(self, introspector):
        """grants issues SHOW GRANTS (FOR user@host when given)."""
        intr, executor = introspector
        _set_rows(executor, [])
        intr.grants()
        assert executor.execute.call_args[0][0] == "SHOW GRANTS", "bare grants SQL expected"

        intr.grants(user="app", host="10.0.0.%")
        sql, params = executor.execute.call_args[0]
        assert sql == "SHOW GRANTS FOR %s@%s", "user@host grants SQL expected"
        assert params == ("app", "10.0.0.%"), "grants user/host should be bound parameters"


class TestShowIntrospectorParseEdgeCases:
    """Parse helpers must tolerate alternate driver key casings."""

    def test_parse_create_table_uppercase_keys(self, introspector):
        """Some drivers return TABLE/CREATE TABLE keys — both must parse."""
        intr, _ = introspector
        result = SyncShowIntrospector._parse_create_table(
            [{"TABLE": "t", "CREATE TABLE": "CREATE TABLE t (id INT)"}], "t"
        )
        assert result.table_name == "t", "uppercase key fallback should parse"
        assert result.create_statement == "CREATE TABLE t (id INT)", (
            "uppercase create statement should parse"
        )

    def test_parse_tables_single_column(self, introspector):
        """A one-column row (no FULL) parses name only."""
        result = SyncShowIntrospector._parse_tables([{"Tables_in_shop": "users"}])
        assert result[0].name == "users", "single-column row should parse the name"
        assert result[0].table_type is None, "table_type should be None without FULL"

    def test_parse_databases_null_name(self, introspector):
        """A missing Database key parses to name=None without raising."""
        result = SyncShowIntrospector._parse_databases([{}])
        assert result[0].name is None, "missing key should yield None name"

    def test_parse_variables_empty(self, introspector):
        """Empty rows parse to an empty list."""
        assert SyncShowIntrospector._parse_variables([]) == [], "no rows, no variables"