# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/show/test_mariadb_show_functionality_offline.py
"""Database-free unit tests for MariaDB's SHOW functionality.

These tests never open a MariaDB connection. Both the synchronous
:class:`MariaDBShowFunctionality` and its native-async twin
:class:`AsyncMariaDBShowFunctionality` are driven through mocked backends:
the real :class:`MariaDBDialect` renders SQL without a server, ``backend.execute``
is a :class:`~unittest.mock.MagicMock` / :class:`~unittest.mock.AsyncMock`
returning controlled rows, and the parsers map those rows into the typed
dataclasses from ``show/types.py``.

MariaDB has a real asyncio driver, so the async class is production code, not a
pseudo-async wrapper: every awaited ``execute`` call is exercised here too.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.show.functionality import (
    AsyncMariaDBShowFunctionality,
    MariaDBShowFunctionality,
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


def _rows_result(rows):
    """A tiny stand-in for the backend's query result object."""
    return SimpleNamespace(data=rows)


def _sql(backend):
    """The SQL string handed to ``backend.execute``."""
    return backend.execute.call_args.args[0]


def _params(backend):
    """The parameter tuple handed to ``backend.execute``."""
    return backend.execute.call_args.args[1]


@pytest.fixture
def backend():
    """A mock backend with a real, versioned MariaDB dialect (no connection)."""
    be = MagicMock()
    be.dialect = MariaDBDialect(version=(11, 4, 0))
    return be


@pytest.fixture
def show(backend):
    return MariaDBShowFunctionality(backend, version=(11, 4, 0))


@pytest.fixture
def async_backend():
    """A mock backend whose ``execute`` is awaited (native async driver)."""
    be = MagicMock()
    be.dialect = MariaDBDialect(version=(11, 4, 0))
    be.execute = AsyncMock()
    return be


@pytest.fixture
def async_show(async_backend):
    return AsyncMariaDBShowFunctionality(async_backend, version=(11, 4, 0))


class TestInitialization:
    """Construction stores the version and reuses the backend's dialect."""

    def test_sync_init(self, backend, show):
        assert show._backend is backend
        assert show._version == (11, 4, 0)
        assert show.dialect is backend.dialect

    def test_sync_init_without_version(self, backend):
        func = MariaDBShowFunctionality(backend)
        assert func._version is None
        assert func.dialect is backend.dialect

    def test_async_init(self, async_backend, async_show):
        assert async_show._backend is async_backend
        assert async_show._version == (11, 4, 0)
        assert async_show.dialect is async_backend.dialect
        assert isinstance(async_show._sync_impl, MariaDBShowFunctionality)

    def test_async_publish_methods(self, async_show, show):
        """Async mirrors the sync public surface."""
        sync_names = {n for n in dir(show) if not n.startswith("_")}
        async_names = {n for n in dir(async_show) if not n.startswith("_")}
        assert sync_names == async_names


class TestSyncShowFunctionality:
    """Every public method on MariaDBShowFunctionality maps rows to types."""

    def test_create_table(self, backend, show):
        backend.execute.return_value = _rows_result(
            [{"Table": "users", "Create Table": "CREATE TABLE `users` (`id` INT)"}]
        )
        result = show.create_table("users", schema="app")

        assert isinstance(result, ShowCreateTableResult)
        assert result.relation_name == "users"
        assert result.table_name == "users"
        assert result.object_name == "users"
        assert result.create_statement == "CREATE TABLE `users` (`id` INT)"
        backend.execute.assert_called_once()
        assert "`app`.`users`" in _sql(backend)

    def test_create_table_alternate_keys_and_fallback(self, backend, show):
        backend.execute.return_value = _rows_result(
            [{"TABLE": "orders", "CREATE TABLE": "CREATE TABLE `orders`"}]
        )
        result = show.create_table("orders")
        assert result.relation_name == "orders"
        assert result.create_statement == "CREATE TABLE `orders`"

    def test_create_table_missing_fields_fall_back_to_argument(self, backend, show):
        backend.execute.return_value = _rows_result([{}])
        result = show.create_table("widgets")
        assert result.relation_name == "widgets"
        assert result.create_statement == ""

    def test_create_view(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "View": "active_users",
                    "Create View": "CREATE VIEW `active_users` AS SELECT 1",
                    "character_set_client": "utf8mb4",
                    "collation_connection": "utf8mb4_general_ci",
                }
            ]
        )
        result = show.create_view("active_users")

        assert isinstance(result, ShowCreateViewResult)
        assert result.view_name == "active_users"
        assert result.create_statement.startswith("CREATE VIEW")
        assert result.character_set_client == "utf8mb4"
        assert result.collation_connection == "utf8mb4_general_ci"

    def test_columns(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Field": "id",
                    "Type": "int(11)",
                    "Null": "NO",
                    "Key": "PRI",
                    "Default": None,
                    "Extra": "auto_increment",
                }
            ]
        )
        columns = show.columns("users", schema="app")

        assert len(columns) == 1
        assert isinstance(columns[0], ShowColumnResult)
        col = columns[0]
        assert (col.field, col.type, col.null, col.key) == ("id", "int(11)", "NO", "PRI")
        assert col.default is None
        assert col.extra == "auto_increment"
        assert col.privileges is None
        assert col.comment is None
        assert "`app`.`users`" in _sql(backend)

    def test_columns_full_mode_and_privileges(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Field": "name",
                    "Type": "varchar(255)",
                    "Null": "YES",
                    "Collation": "utf8mb4_general_ci",
                    "Privileges": "select,insert",
                    "Comment": "display name",
                    "Extra": "",
                }
            ]
        )
        col = show.columns("users", full=True, like="name%")[0]
        assert col.privileges == "select,insert"
        assert col.comment == "display name"
        assert "FULL COLUMNS" in _sql(backend)
        assert "LIKE" in _sql(backend)
        assert _params(backend) == ("name%",)

    def test_columns_information_schema_keys(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "COLUMN_NAME": "id",
                    "COLUMN_TYPE": "bigint",
                    "IS_NULLABLE": "NO",
                    "COLUMN_KEY": "PRI",
                    "COLUMN_DEFAULT": "0",
                    "EXTRA": "",
                }
            ]
        )
        col = show.columns("users")[0]
        assert (col.field, col.type, col.null, col.key, col.default) == (
            "id",
            "bigint",
            "NO",
            "PRI",
            "0",
        )

    def test_indexes(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Table": "users",
                    "Non_unique": 0,
                    "Key_name": "PRIMARY",
                    "Seq_in_index": 1,
                    "Column_name": "id",
                    "Collation": "A",
                    "Cardinality": 100,
                    "Sub_part": None,
                    "Packed": None,
                    "Null": "",
                    "Index_type": "BTREE",
                    "Comment": "",
                    "Index_comment": "primary key",
                    "Visible": "YES",
                    "Expression": None,
                },
                {
                    "Table": "users",
                    "Non_unique": 1,
                    "Key_name": "idx_email",
                    "Seq_in_index": 1,
                    "Column_name": "email",
                },
            ]
        )
        indexes = show.indexes("users", schema="app")

        assert len(indexes) == 2
        assert all(isinstance(idx, ShowIndexResult) for idx in indexes)
        first = indexes[0]
        assert (first.table, first.key_name, first.column_name) == ("users", "PRIMARY", "id")
        assert (first.non_unique, first.seq_in_index, first.cardinality) == (0, 1, 100)
        assert first.index_type == "BTREE"
        assert first.index_comment == "primary key"
        assert first.visible == "YES"
        assert indexes[1].index_type == "BTREE"  # default when key absent

    def test_indexes_information_schema_keys(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "TABLE_NAME": "orders",
                    "NON_UNIQUE": 1,
                    "INDEX_NAME": "idx_total",
                    "SEQ_IN_INDEX": 2,
                    "COLUMN_NAME": "total",
                    "INDEX_TYPE": "HASH",
                    "INDEX_COMMENT": "from info schema",
                }
            ]
        )
        idx = show.indexes("orders")[0]
        assert (idx.table, idx.key_name, idx.column_name) == ("orders", "idx_total", "total")
        assert (idx.non_unique, idx.seq_in_index) == (1, 2)
        assert idx.index_type == "HASH"
        assert idx.comment == "from info schema"

    def test_tables_single_column(self, backend, show):
        backend.execute.return_value = _rows_result(
            [{"Tables_in_app": "users"}, {"Tables_in_app": "orders"}]
        )
        tables = show.tables(schema="app")

        assert len(tables) == 2
        assert all(isinstance(t, ShowTableResult) for t in tables)
        assert [t.name for t in tables] == ["users", "orders"]
        assert all(t.table_type is None for t in tables)

    def test_tables_full_with_table_type(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {"Tables_in_app": "users", "Table_type": "BASE TABLE"},
                {"Tables_in_app": "active_users", "Table_type": "VIEW"},
                {"Other": "ignored", "Table_type": "BASE TABLE"},
            ]
        )
        tables = show.tables(schema="app", like="%", full=True)

        assert [(t.name, t.table_type) for t in tables] == [
            ("users", "BASE TABLE"),
            ("active_users", "VIEW"),
        ]
        assert "FULL TABLES" in _sql(backend)
        assert "FROM `app`" in _sql(backend)

    def test_databases(self, backend, show):
        backend.execute.return_value = _rows_result(
            [{"Database": "information_schema"}, {"Database": "app"}]
        )
        databases = show.databases(like="a%")

        assert len(databases) == 2
        assert all(isinstance(d, ShowDatabaseResult) for d in databases)
        assert [d.name for d in databases] == ["information_schema", "app"]
        assert _params(backend) == ("a%",)

    def test_table_status(self, backend, show):
        created = datetime(2026, 1, 2, 3, 4, 5)
        backend.execute.return_value = _rows_result(
            [
                {
                    "Name": "users",
                    "Engine": "InnoDB",
                    "Version": 10,
                    "Row_format": "Dynamic",
                    "Rows": 42,
                    "Avg_row_length": 100,
                    "Data_length": 4200,
                    "Max_data_length": 0,
                    "Index_length": 1024,
                    "Data_free": 0,
                    "Auto_increment": 43,
                    "Create_time": created,
                    "Update_time": None,
                    "Check_time": None,
                    "Collation": "utf8mb4_general_ci",
                    "Checksum": None,
                    "Create_options": "",
                    "Comment": "user records",
                }
            ]
        )
        statuses = show.table_status(schema="app", like="u%")

        assert len(statuses) == 1
        assert isinstance(statuses[0], ShowTableStatusResult)
        st = statuses[0]
        assert (st.name, st.engine, st.row_format) == ("users", "InnoDB", "Dynamic")
        assert (st.rows, st.data_length, st.index_length) == (42, 4200, 1024)
        assert st.create_time == str(created)
        assert st.update_time is None
        assert st.comment == "user records"
        assert "FROM `app`" in _sql(backend)

    def test_triggers(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Trigger": "users_before_insert",
                    "Event": "INSERT",
                    "Table": "users",
                    "Statement": "BEGIN SET NEW.x = 1; END",
                    "Timing": "BEFORE",
                    "Created": "2026-01-01 00:00:00",
                    "sql_mode": "STRICT_TRANS_TABLES",
                    "Definer": "root@localhost",
                    "character_set_client": "utf8mb4",
                    "collation_connection": "utf8mb4_general_ci",
                    "Database Collation": "utf8mb4_general_ci",
                }
            ]
        )
        triggers = show.triggers(schema="app", table_name="users")

        assert len(triggers) == 1
        assert isinstance(triggers[0], ShowTriggerResult)
        trg = triggers[0]
        assert (trg.trigger, trg.event, trg.table, trg.timing) == (
            "users_before_insert",
            "INSERT",
            "users",
            "BEFORE",
        )
        assert trg.statement.startswith("BEGIN")
        assert trg.definer == "root@localhost"
        assert trg.database_collation == "utf8mb4_general_ci"
        assert "LIKE" in _sql(backend)
        assert _params(backend) == ("users",)

    def test_create_trigger(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Trigger": "trg",
                    "SQL Original Statement": "CREATE TRIGGER trg ...",
                    "character_set_client": "utf8mb4",
                    "collation_connection": "utf8mb4_general_ci",
                    "Database Collation": "utf8mb4_general_ci",
                }
            ]
        )
        result = show.create_trigger("trg", schema="app")

        assert isinstance(result, ShowCreateTriggerResult)
        assert result.trigger_name == "trg"
        assert result.create_statement == "CREATE TRIGGER trg ..."
        assert result.character_set_client == "utf8mb4"
        assert result.database_collation == "utf8mb4_general_ci"
        assert "`app`.`trg`" in _sql(backend)

    def test_create_trigger_alternate_keys(self, backend, show):
        backend.execute.return_value = _rows_result(
            [{"TRIGGER": "trg2", "CREATE TRIGGER": "CREATE TRIGGER trg2 ..."}]
        )
        result = show.create_trigger("fallback")
        assert result.trigger_name == "trg2"
        assert result.create_statement == "CREATE TRIGGER trg2 ..."

    @pytest.mark.parametrize("session", [True, False])
    def test_variables(self, backend, show, session):
        backend.execute.return_value = _rows_result(
            [{"Variable_name": "max_connections", "Value": "151"}]
        )
        variables = show.variables(like="max%", session=session)

        assert len(variables) == 1
        assert isinstance(variables[0], ShowVariableResult)
        assert variables[0].variable_name == "max_connections"
        assert variables[0].value == "151"
        assert _params(backend) == ("max%",)
        assert ("GLOBAL" in _sql(backend)) is (session is False)

    @pytest.mark.parametrize("session", [True, False])
    def test_status(self, backend, show, session):
        backend.execute.return_value = _rows_result(
            [{"Variable_name": "Threads_connected", "Value": "5"}]
        )
        statuses = show.status(session=session)

        assert len(statuses) == 1
        assert isinstance(statuses[0], ShowStatusResult)
        assert statuses[0].variable_name == "Threads_connected"
        assert statuses[0].value == "5"
        assert ("GLOBAL" in _sql(backend)) is (session is False)

    def test_processlist(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Id": 7,
                    "User": "root",
                    "Host": "localhost:1234",
                    "Command": "Query",
                    "Time": 0,
                    "db": "app",
                    "State": " executing ",
                    "Info": "SELECT 1",
                },
                {"ID": 8, "User": "app", "Host": "%", "Command": "Sleep", "Time": 10},
            ]
        )
        processes = show.processlist(full=True)

        assert len(processes) == 2
        assert all(isinstance(p, ShowProcessListResult) for p in processes)
        assert (processes[0].id, processes[0].user, processes[0].db) == (7, "root", "app")
        assert processes[0].info == "SELECT 1"
        assert processes[1].id == 8
        assert "FULL PROCESSLIST" in _sql(backend)

    def test_warnings_with_limit(self, backend, show):
        backend.execute.return_value = _rows_result(
            [{"Level": "Warning", "Code": 1265, "Message": "data truncated"}]
        )
        warnings = show.warnings(limit=5)

        assert len(warnings) == 1
        assert isinstance(warnings[0], ShowWarningResult)
        assert (warnings[0].level, warnings[0].code, warnings[0].message) == (
            "Warning",
            1265,
            "data truncated",
        )
        assert "LIMIT 5" in _sql(backend)

    def test_errors_with_limit(self, backend, show):
        backend.execute.return_value = _rows_result(
            [{"Level": "Error", "Code": 1064, "Message": "syntax error"}]
        )
        errors = show.errors(limit=3)

        assert len(errors) == 1
        assert isinstance(errors[0], ShowWarningResult)
        assert (errors[0].level, errors[0].code) == ("Error", 1064)
        assert "LIMIT 3" in _sql(backend)

    def test_engines(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Engine": "InnoDB",
                    "Support": "DEFAULT",
                    "Transactions": "YES",
                    "XA": "YES",
                    "Savepoints": "YES",
                },
                {"Engine": "MyISAM", "Support": "YES"},
            ]
        )
        engines = show.engines()

        assert len(engines) == 2
        assert all(isinstance(e, ShowEngineResult) for e in engines)
        assert (engines[0].engine, engines[0].support) == ("InnoDB", "DEFAULT")
        assert engines[0].savepoints == "YES"
        assert engines[1].transactions is None

    def test_charset(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Charset": "utf8mb4",
                    "Description": "UTF-8 Unicode",
                    "Default collation": "utf8mb4_general_ci",
                    "Maxlen": 4,
                }
            ]
        )
        charsets = show.charset(like="utf8%")

        assert len(charsets) == 1
        assert isinstance(charsets[0], ShowCharsetResult)
        assert (charsets[0].charset, charsets[0].maxlen) == ("utf8mb4", 4)
        assert charsets[0].default_collation == "utf8mb4_general_ci"
        assert _params(backend) == ("utf8%",)

    def test_collation(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Collation": "utf8mb4_general_ci",
                    "Charset": "utf8mb4",
                    "Id": 45,
                    "Default": "Yes",
                    "Compiled": "Yes",
                    "Sortlen": 1,
                }
            ]
        )
        collations = show.collation()

        assert len(collations) == 1
        assert isinstance(collations[0], ShowCollationResult)
        assert (collations[0].collation, collations[0].charset, collations[0].id) == (
            "utf8mb4_general_ci",
            "utf8mb4",
            45,
        )
        assert collations[0].sortlen == 1

    def test_grants(self, backend, show):
        backend.execute.return_value = _rows_result(
            [{"Grants for": "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost'"}]
        )
        grants = show.grants(user="root", host="localhost")

        assert len(grants) == 1
        assert isinstance(grants[0], ShowGrantResult)
        assert grants[0].grants.startswith("GRANT ALL")
        assert _params(backend) == ("root", "localhost")

    def test_plugins(self, backend, show):
        backend.execute.return_value = _rows_result(
            [
                {
                    "Name": "InnoDB",
                    "Status": "ACTIVE",
                    "Type": "STORAGE ENGINE",
                    "Library": None,
                    "License": "GPL",
                }
            ]
        )
        plugins = show.plugins()

        assert len(plugins) == 1
        assert isinstance(plugins[0], ShowPluginResult)
        assert (plugins[0].name, plugins[0].status, plugins[0].type) == (
            "InnoDB",
            "ACTIVE",
            "STORAGE ENGINE",
        )
        assert plugins[0].license == "GPL"


class TestSyncEmptyResults:
    """Empty result sets map to empty lists or ``None`` for single-row reads."""

    @pytest.mark.parametrize(
        "method, args",
        [
            ("columns", ("users",)),
            ("indexes", ("users",)),
            ("tables", ()),
            ("databases", ()),
            ("table_status", ()),
            ("triggers", ()),
            ("variables", ()),
            ("status", ()),
            ("processlist", ()),
            ("warnings", ()),
            ("errors", ()),
            ("engines", ()),
            ("charset", ()),
            ("collation", ()),
            ("grants", ()),
            ("plugins", ()),
        ],
    )
    def test_list_methods_return_empty_list(self, backend, show, method, args):
        backend.execute.return_value = _rows_result([])
        assert getattr(show, method)(*args) == []
        backend.execute.assert_called_once()

    @pytest.mark.parametrize(
        "method, args",
        [("create_table", ("users",)), ("create_view", ("v",)), ("create_trigger", ("t",))],
    )
    def test_single_row_methods_return_none(self, backend, show, method, args):
        backend.execute.return_value = _rows_result([])
        assert getattr(show, method)(*args) is None
        backend.execute.assert_called_once()


class TestAsyncShowFunctionality:
    """Every public async method awaits ``execute`` and maps rows identically."""

    async def test_create_table(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [{"Table": "users", "Create Table": "CREATE TABLE `users`"}]
        )
        result = await async_show.create_table("users", schema="app")

        assert isinstance(result, ShowCreateTableResult)
        assert (result.table_name, result.create_statement) == ("users", "CREATE TABLE `users`")
        async_backend.execute.assert_awaited_once()
        assert "`app`.`users`" in _sql(async_backend)

    async def test_create_view(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [
                {
                    "View": "v",
                    "Create View": "CREATE VIEW `v`",
                    "character_set_client": "utf8mb4",
                    "collation_connection": "utf8mb4_general_ci",
                }
            ]
        )
        result = await async_show.create_view("v")
        assert isinstance(result, ShowCreateViewResult)
        assert result.view_name == "v"
        assert result.character_set_client == "utf8mb4"
        async_backend.execute.assert_awaited_once()

    async def test_columns(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [
                {
                    "Field": "id",
                    "Type": "int",
                    "Null": "NO",
                    "Key": "PRI",
                    "Default": None,
                    "Extra": "auto_increment",
                }
            ]
        )
        col = (await async_show.columns("users", schema="app"))[0]
        assert isinstance(col, ShowColumnResult)
        assert (col.field, col.type, col.null, col.key) == ("id", "int", "NO", "PRI")
        async_backend.execute.assert_awaited_once()

    async def test_columns_full_mode(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [
                {
                    "Field": "name",
                    "Type": "varchar(255)",
                    "Null": "YES",
                    "Privileges": "select",
                    "Comment": "label",
                }
            ]
        )
        col = (await async_show.columns("users", full=True, like="name%"))[0]
        assert (col.privileges, col.comment) == ("select", "label")
        assert "FULL COLUMNS" in _sql(async_backend)
        assert _params(async_backend) == ("name%",)

    async def test_indexes(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [
                {
                    "Table": "users",
                    "Non_unique": 0,
                    "Key_name": "PRIMARY",
                    "Seq_in_index": 1,
                    "Column_name": "id",
                    "Index_type": "BTREE",
                }
            ]
        )
        idx = (await async_show.indexes("users"))[0]
        assert isinstance(idx, ShowIndexResult)
        assert (idx.table, idx.key_name, idx.column_name) == ("users", "PRIMARY", "id")

    async def test_tables(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [{"Tables_in_app": "users"}, {"Tables_in_app": "orders"}]
        )
        tables = await async_show.tables(schema="app", like="%", full=True)
        assert [t.name for t in tables] == ["users", "orders"]
        assert all(isinstance(t, ShowTableResult) for t in tables)
        assert "FULL TABLES" in _sql(async_backend)

    async def test_databases(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result([{"Database": "app"}])
        databases = await async_show.databases(like="a%")
        assert [d.name for d in databases] == ["app"]
        assert all(isinstance(d, ShowDatabaseResult) for d in databases)
        assert _params(async_backend) == ("a%",)

    async def test_table_status(self, async_backend, async_show):
        created = datetime(2026, 5, 6, 7, 8, 9)
        async_backend.execute.return_value = _rows_result(
            [{"Name": "users", "Engine": "InnoDB", "Rows": 3, "Create_time": created}]
        )
        st = (await async_show.table_status(schema="app"))[0]
        assert isinstance(st, ShowTableStatusResult)
        assert (st.name, st.engine, st.rows) == ("users", "InnoDB", 3)
        assert st.create_time == str(created)

    async def test_triggers(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [
                {
                    "Trigger": "trg",
                    "Event": "UPDATE",
                    "Table": "users",
                    "Statement": "BEGIN END",
                    "Timing": "AFTER",
                }
            ]
        )
        trg = (await async_show.triggers(schema="app", table_name="users"))[0]
        assert isinstance(trg, ShowTriggerResult)
        assert (trg.trigger, trg.event, trg.table, trg.timing) == (
            "trg",
            "UPDATE",
            "users",
            "AFTER",
        )
        assert _params(async_backend) == ("users",)

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Source bug: AsyncMariaDBShowFunctionality.create_trigger calls self._target(), "
            "which is defined only on the sync class (should be self._sync_impl._target())."
        ),
    )
    async def test_create_trigger(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [{"Trigger": "trg", "SQL Original Statement": "CREATE TRIGGER trg ..."}]
        )
        result = await async_show.create_trigger("trg", schema="app")
        assert isinstance(result, ShowCreateTriggerResult)
        assert result.trigger_name == "trg"
        assert "`app`.`trg`" in _sql(async_backend)

    @pytest.mark.parametrize("session", [True, False])
    async def test_variables(self, async_backend, async_show, session):
        async_backend.execute.return_value = _rows_result(
            [{"Variable_name": "max_connections", "Value": "151"}]
        )
        variables = await async_show.variables(like="max%", session=session)
        assert (variables[0].variable_name, variables[0].value) == ("max_connections", "151")
        assert ("GLOBAL" in _sql(async_backend)) is (session is False)

    @pytest.mark.parametrize("session", [True, False])
    async def test_status(self, async_backend, async_show, session):
        async_backend.execute.return_value = _rows_result(
            [{"Variable_name": "Uptime", "Value": "100"}]
        )
        statuses = await async_show.status(session=session)
        assert (statuses[0].variable_name, statuses[0].value) == ("Uptime", "100")
        assert ("GLOBAL" in _sql(async_backend)) is (session is False)

    async def test_processlist(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [{"Id": 1, "User": "root", "Host": "localhost", "Command": "Query"}]
        )
        processes = await async_show.processlist(full=True)
        assert (processes[0].id, processes[0].user) == (1, "root")
        assert isinstance(processes[0], ShowProcessListResult)
        assert "FULL PROCESSLIST" in _sql(async_backend)

    async def test_warnings(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [{"Level": "Warning", "Code": 1265, "Message": "truncated"}]
        )
        warnings = await async_show.warnings(limit=5)
        assert (warnings[0].level, warnings[0].code, warnings[0].message) == (
            "Warning",
            1265,
            "truncated",
        )
        assert "LIMIT 5" in _sql(async_backend)

    async def test_errors(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [{"Level": "Error", "Code": 1064, "Message": "syntax"}]
        )
        errors = await async_show.errors(limit=3)
        assert (errors[0].level, errors[0].code) == ("Error", 1064)
        assert "LIMIT 3" in _sql(async_backend)

    async def test_engines(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [{"Engine": "InnoDB", "Support": "DEFAULT", "Transactions": "YES"}]
        )
        engines = await async_show.engines()
        assert (engines[0].engine, engines[0].support, engines[0].transactions) == (
            "InnoDB",
            "DEFAULT",
            "YES",
        )
        assert isinstance(engines[0], ShowEngineResult)

    async def test_charset(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [
                {
                    "Charset": "utf8mb4",
                    "Description": "UTF-8 Unicode",
                    "Default collation": "utf8mb4_general_ci",
                    "Maxlen": 4,
                }
            ]
        )
        charsets = await async_show.charset(like="utf8%")
        assert (charsets[0].charset, charsets[0].maxlen) == ("utf8mb4", 4)
        assert isinstance(charsets[0], ShowCharsetResult)
        assert _params(async_backend) == ("utf8%",)

    async def test_collation(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [
                {
                    "Collation": "utf8mb4_general_ci",
                    "Charset": "utf8mb4",
                    "Id": 45,
                    "Default": "Yes",
                    "Compiled": "Yes",
                    "Sortlen": 1,
                }
            ]
        )
        collations = await async_show.collation()
        assert (collations[0].collation, collations[0].id) == ("utf8mb4_general_ci", 45)
        assert isinstance(collations[0], ShowCollationResult)

    async def test_grants(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [{"Grants for": "GRANT ALL ON *.* TO 'root'@'localhost'"}]
        )
        grants = await async_show.grants(user="root", host="localhost")
        assert grants[0].grants.startswith("GRANT ALL")
        assert isinstance(grants[0], ShowGrantResult)
        assert _params(async_backend) == ("root", "localhost")

    async def test_plugins(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result(
            [{"Name": "InnoDB", "Status": "ACTIVE", "Type": "STORAGE ENGINE"}]
        )
        plugins = await async_show.plugins()
        assert (plugins[0].name, plugins[0].status) == ("InnoDB", "ACTIVE")
        assert isinstance(plugins[0], ShowPluginResult)


class TestAsyncEmptyResults:
    """Empty result sets on the async side mirror the sync behaviour."""

    @pytest.mark.parametrize(
        "method, args",
        [
            ("columns", ("users",)),
            ("indexes", ("users",)),
            ("tables", ()),
            ("databases", ()),
            ("table_status", ()),
            ("triggers", ()),
            ("variables", ()),
            ("status", ()),
            ("processlist", ()),
            ("warnings", ()),
            ("errors", ()),
            ("engines", ()),
            ("charset", ()),
            ("collation", ()),
            ("grants", ()),
            ("plugins", ()),
        ],
    )
    async def test_list_methods_return_empty_list(self, async_backend, async_show, method, args):
        async_backend.execute.return_value = _rows_result([])
        assert await getattr(async_show, method)(*args) == []
        async_backend.execute.assert_awaited_once()

    @pytest.mark.parametrize(
        "method, args",
        [("create_table", ("users",)), ("create_view", ("v",))],
    )
    async def test_single_row_methods_return_none(self, async_backend, async_show, method, args):
        async_backend.execute.return_value = _rows_result([])
        assert await getattr(async_show, method)(*args) is None
        async_backend.execute.assert_awaited_once()

    @pytest.mark.xfail(
        strict=True,
        reason="Source bug: async create_trigger references missing self._target helper.",
    )
    async def test_create_trigger_empty_returns_none(self, async_backend, async_show):
        async_backend.execute.return_value = _rows_result([])
        assert await async_show.create_trigger("t") is None
        async_backend.execute.assert_awaited_once()
