# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/introspection/test_show_introspector_offline.py
"""Database-free unit tests for MariaDB's SHOW sub-introspectors.

No MariaDB server, driver or connection is opened. The pure ``parse_*``
helpers on :class:`ShowMixin` are exercised directly, and the I/O-facing
public methods of both :class:`ShowIntrospector` and
:class:`AsyncShowIntrospector` are driven through a mocked
``IntrospectorExecutor`` / ``AsyncIntrospectorExecutor``.

MariaDB has a native asyncio driver, so the async class is real production
code: both the synchronous and the asynchronous class are covered
symmetrically here. A real :class:`MariaDBDialect` (which needs no connection)
is used so the SHOW expression objects render genuine SQL offline.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from rhosocial.activerecord.backend.expression.objects import Table, Trigger, View
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.show import (
    MariaDBShowColumnsStatement,
    MariaDBShowCreateTableStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.introspection.show_introspector import (
    AsyncShowIntrospector,
    ShowIntrospector,
    ShowMixin,
)
from rhosocial.activerecord.backend.impl.mariadb.show.types import (
    ShowCharsetResult,
    ShowCollationResult,
    ShowColumnResult,
    ShowCreateTableResult,
    ShowCreateTriggerResult,
    ShowCreateViewResult,
    ShowDatabaseResult,
    ShowEngineResult,
    ShowGrantResult,
    ShowIndexResult,
    ShowPluginResult,
    ShowProcessListResult,
    ShowStatusResult,
    ShowTableResult,
    ShowTableStatusResult,
    ShowTriggerResult,
    ShowVariableResult,
    ShowWarningResult,
)

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def backend():
    """A backend mock holding a real, connection-free MariaDB dialect."""
    backend = MagicMock()
    backend.dialect = MariaDBDialect(version=(11, 4, 0))
    return backend


@pytest.fixture
def executor():
    """A synchronous executor mock; ``execute`` returns no rows by default."""
    executor = MagicMock()
    executor.execute.return_value = []
    return executor


@pytest.fixture
def async_executor():
    """An async executor mock whose awaited ``execute`` returns no rows."""
    executor = AsyncMock()
    executor.execute.return_value = []
    return executor


@pytest.fixture
def introspector(backend, executor):
    return ShowIntrospector(backend, executor)


@pytest.fixture
def async_introspector(backend, async_executor):
    return AsyncShowIntrospector(backend, async_executor)


# --------------------------------------------------------------------------- #
# Shared assertion helpers
# --------------------------------------------------------------------------- #


def _assert_parse(result, rows, rtype, expected):
    """Check a parse helper returned *rtype* objects carrying *expected*."""
    if isinstance(result, list):
        assert len(result) == len(rows)
        assert all(isinstance(item, rtype) for item in result)
        subject = result[0] if result else None
    else:
        subject = result
    if subject is not None:
        assert isinstance(subject, rtype)
        for attr, value in expected.items():
            assert getattr(subject, attr) == value


# SHOW_CASES drive every public method on both introspectors. Each entry is
# (method_name, positional_args, mocked_rows, result_type, expected_fields).
SHOW_CASES = [
    pytest.param(
        "create_table",
        ("users",),
        [{"Table": "users", "Create Table": "CREATE TABLE `users` (`id` int)"}],
        ShowCreateTableResult,
        {"relation_name": "users", "create_statement": "CREATE TABLE `users` (`id` int)"},
        id="create_table",
    ),
    pytest.param(
        "create_view",
        ("v",),
        [
            {
                "View": "v",
                "Create View": "CREATE VIEW v AS SELECT 1",
                "character_set_client": "utf8mb4",
                "collation_connection": "utf8mb4_general_ci",
            }
        ],
        ShowCreateViewResult,
        {
            "relation_name": "v",
            "create_statement": "CREATE VIEW v AS SELECT 1",
            "character_set_client": "utf8mb4",
            "collation_connection": "utf8mb4_general_ci",
        },
        id="create_view",
    ),
    pytest.param(
        "columns",
        ("users",),
        [
            {
                "Field": "id",
                "Type": "int(11)",
                "Null": "NO",
                "Key": "PRI",
                "Default": None,
                "Extra": "auto_increment",
            }
        ],
        ShowColumnResult,
        {"field": "id", "type": "int(11)", "null": "NO", "key": "PRI", "extra": "auto_increment"},
        id="columns",
    ),
    pytest.param(
        "indexes",
        ("users",),
        [
            {
                "Table": "users",
                "Non_unique": 0,
                "Key_name": "PRIMARY",
                "Seq_in_index": 1,
                "Column_name": "id",
                "Collation": "A",
                "Cardinality": 5,
                "Index_type": "BTREE",
                "Visible": "YES",
            }
        ],
        ShowIndexResult,
        {
            "table": "users",
            "non_unique": 0,
            "key_name": "PRIMARY",
            "seq_in_index": 1,
            "column_name": "id",
            "index_type": "BTREE",
            "visible": "YES",
        },
        id="indexes",
    ),
    pytest.param(
        "tables",
        (),
        [{"Tables_in_app": "users", "Table_type": "BASE TABLE"}],
        ShowTableResult,
        {"name": "users", "table_type": "BASE TABLE"},
        id="tables",
    ),
    pytest.param(
        "databases",
        (),
        [{"Database": "app"}],
        ShowDatabaseResult,
        {"name": "app"},
        id="databases",
    ),
    pytest.param(
        "table_status",
        (),
        [
            {
                "Name": "users",
                "Engine": "InnoDB",
                "Version": 10,
                "Create_time": "2026-01-01 00:00:00",
                "Comment": "rows",
            }
        ],
        ShowTableStatusResult,
        {
            "name": "users",
            "engine": "InnoDB",
            "version": 10,
            "create_time": "2026-01-01 00:00:00",
            "comment": "rows",
        },
        id="table_status",
    ),
    pytest.param(
        "triggers",
        (),
        [
            {
                "Trigger": "bi_users",
                "Event": "INSERT",
                "Table": "users",
                "Statement": "SET NEW.x = 1",
                "Timing": "BEFORE",
                "Created": "2026-01-01",
                "Definer": "root@localhost",
            }
        ],
        ShowTriggerResult,
        {
            "trigger": "bi_users",
            "event": "INSERT",
            "table": "users",
            "statement": "SET NEW.x = 1",
            "timing": "BEFORE",
            "created": "2026-01-01",
        },
        id="triggers",
    ),
    pytest.param(
        "create_trigger",
        ("bi_users",),
        [
            {
                "Trigger": "bi_users",
                "SQL Original Statement": "CREATE TRIGGER bi_users ...",
                "character_set_client": "utf8mb4",
            }
        ],
        ShowCreateTriggerResult,
        {
            "trigger_name": "bi_users",
            "create_statement": "CREATE TRIGGER bi_users ...",
            "character_set_client": "utf8mb4",
        },
        id="create_trigger",
    ),
    pytest.param(
        "variables",
        (),
        [{"Variable_name": "max_connections", "Value": "151"}],
        ShowVariableResult,
        {"variable_name": "max_connections", "value": "151"},
        id="variables",
    ),
    pytest.param(
        "status",
        (),
        [{"Variable_name": "Threads_connected", "Value": "5"}],
        ShowStatusResult,
        {"variable_name": "Threads_connected", "value": "5"},
        id="status",
    ),
    pytest.param(
        "processlist",
        (),
        [
            {
                "Id": 1,
                "User": "root",
                "Host": "localhost",
                "Command": "Query",
                "Time": 0,
                "db": "app",
                "State": "init",
                "Info": "SHOW PROCESSLIST",
            }
        ],
        ShowProcessListResult,
        {"id": 1, "user": "root", "host": "localhost", "command": "Query", "db": "app"},
        id="processlist",
    ),
    pytest.param(
        "warnings",
        (),
        [{"Level": "Warning", "Code": 1234, "Message": "truncated"}],
        ShowWarningResult,
        {"level": "Warning", "code": 1234, "message": "truncated"},
        id="warnings",
    ),
    pytest.param(
        "errors",
        (),
        [{"Level": "Error", "Code": 1064, "Message": "syntax error"}],
        ShowWarningResult,
        {"level": "Error", "code": 1064, "message": "syntax error"},
        id="errors",
    ),
    pytest.param(
        "engines",
        (),
        [
            {
                "Engine": "InnoDB",
                "Support": "DEFAULT",
                "Transactions": "YES",
                "XA": "YES",
                "Savepoints": "YES",
            }
        ],
        ShowEngineResult,
        {"engine": "InnoDB", "support": "DEFAULT", "transactions": "YES", "savepoints": "YES"},
        id="engines",
    ),
    pytest.param(
        "charset",
        (),
        [
            {
                "Charset": "utf8mb4",
                "Description": "UTF-8 Unicode",
                "Default collation": "utf8mb4_general_ci",
                "Maxlen": 4,
            }
        ],
        ShowCharsetResult,
        {
            "charset": "utf8mb4",
            "description": "UTF-8 Unicode",
            "default_collation": "utf8mb4_general_ci",
            "maxlen": 4,
        },
        id="charset",
    ),
    pytest.param(
        "collation",
        (),
        [
            {
                "Collation": "utf8mb4_general_ci",
                "Charset": "utf8mb4",
                "Id": 45,
                "Default": "Yes",
                "Compiled": "Yes",
                "Sortlen": 1,
            }
        ],
        ShowCollationResult,
        {"collation": "utf8mb4_general_ci", "charset": "utf8mb4", "id": 45, "sortlen": 1},
        id="collation",
    ),
    pytest.param(
        "grants",
        (),
        [{"Grants for": "GRANT ALL ON *.* TO 'root'@'localhost'"}],
        ShowGrantResult,
        {"grants": "GRANT ALL ON *.* TO 'root'@'localhost'"},
        id="grants",
    ),
    pytest.param(
        "plugins",
        (),
        [
            {
                "Name": "InnoDB",
                "Status": "ACTIVE",
                "Type": "STORAGE ENGINE",
                "Library": None,
                "License": "GPL",
            }
        ],
        ShowPluginResult,
        {"name": "InnoDB", "status": "ACTIVE", "type": "STORAGE ENGINE", "license": "GPL"},
        id="plugins",
    ),
]

SINGLE_RESULT_METHODS = {"create_table", "create_view", "create_trigger"}


# --------------------------------------------------------------------------- #
# Pure parse helpers on the mixin
# --------------------------------------------------------------------------- #


class TestParseCreateHelpers:
    """The three single-row ``SHOW CREATE`` parsers."""

    @pytest.mark.parametrize(
        "rows, table_name, expected_name, expected_ddl",
        [
            ([{"Table": "users", "Create Table": "DDL"}], "ignored", "users", "DDL"),
            ([{"TABLE": "users", "CREATE TABLE": "DDL2"}], "ignored", "users", "DDL2"),
            ([{}], "fallback", "fallback", ""),
        ],
    )
    def test_parse_create_table(self, rows, table_name, expected_name, expected_ddl):
        result = ShowMixin.parse_create_table(rows, table_name)
        assert isinstance(result, ShowCreateTableResult)
        assert result.relation_name == expected_name
        assert result.create_statement == expected_ddl
        assert result.object_name == expected_name
        assert result.table_name == expected_name

    @pytest.mark.parametrize("rows", [[], ()])
    def test_parse_create_table_empty(self, rows):
        assert ShowMixin.parse_create_table(rows, "users") is None

    def test_parse_create_view_with_optional_fields(self):
        rows = [
            {
                "View": "v",
                "Create View": "DDL",
                "character_set_client": "utf8mb4",
                "collation_connection": "utf8mb4_bin",
            }
        ]
        result = ShowMixin.parse_create_view(rows, "ignored")
        assert isinstance(result, ShowCreateViewResult)
        assert result.relation_name == "v"
        assert result.view_name == "v"
        assert result.create_statement == "DDL"
        assert result.character_set_client == "utf8mb4"
        assert result.collation_connection == "utf8mb4_bin"

    def test_parse_create_view_optional_defaults(self):
        result = ShowMixin.parse_create_view([{"View": "v", "Create View": "DDL"}], "v")
        assert result.character_set_client is None
        assert result.collation_connection is None

    def test_parse_create_view_uppercase_and_empty(self):
        result = ShowMixin.parse_create_view([{"VIEW": "v", "CREATE VIEW": "DDL"}], "v")
        assert result.relation_name == "v"
        assert result.create_statement == "DDL"
        assert ShowMixin.parse_create_view([], "v") is None

    def test_parse_create_trigger_with_optional_fields(self):
        rows = [
            {
                "Trigger": "tr",
                "SQL Original Statement": "CREATE TRIGGER tr ...",
                "character_set_client": "utf8mb4",
                "collation_connection": "utf8mb4_bin",
                "Database Collation": "utf8mb4_general_ci",
            }
        ]
        result = ShowMixin.parse_create_trigger(rows, "ignored")
        assert isinstance(result, ShowCreateTriggerResult)
        assert result.trigger_name == "tr"
        assert result.create_statement == "CREATE TRIGGER tr ..."
        assert result.character_set_client == "utf8mb4"
        assert result.database_collation == "utf8mb4_general_ci"

    def test_parse_create_trigger_fallback_and_empty(self):
        result = ShowMixin.parse_create_trigger([{"TRIGGER": "tr", "CREATE TRIGGER": "DDL"}], "tr")
        assert result.trigger_name == "tr"
        assert result.create_statement == "DDL"
        assert result.character_set_client is None
        assert ShowMixin.parse_create_trigger([], "tr") is None


class TestParseRelationHelpers:
    """Parsers whose rows map onto one relation."""

    def test_parse_columns_short_form(self):
        row = {
            "Field": "id",
            "Type": "int(11)",
            "Null": "NO",
            "Key": "PRI",
            "Default": None,
            "Extra": "auto_increment",
        }
        result = ShowMixin.parse_columns([row])
        assert result == [
            ShowColumnResult(
                field="id",
                type="int(11)",
                null="NO",
                key="PRI",
                default=None,
                extra="auto_increment",
            )
        ]

    def test_parse_columns_full_form_sets_privileges_and_comment(self):
        row = {
            "Field": "name",
            "Type": "varchar(50)",
            "Null": "YES",
            "Collation": "utf8mb4_bin",
            "Privileges": "select,insert",
            "Comment": "a name",
            "Extra": "",
        }
        result = ShowMixin.parse_columns([row])[0]
        assert result.privileges == "select,insert"
        assert result.comment == "a name"

    def test_parse_columns_information_schema_keys(self):
        row = {
            "COLUMN_NAME": "id",
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_KEY": "PRI",
            "COLUMN_DEFAULT": "0",
            "EXTRA": "auto_increment",
        }
        result = ShowMixin.parse_columns([row])[0]
        assert result.field == "id"
        assert result.type == "bigint"
        assert result.null == "NO"
        assert result.key == "PRI"
        assert result.default == "0"

    def test_parse_columns_empty(self):
        assert ShowMixin.parse_columns([]) == []

    def test_parse_indexes_short_form(self):
        row = {
            "Table": "users",
            "Non_unique": 0,
            "Key_name": "PRIMARY",
            "Seq_in_index": 1,
            "Column_name": "id",
            "Index_type": "HASH",
            "Visible": "YES",
        }
        result = ShowMixin.parse_indexes([row])[0]
        assert isinstance(result, ShowIndexResult)
        assert result.table == "users"
        assert result.non_unique == 0
        assert result.key_name == "PRIMARY"
        assert result.seq_in_index == 1
        assert result.index_type == "HASH"
        assert result.visible == "YES"

    def test_parse_indexes_defaults_index_type(self):
        row = {"Table": "t", "Key_name": "idx", "Column_name": "c"}
        result = ShowMixin.parse_indexes([row])[0]
        assert result.index_type == "BTREE"
        assert result.collation is None
        assert result.cardinality is None

    def test_parse_indexes_information_schema_keys(self):
        row = {
            "TABLE_NAME": "t",
            "NON_UNIQUE": 1,
            "INDEX_NAME": "idx",
            "SEQ_IN_INDEX": 2,
            "COLUMN_NAME": "c",
            "INDEX_TYPE": "BTREE",
            "IS_VISIBLE": "YES",
        }
        result = ShowMixin.parse_indexes([row])[0]
        assert result.table == "t"
        assert result.non_unique == 1
        assert result.key_name == "idx"
        assert result.seq_in_index == 2
        assert result.visible == "YES"

    def test_parse_indexes_empty(self):
        assert ShowMixin.parse_indexes([]) == []

    def test_parse_tables_single_column_rows(self):
        assert ShowMixin.parse_tables([{"Tables_in_app": "users"}]) == [
            ShowTableResult(name="users", table_type=None),
        ]

    def test_parse_tables_qualified_rows(self):
        rows = [
            {"Tables_in_app": "users", "Table_type": "BASE TABLE"},
            {"Tables_in_app": "v", "Table_type": "VIEW"},
        ]
        assert ShowMixin.parse_tables(rows) == [
            ShowTableResult(name="users", table_type="BASE TABLE"),
            ShowTableResult(name="v", table_type="VIEW"),
        ]

    def test_parse_tables_single_column_uses_sole_value(self):
        # Any one-column row is treated as a bare table name, whatever its key.
        assert ShowMixin.parse_tables([{"Other": "x"}]) == [ShowTableResult(name="x")]

    def test_parse_tables_ignores_multi_column_rows_without_name_key(self):
        assert ShowMixin.parse_tables([{"Foo": "x", "Bar": "y"}]) == []
        assert ShowMixin.parse_tables([]) == []

    def test_parse_table_status_stringifies_times(self):
        stamp = datetime(2026, 1, 2, 3, 4, 5)
        row = {"Name": "t", "Create_time": stamp, "Update_time": None, "Check_time": stamp}
        result = ShowMixin.parse_table_status([row])[0]
        assert result.name == "t"
        assert result.create_time == str(stamp)
        assert result.update_time is None
        assert result.check_time == str(stamp)

    def test_parse_table_status_empty(self):
        assert ShowMixin.parse_table_status([]) == []

    def test_parse_triggers_short_form(self):
        row = {
            "Trigger": "tr",
            "Event": "INSERT",
            "Table": "users",
            "Statement": "BEGIN END",
            "Timing": "BEFORE",
            "Created": "2026-01-01",
            "sql_mode": "STRICT",
            "definer": "root@%",
            "Database Collation": "utf8mb4_general_ci",
        }
        result = ShowMixin.parse_triggers([row])[0]
        assert isinstance(result, ShowTriggerResult)
        assert result.trigger == "tr"
        assert result.event == "INSERT"
        assert result.table == "users"
        assert result.statement == "BEGIN END"
        assert result.timing == "BEFORE"
        assert result.sql_mode == "STRICT"
        assert result.database_collation == "utf8mb4_general_ci"

    def test_parse_triggers_information_schema_keys(self):
        row = {
            "TRIGGER_NAME": "tr",
            "EVENT_MANIPULATION": "UPDATE",
            "EVENT_OBJECT_TABLE": "users",
            "ACTION_STATEMENT": "SET 1",
            "ACTION_TIMING": "AFTER",
        }
        result = ShowMixin.parse_triggers([row])[0]
        assert result.trigger == "tr"
        assert result.event == "UPDATE"
        assert result.table == "users"
        assert result.statement == "SET 1"
        assert result.timing == "AFTER"

    def test_parse_triggers_empty(self):
        assert ShowMixin.parse_triggers([]) == []


# Row-shape cases for the simple list-returning parsers.
MISC_PARSE_CASES = [
    pytest.param(
        "parse_databases",
        [{"Database": "app"}, {"Database": "sys"}],
        ShowDatabaseResult,
        [{"name": "app"}, {"name": "sys"}],
        id="databases",
    ),
    pytest.param(
        "parse_variables",
        [{"Variable_name": "a", "Value": "1"}],
        ShowVariableResult,
        [{"variable_name": "a", "value": "1"}],
        id="variables",
    ),
    pytest.param(
        "parse_status",
        [{"Variable_name": "Threads", "Value": "2"}],
        ShowStatusResult,
        [{"variable_name": "Threads", "value": "2"}],
        id="status",
    ),
    pytest.param(
        "parse_processlist",
        [{"ID": 7, "User": "app", "Host": "h", "Command": "Sleep", "Time": 3}],
        ShowProcessListResult,
        [{"id": 7, "user": "app", "host": "h", "command": "Sleep", "time": 3}],
        id="processlist",
    ),
    pytest.param(
        "parse_warnings",
        [{"Level": "Warning", "Code": 1, "Message": "m"}],
        ShowWarningResult,
        [{"level": "Warning", "code": 1, "message": "m"}],
        id="warnings",
    ),
    pytest.param(
        "parse_engines",
        [{"Engine": "InnoDB", "Support": "DEFAULT", "XA": "YES"}],
        ShowEngineResult,
        [{"engine": "InnoDB", "support": "DEFAULT", "xa": "YES"}],
        id="engines",
    ),
    pytest.param(
        "parse_charset",
        [
            {
                "Charset": "utf8mb4",
                "Description": "UTF-8",
                "Default collation": "utf8mb4_bin",
                "Maxlen": 4,
            }
        ],
        ShowCharsetResult,
        [
            {
                "charset": "utf8mb4",
                "description": "UTF-8",
                "default_collation": "utf8mb4_bin",
                "maxlen": 4,
            }
        ],
        id="charset",
    ),
    pytest.param(
        "parse_collation",
        [{"Collation": "utf8mb4_bin", "Charset": "utf8mb4", "Id": 46, "Default": ""}],
        ShowCollationResult,
        [{"collation": "utf8mb4_bin", "charset": "utf8mb4", "id": 46, "default": ""}],
        id="collation",
    ),
    pytest.param(
        "parse_grants",
        [{"Grants for": "GRANT ALL ON *.* TO 'r'@'h'"}],
        ShowGrantResult,
        [{"grants": "GRANT ALL ON *.* TO 'r'@'h'"}],
        id="grants",
    ),
    pytest.param(
        "parse_plugins",
        [{"Name": "p", "Status": "ACTIVE", "Type": "AUTHENTICATION"}],
        ShowPluginResult,
        [{"name": "p", "status": "ACTIVE", "type": "AUTHENTICATION"}],
        id="plugins",
    ),
]


class TestParseMiscHelpers:
    """The remaining list-returning parsers, happy path and empty input."""

    @pytest.mark.parametrize("helper, rows, rtype, fields", MISC_PARSE_CASES)
    def test_parse_rows(self, helper, rows, rtype, fields):
        result = getattr(ShowMixin, helper)(rows)
        assert len(result) == len(rows)
        for item, expected in zip(result, fields):
            assert isinstance(item, rtype)
            for attr, value in expected.items():
                assert getattr(item, attr) == value

    @pytest.mark.parametrize(
        "helper",
        [case.values[0] for case in MISC_PARSE_CASES],
    )
    def test_parse_empty(self, helper):
        assert getattr(ShowMixin, helper)([]) == []


# --------------------------------------------------------------------------- #
# Shared SQL-generation helpers on the mixin
# --------------------------------------------------------------------------- #


class TestShowMixinHelpers:
    """``dialect``, ``_target`` and ``_show_relation`` use the backend dialect."""

    def test_dialect_property(self, introspector, backend):
        assert introspector.dialect is backend.dialect

    def test_target_without_schema(self, introspector):
        target = introspector._target(Table, "users", None)
        assert isinstance(target, Table)
        assert target.name == "users"
        assert target.catalog_name is None

    def test_target_with_schema(self, introspector):
        target = introspector._target(Table, "users", "app")
        assert isinstance(target, Table)
        assert target.catalog_name == "app"

    def test_target_honours_object_kind(self, introspector):
        assert isinstance(introspector._target(View, "v", None), View)
        assert isinstance(introspector._target(Trigger, "tr", None), Trigger)

    def test_show_relation_without_schema(self, introspector):
        expr = introspector._show_relation(MariaDBShowCreateTableStatement, "users", None)
        assert isinstance(expr, MariaDBShowCreateTableStatement)
        assert expr.relation.name == "users"
        assert expr.relation.catalog_name is None
        assert expr.to_sql()[0] == "SHOW CREATE TABLE `users`"

    def test_show_relation_with_schema_and_options(self, introspector):
        expr = introspector._show_relation(
            MariaDBShowColumnsStatement, "users", "app", full=True, like_pattern="i%"
        )
        assert expr.relation.catalog_name == "app"
        assert expr.full is True
        assert expr.like_pattern == "i%"
        sql, params = expr.to_sql()
        assert "COLUMNS" in sql
        assert params == ("i%",)


# --------------------------------------------------------------------------- #
# Public methods on the synchronous introspector
# --------------------------------------------------------------------------- #


class TestShowIntrospectorSync:
    """Every sync public method renders SQL and maps mocked rows."""

    @pytest.mark.parametrize("method, args, rows, rtype, expected", SHOW_CASES)
    def test_public_method_maps_rows(
        self, introspector, executor, method, args, rows, rtype, expected
    ):
        executor.execute.return_value = rows
        result = getattr(introspector, method)(*args)

        _assert_parse(result, rows, rtype, expected)
        executor.execute.assert_called_once()
        sql = executor.execute.call_args.args[0]
        assert isinstance(sql, str)
        assert sql.startswith("SHOW")

    @pytest.mark.parametrize("method", sorted(SINGLE_RESULT_METHODS))
    @pytest.mark.parametrize("args", [("thing",)])
    def test_single_result_method_empty_rows_returns_none(
        self, introspector, executor, method, args
    ):
        executor.execute.return_value = []
        assert getattr(introspector, method)(*args) is None

    def test_exec_delegates_to_executor(self, introspector, executor):
        executor.execute.return_value = [{"ok": 1}]
        assert introspector._exec("SHOW ENGINES", ()) == [{"ok": 1}]
        executor.execute.assert_called_once_with("SHOW ENGINES", ())

    def test_options_flow_into_sql(self, introspector, executor):
        executor.execute.return_value = []
        introspector.variables(like="max_%", session=False)
        sql = executor.execute.call_args.args[0]
        assert "GLOBAL VARIABLES" in sql

    def test_schema_flows_into_relation_sql(self, introspector, executor):
        executor.execute.return_value = []
        introspector.create_table("users", schema="app")
        sql = executor.execute.call_args.args[0]
        assert "app" in sql
        assert "users" in sql


# --------------------------------------------------------------------------- #
# Public methods on the native-async introspector
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
class TestAsyncShowIntrospector:
    """Every async public method awaits the executor and maps mocked rows."""

    @pytest.mark.parametrize("method, args, rows, rtype, expected", SHOW_CASES)
    async def test_public_method_maps_rows(
        self, async_introspector, async_executor, method, args, rows, rtype, expected
    ):
        async_executor.execute.return_value = rows
        result = await getattr(async_introspector, method)(*args)

        _assert_parse(result, rows, rtype, expected)
        async_executor.execute.assert_awaited_once()
        sql = async_executor.execute.call_args.args[0]
        assert isinstance(sql, str)
        assert sql.startswith("SHOW")

    @pytest.mark.parametrize("method", sorted(SINGLE_RESULT_METHODS))
    async def test_single_result_method_empty_rows_returns_none(
        self, async_introspector, async_executor, method
    ):
        async_executor.execute.return_value = []
        assert await getattr(async_introspector, method)("thing") is None

    async def test_exec_awaits_executor(self, async_introspector, async_executor):
        async_executor.execute.return_value = [{"ok": 1}]
        assert await async_introspector._exec("SHOW ENGINES", ()) == [{"ok": 1}]
        async_executor.execute.assert_awaited_once_with("SHOW ENGINES", ())

    async def test_options_flow_into_sql(self, async_introspector, async_executor):
        async_executor.execute.return_value = []
        await async_introspector.processlist(full=True)
        sql = async_executor.execute.call_args.args[0]
        assert "FULL PROCESSLIST" in sql

    async def test_schema_flows_into_relation_sql(self, async_introspector, async_executor):
        async_executor.execute.return_value = []
        await async_introspector.columns("users", schema="app", full=True, like="i%")
        sql = async_executor.execute.call_args.args[0]
        assert "app" in sql
        assert "users" in sql
