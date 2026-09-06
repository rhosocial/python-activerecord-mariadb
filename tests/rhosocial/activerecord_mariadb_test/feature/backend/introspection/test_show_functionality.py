# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_show_functionality.py
"""
Tests for MySQL SHOW functionality.

Tests the MariaDBShowFunctionality class for SHOW command execution.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestMariaDBShowFunctionalityInit:
    """Tests for MariaDBShowFunctionality initialization."""

    def test_init_with_version(self, mariadb_backend_single):
        """Test initialization with explicit version."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single, version=(10, 5, 0))

        assert func._version == (10, 5, 0)
        assert func._supports_invisible_columns is True

    def test_init_with_mysql57_version(self, mariadb_backend_single):
        """Test initialization with MySQL 5.7 version."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single, version=(5, 7, 0))

        assert func._version == (5, 7, 0)
        assert func._supports_invisible_columns is False

    def test_init_without_version(self, mariadb_backend_single):
        """Test initialization without version (defaults to supporting invisible columns)."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        assert func._version is None
        assert func._supports_invisible_columns is True


class TestShowCreateTableParsing:
    """Tests for SHOW CREATE TABLE result parsing."""

    def test_parse_create_table_result_with_data(self, mariadb_backend_single):
        """Test parsing SHOW CREATE TABLE result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        # Mock result
        result = MagicMock()
        result.data = [{"Table": "users", "Create Table": "CREATE TABLE `users` (`id` INT PRIMARY KEY)"}]

        parsed = func._parse_create_table_result(result, "users")

        assert parsed is not None
        assert parsed.table_name == "users"
        assert "CREATE TABLE" in parsed.create_statement

    def test_parse_create_table_result_empty(self, mariadb_backend_single):
        """Test parsing empty SHOW CREATE TABLE result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = []

        parsed = func._parse_create_table_result(result, "nonexistent")
        assert parsed is None

    def test_parse_create_table_result_alternate_keys(self, mariadb_backend_single):
        """Test parsing result with alternate column keys."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = [{"TABLE": "users", "CREATE TABLE": "CREATE TABLE `users` (`id` INT)"}]

        parsed = func._parse_create_table_result(result, "users")

        assert parsed is not None
        assert parsed.table_name == "users"


class TestShowCreateViewParsing:
    """Tests for SHOW CREATE VIEW result parsing."""

    def test_parse_create_view_result(self, mariadb_backend_single):
        """Test parsing SHOW CREATE VIEW result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = [
            {
                "View": "user_view",
                "Create View": "CREATE VIEW `user_view` AS SELECT * FROM users",
                "character_set_client": "utf8mb4",
                "collation_connection": "utf8mb4_general_ci",
            }
        ]

        parsed = func._parse_create_view_result(result, "user_view")

        assert parsed is not None
        assert parsed.view_name == "user_view"
        assert "CREATE VIEW" in parsed.create_statement
        assert parsed.character_set_client == "utf8mb4"

    def test_parse_create_view_result_empty(self, mariadb_backend_single):
        """Test parsing empty SHOW CREATE VIEW result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = []

        parsed = func._parse_create_view_result(result, "nonexistent")
        assert parsed is None


class TestShowColumnsParsing:
    """Tests for SHOW COLUMNS result parsing."""

    def test_parse_columns_result(self, mariadb_backend_single):
        """Test parsing SHOW COLUMNS result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = [
            {"Field": "id", "Type": "int", "Null": "NO", "Key": "PRI", "Default": None, "Extra": "auto_increment"},
            {"Field": "name", "Type": "varchar(255)", "Null": "YES", "Key": "", "Default": None, "Extra": ""},
        ]

        columns = func._parse_columns_result(result)

        assert len(columns) == 2
        # ShowColumnResult uses 'field' attribute, not 'name'
        assert columns[0].field == "id"
        assert columns[0].type == "int"
        assert columns[1].field == "name"

    def test_parse_columns_result_empty(self, mariadb_backend_single):
        """Test parsing empty SHOW COLUMNS result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = []

        columns = func._parse_columns_result(result)
        assert columns == []


class TestShowIndexesParsing:
    """Tests for SHOW INDEX result parsing."""

    def test_parse_indexes_result(self, mariadb_backend_single):
        """Test parsing SHOW INDEX result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = [
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
                "Index_comment": "",
            }
        ]

        # Method name is _parse_indexes_result (plural)
        indexes = func._parse_indexes_result(result)

        assert len(indexes) >= 1
        # ShowIndexResult uses 'key_name' attribute for index name
        index_names = [idx.key_name for idx in indexes]
        assert "PRIMARY" in index_names


class TestShowTablesParsing:
    """Tests for SHOW TABLES result parsing."""

    def test_parse_tables_result(self, mariadb_backend_single):
        """Test parsing SHOW TABLES result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = [{"Tables_in_test": "users"}, {"Tables_in_test": "posts"}, {"Tables_in_test": "comments"}]

        # Mock database name
        with patch.object(func._backend, "config") as mock_config:
            mock_config.database = "test"
            tables = func._parse_tables_result(result)

        # Returns list of ShowTableResult objects, not strings
        assert len(tables) == 3
        table_names = [t.name for t in tables]
        assert "users" in table_names
        assert "posts" in table_names

    def test_parse_tables_result_empty(self, mariadb_backend_single):
        """Test parsing empty SHOW TABLES result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = []

        tables = func._parse_tables_result(result)
        assert tables == []


class TestShowDatabasesParsing:
    """Tests for SHOW DATABASES result parsing."""

    def test_parse_databases_result(self, mariadb_backend_single):
        """Test parsing SHOW DATABASES result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = [{"Database": "information_schema"}, {"Database": "mysql"}, {"Database": "test_db"}]

        databases = func._parse_databases_result(result)

        # Returns list of ShowDatabaseResult objects, not strings
        assert len(databases) == 3
        db_names = [d.name for d in databases]
        assert "information_schema" in db_names
        assert "mysql" in db_names
        assert "test_db" in db_names


class TestShowTriggersParsing:
    """Tests for SHOW TRIGGERS result parsing."""

    def test_parse_triggers_result(self, mariadb_backend_single):
        """Test parsing SHOW TRIGGERS result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = [
            {
                "Trigger": "users_before_insert",
                "Event": "INSERT",
                "Table": "users",
                "Statement": "BEGIN END",
                "Timing": "BEFORE",
                "Created": None,
                "sql_mode": "",
                "Definer": "root@localhost",
                "character_set_client": "utf8mb4",
                "collation_connection": "utf8mb4_general_ci",
                "Database Collation": "utf8mb4_general_ci",
            }
        ]

        triggers = func._parse_triggers_result(result)

        assert len(triggers) == 1
        # ShowTriggerResult uses 'trigger' attribute, not 'name'
        assert triggers[0].trigger_name == "users_before_insert"
        assert triggers[0].event == "INSERT"
        assert triggers[0].table_name == "users"


class TestShowVariablesParsing:
    """Tests for SHOW VARIABLES result parsing."""

    def test_parse_variables_result(self, mariadb_backend_single):
        """Test parsing SHOW VARIABLES result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = [
            {"Variable_name": "autocommit", "Value": "ON"},
            {"Variable_name": "max_connections", "Value": "151"},
        ]

        variables = func._parse_variables_result(result)

        assert len(variables) == 2
        # ShowVariableResult uses 'variable_name' attribute, not 'name'
        assert variables[0].variable_name == "autocommit"
        assert variables[0].value == "ON"


class TestShowStatusParsing:
    """Tests for SHOW STATUS result parsing."""

    def test_parse_status_result(self, mariadb_backend_single):
        """Test parsing SHOW STATUS result."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        func = MariaDBShowFunctionality(mariadb_backend_single)

        result = MagicMock()
        result.data = [
            {"Variable_name": "Uptime", "Value": "12345"},
            {"Variable_name": "Threads_connected", "Value": "5"},
        ]

        status = func._parse_status_result(result)

        assert len(status) == 2
        # ShowStatusResult uses 'variable_name' attribute, not 'name'
        assert status[0].variable_name == "Uptime"
        assert status[0].value == "12345"


class TestShowFunctionalityExecution:
    """MariaDBShowFunctionality public methods build SQL and parse via backend.execute."""

    @pytest.fixture
    def func(self):
        """Build MariaDBShowFunctionality over a mock backend capturing SQL."""
        from unittest.mock import MagicMock
        from rhosocial.activerecord.backend.result import QueryResult
        from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import MariaDBShowFunctionality

        backend = MagicMock()
        backend.dialect = MariaDBDialect()
        result = QueryResult(data=[], affected_rows=0)
        backend.execute.return_value = result
        return MariaDBShowFunctionality(backend, version=(10, 5, 0)), backend

    def test_create_table(self, func):
        """create_table issues SHOW CREATE TABLE and parses the statement."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(
            data=[{"Table": "users", "Create Table": "CREATE TABLE `users` (id INT)"}], affected_rows=1
        )
        result = f.create_table("users")
        sql, params = backend.execute.call_args[0]
        assert sql == "SHOW CREATE TABLE `users`", f"unexpected SQL: {sql}"
        assert params == (), "SHOW CREATE TABLE takes no params"
        assert result.table_name == "users", "parsed table name should match"
        assert "CREATE TABLE" in result.create_statement, "create statement should be parsed"

    def test_create_table_missing(self, func):
        """create_table on a missing table returns None."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(data=[], affected_rows=0)
        assert f.create_table("ghost") is None, "missing table should parse to None"

    def test_columns(self, func):
        """columns issues SHOW COLUMNS and parses field metadata."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(
            data=[{"Field": "id", "Type": "int", "Null": "NO", "Key": "PRI",
                   "Default": None, "Extra": ""}], affected_rows=1
        )
        columns = f.columns("users")
        sql, _ = backend.execute.call_args[0]
        assert sql == "SHOW COLUMNS FROM `users`", f"unexpected SQL: {sql}"
        assert columns[0].field == "id", "parsed column field should match"
        assert columns[0].type == "int", "parsed column type should match"

    def test_tables(self, func):
        """tables issues SHOW TABLES and parses names."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(
            data=[{"Tables_in_test": "users"}], affected_rows=1
        )
        tables = f.tables()
        sql, _ = backend.execute.call_args[0]
        assert sql == "SHOW TABLES", f"unexpected SQL: {sql}"
        assert tables[0].name == "users", "parsed table name should match"

    def test_databases(self, func):
        """databases issues SHOW DATABASES."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(data=[{"Database": "shop"}], affected_rows=1)
        databases = f.databases()
        assert backend.execute.call_args[0][0] == "SHOW DATABASES", "databases SQL expected"
        assert databases[0].name == "shop", "parsed database name should match"

    def test_table_status(self, func):
        """table_status issues SHOW TABLE STATUS and parses engine fields."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(
            data=[{"Name": "users", "Engine": "InnoDB", "Rows": 10}], affected_rows=1
        )
        status = f.table_status()
        assert backend.execute.call_args[0][0] == "SHOW TABLE STATUS", "table_status SQL expected"
        assert status[0].name == "users", "parsed name should match"
        assert status[0].engine == "InnoDB", "parsed engine should match"

    def test_variables(self, func):
        """variables issues SHOW VARIABLES with LIKE bound as a parameter."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(
            data=[{"Variable_name": "max_connections", "Value": "151"}], affected_rows=1
        )
        variables = f.variables(like="max_%")
        sql, params = backend.execute.call_args[0]
        assert sql == "SHOW VARIABLES LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("max_%",), "LIKE pattern should be a bound parameter"
        assert variables[0].variable_name == "max_connections", "parsed name should match"

    def test_processlist(self, func):
        """processlist issues SHOW PROCESSLIST."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(data=[], affected_rows=0)
        f.processlist()
        assert backend.execute.call_args[0][0] == "SHOW PROCESSLIST", "processlist SQL expected"

    def test_warnings(self, func):
        """warnings issues SHOW WARNINGS with LIMIT."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(data=[], affected_rows=0)
        f.warnings(limit=5)
        assert backend.execute.call_args[0][0] == "SHOW WARNINGS LIMIT 5", "warnings SQL expected"

    def test_engines_charset_plugins(self, func):
        """engines/charset/plugins issue their SHOW statements."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(data=[], affected_rows=0)
        f.engines()
        assert backend.execute.call_args[0][0] == "SHOW ENGINES", "engines SQL expected"
        f.charset()
        assert backend.execute.call_args[0][0] == "SHOW CHARACTER SET", "charset SQL expected"
        f.plugins()
        assert backend.execute.call_args[0][0] == "SHOW PLUGINS", "plugins SQL expected"

    def test_grants(self, func):
        """grants issues SHOW GRANTS (FOR user@host when given)."""
        f, backend = func
        from rhosocial.activerecord.backend.result import QueryResult
        backend.execute.return_value = QueryResult(data=[], affected_rows=0)
        f.grants()
        assert backend.execute.call_args[0][0] == "SHOW GRANTS", "bare grants SQL expected"
        f.grants(user="app", host="10.0.0.%")
        sql, params = backend.execute.call_args[0]
        assert sql == "SHOW GRANTS FOR %s@%s", "user@host grants SQL expected"
        assert params == ("app", "10.0.0.%"), "grants user/host should be bound parameters"

    def test_async_methods_exist(self, func):
        """AsyncShowFunctionality mirrors the sync method surface."""
        from rhosocial.activerecord.backend.impl.mariadb.show.functionality import AsyncMariaDBShowFunctionality
        async_methods = {
            m for m in dir(AsyncMariaDBShowFunctionality) if not m.startswith("_")
        }
        assert "create_table" in async_methods, "create_table async method should exist"
        assert "columns" in async_methods, "columns async method should exist"
        assert "tables" in async_methods, "tables async method should exist"
        assert "variables" in async_methods, "variables async method should exist"
