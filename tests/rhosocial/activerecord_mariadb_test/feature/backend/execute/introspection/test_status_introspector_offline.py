# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/introspection/test_status_introspector_offline.py
"""Database-free unit tests for MariaDB's status introspector.

These tests never open a MariaDB connection. The pure parsing helpers are
exercised directly, and the I/O-facing methods are driven through mocked
``_show_variables`` / ``_show_status`` / ``_execute_query*`` collaborators
built with :class:`~unittest.mock.MagicMock` / :class:`~unittest.mock.AsyncMock`.
No MariaDB server, driver or dialect connection is required.

Both the synchronous :class:`MariaDBStatusIntrospector` and its native-async
twin :class:`AsyncMariaDBStatusIntrospector` are covered symmetrically. MariaDB
has a real asyncio driver, so the async class is production code, not a
pseudo-async wrapper: its ``await``-based cursor plumbing and every async
reader are exercised here.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.introspection.status_introspector import (
    MARIADB_BINLOG_VARIABLES,
    MARIADB_CONFIG_VARIABLES,
    MARIADB_REPLICATION_VARIABLES,
    MARIADB_STATUS_VARIABLES,
    AsyncMariaDBStatusIntrospector,
    MariaDBStatusIntrospector,
)
from rhosocial.activerecord.backend.impl.mariadb.introspection.status_types import (
    MariaDBBinaryLogInfo,
    MariaDBReplicationInfo,
    MariaDBServerOverview,
)
from rhosocial.activerecord.backend.introspection.status import (
    ConnectionInfo,
    DatabaseBriefInfo,
    SessionInfo,
    StatusCategory,
    StatusItem,
    StorageInfo,
    UserInfo,
)

_DIALECT_FORMATTERS = (
    "format_show_variables_statement",
    "format_show_status_statement",
    "format_show_master_status_statement",
    "format_show_slave_status_statement",
    "format_mariadb_version_query",
    "format_mariadb_storage_size_query",
    "format_mariadb_database_list_query",
    "format_mariadb_user_list_query",
    "format_mariadb_session_info_query",
)


@pytest.fixture
def backend():
    """A backend mock with a real dialect whose formatters return harmless SQL.

    The expression classes validate that their dialect is a real
    ``SQLDialectBase`` instance, so a bare ``MagicMock`` cannot be used. A
    real :class:`MariaDBDialect` is constructed (no connection needed) and its
    format methods are patched to a fixed ``(sql, params)`` pair so rendering
    never depends on a server or on version-specific SQL.
    """
    backend = MagicMock()
    dialect = MariaDBDialect(version=(11, 4, 0))
    patches = [
        patch.object(dialect, name, return_value=("SHOW", ())) for name in _DIALECT_FORMATTERS
    ]
    for item in patches:
        item.start()
    backend.dialect = dialect
    yield backend
    for item in patches:
        item.stop()


@pytest.fixture
def introspector(backend):
    """A synchronous introspector backed entirely by mocks."""
    return MariaDBStatusIntrospector(backend=backend)


@pytest.fixture
def async_introspector(backend):
    """A native-async introspector backed entirely by mocks."""
    return AsyncMariaDBStatusIntrospector(backend=backend)


@pytest.fixture
def async_cursor(backend):
    """A cursor whose awaited DB-API calls are AsyncMocks.

    ``cursor()`` itself is synchronous; ``execute`` / ``fetchall`` / ``close``
    are awaited by the async introspector and are therefore AsyncMocks.
    """
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.close = AsyncMock()
    backend._connection.cursor.return_value = cursor
    return cursor


class TestParseHelpers:
    """The pure scalar parsers on the mixin."""

    def test_get_vendor_name(self, introspector):
        assert introspector._get_vendor_name() == "MariaDB"

    @pytest.mark.parametrize(
        "raw, expected",
        [("11", 11), ("0", 0), ("007", 7), ("3306", 3306)],
    )
    def test_parse_variable_value_digit_strings(self, introspector, raw, expected):
        assert introspector.parse_variable_value(raw) == expected
        assert isinstance(introspector.parse_variable_value(raw), int)

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("ON", True),
            ("yes", True),
            ("TRUE", True),
            ("off", False),
            ("No", False),
            ("false", False),
        ],
    )
    def test_parse_variable_value_boolean_strings(self, introspector, raw, expected):
        assert introspector.parse_variable_value(raw) is expected

    @pytest.mark.parametrize(
        "raw",
        [None, 5, 0, 3.14, "ROW", "", "ON ", "maybe"],
    )
    def test_parse_variable_value_passthrough(self, introspector, raw):
        assert introspector.parse_variable_value(raw) == raw

    @pytest.mark.parametrize(
        "raw, expected",
        [
            (None, None),
            ("ON", True),
            ("0", False),
            (1, True),
            ("yes", True),
            ("off", False),
        ],
    )
    def test_parse_optional_bool(self, introspector, raw, expected):
        assert introspector.parse_optional_bool(raw) is expected

    @pytest.mark.parametrize(
        "raw, expected",
        [(None, None), ("3306", 3306), (100, 100), ("0", 0)],
    )
    def test_parse_optional_int(self, introspector, raw, expected):
        assert introspector.parse_optional_int(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            (None, []),
            ("", []),
            ("   ", []),
            ("a,b", ["a", "b"]),
            (" a , b ", ["a", "b"]),
            ("a,,b,", ["a", "b"]),
            (["db1", " db2 ", "", "db3"], ["db1", "db2", "db3"]),
            (("db1", "db2"), ["db1", "db2"]),
        ],
    )
    def test_parse_db_list(self, introspector, raw, expected):
        assert introspector.parse_db_list(raw) == expected


class TestCreateStatusItem:
    """``_create_status_item`` parses the value and fills the dataclass."""

    def test_defaults(self, introspector):
        item = introspector._create_status_item(
            name="character_set_server",
            value="utf8mb4",
            category=StatusCategory.CONFIGURATION,
        )
        assert isinstance(item, StatusItem)
        assert item.name == "character_set_server"
        assert item.value == "utf8mb4"
        assert item.category is StatusCategory.CONFIGURATION
        assert item.description is None
        assert item.unit is None
        assert item.is_readonly is False
        assert item.is_dynamic is True

    def test_parses_value_and_honours_overrides(self, introspector):
        item = introspector._create_status_item(
            name="max_connections",
            value="151",
            category=StatusCategory.CONNECTION,
            description="Maximum simultaneous connections",
            unit="connections",
            is_readonly=True,
            is_dynamic=False,
        )
        assert item.value == 151
        assert isinstance(item.value, int)
        assert item.category is StatusCategory.CONNECTION
        assert item.description == "Maximum simultaneous connections"
        assert item.unit == "connections"
        assert item.is_readonly is True
        assert item.is_dynamic is False

    @pytest.mark.parametrize(
        "raw, expected",
        [("ON", True), ("OFF", False), ("42", 42), ("ROW", "ROW"), (None, None)],
    )
    def test_value_is_parsed(self, introspector, raw, expected):
        item = introspector._create_status_item("v", raw, StatusCategory.PERFORMANCE)
        assert item.value == expected


_SAMPLE_MASTER_ROW = {
    "file": "mysql-bin.000042",
    "position": "1200",
    "binlog_do_db": "app,reporting",
    "binlog_ignore_db": "mysql , sys",
    "executed_gtid_set": "0-1-100",
}


class TestParseBinaryLogInfo:
    """``parse_binary_log_info`` keeps the three row states distinct."""

    def test_variables_only_when_rows_absent(self, introspector):
        variables = {
            "log_bin": "OFF",
            "binlog_format": "ROW",
            "gtid_binlog_pos": "0-1-5",
            "gtid_strict_mode": "ON",
        }
        info = introspector.parse_binary_log_info(variables, None)

        assert isinstance(info, MariaDBBinaryLogInfo)
        assert info.log_enabled is False
        assert info.log_format == "ROW"
        assert info.gtid_binlog_pos == "0-1-5"
        assert info.gtid_strict_mode is True
        assert info.current_log_file is None
        assert info.current_log_position is None
        assert info.binlog_do_db == []
        assert info.binlog_ignore_db == []
        assert info.executed_gtid_set is None

    @pytest.mark.parametrize("rows", [None, []])
    def test_no_row_leaves_file_fields_unset(self, introspector, rows):
        info = introspector.parse_binary_log_info({"log_bin": "ON"}, rows)
        assert info.current_log_file is None
        assert info.current_log_position is None
        assert info.binlog_do_db == []

    def test_with_master_status_row(self, introspector):
        variables = {"log_bin": "ON", "binlog_format": "MIXED", "gtid_strict_mode": "OFF"}
        info = introspector.parse_binary_log_info(variables, [_SAMPLE_MASTER_ROW])

        assert info.log_enabled is True
        assert info.log_format == "MIXED"
        assert info.gtid_strict_mode is False
        assert info.current_log_file == "mysql-bin.000042"
        assert info.current_log_position == 1200
        assert isinstance(info.current_log_position, int)
        assert info.binlog_do_db == ["app", "reporting"]
        assert info.binlog_ignore_db == ["mysql", "sys"]
        assert info.executed_gtid_set == "0-1-100"

    def test_empty_variable_values_become_none(self, introspector):
        info = introspector.parse_binary_log_info(
            {"log_bin": "", "binlog_format": "", "gtid_binlog_pos": ""},
            [],
        )
        assert info.log_enabled is False
        assert info.log_format is None
        assert info.gtid_binlog_pos is None


_SAMPLE_SLAVE_ROW = {
    "slave_io_running": "Yes",
    "slave_sql_running": "Yes",
    "master_host": "10.0.0.5",
    "master_port": "3306",
    "master_user": "repl",
    "seconds_behind_master": "0",
    "master_log_file": "mysql-bin.000041",
    "read_master_log_pos": "900",
    "relay_master_log_file": "mysql-bin.000041",
    "slave_io_state": "Waiting for master to send event",
    "last_io_errno": "0",
    "last_io_error": "",
    "last_sql_errno": "0",
    "last_sql_error": "",
    "relay_log_file": "mysqld-relay-bin.000010",
    "relay_log_pos": "700",
    "exec_master_log_pos": "900",
    "using_gtid": "1",
    "gtid_io_pos": "0-1-90",
}


class TestParseReplicationInfo:
    """``parse_replication_info`` answers identity and the replica side."""

    def test_rows_none_means_not_asked(self, introspector):
        variables = {"server_id": "10", "log_slave_updates": "ON"}
        info = introspector.parse_replication_info(variables, None)

        assert isinstance(info, MariaDBReplicationInfo)
        assert info.server_id == 10
        assert info.log_slave_updates is True
        assert info.is_replica is None
        assert info.master_host is None

    def test_empty_rows_means_not_a_replica(self, introspector):
        info = introspector.parse_replication_info({"server_id": "10"}, [])
        assert info.is_replica is False
        assert info.master_host is None

    def test_replica_row_parses_every_field(self, introspector):
        variables = {"server_id": "10", "log_slave_updates": "OFF"}
        info = introspector.parse_replication_info(variables, [_SAMPLE_SLAVE_ROW])

        assert info.server_id == 10
        assert info.log_slave_updates is False
        assert info.is_replica is True
        assert info.slave_io_running == "Yes"
        assert info.slave_sql_running == "Yes"
        assert info.master_host == "10.0.0.5"
        assert info.master_port == 3306
        assert info.master_user == "repl"
        assert info.seconds_behind_master == 0
        assert info.master_log_file == "mysql-bin.000041"
        assert info.read_master_log_pos == 900
        assert info.relay_master_log_file == "mysql-bin.000041"
        assert info.slave_io_state == "Waiting for master to send event"
        assert info.last_io_errno == 0
        assert info.last_io_error == ""
        assert info.last_sql_errno == 0
        assert info.last_sql_error == ""
        assert info.relay_log_file == "mysqld-relay-bin.000010"
        assert info.relay_log_pos == 700
        assert info.exec_master_log_pos == 900
        assert info.using_gtid == "1"
        assert info.gtid_io_pos == "0-1-90"

    def test_numeric_fields_tolerate_none(self, introspector):
        row = {
            "master_port": None,
            "seconds_behind_master": None,
            "read_master_log_pos": None,
            "last_io_errno": None,
            "last_sql_errno": None,
            "relay_log_pos": None,
            "exec_master_log_pos": None,
        }
        info = introspector.parse_replication_info({"server_id": "10"}, [row])
        assert info.is_replica is True
        assert info.master_port is None
        assert info.seconds_behind_master is None
        assert info.read_master_log_pos is None
        assert info.last_io_errno is None
        assert info.last_sql_errno is None
        assert info.relay_log_pos is None
        assert info.exec_master_log_pos is None

    @pytest.mark.parametrize("raw, expected", [("0", 0), (0, 0), (None, None)])
    def test_server_id_identity(self, introspector, raw, expected):
        info = introspector.parse_replication_info({"server_id": raw}, None)
        assert info.server_id == expected


class TestBuildServerOverview:
    """``_build_server_overview`` composes MariaDB's covariant overview."""

    def test_build_and_serialize(self, introspector):
        config = [StatusItem("max_connections", 151, StatusCategory.CONNECTION, unit="connections")]
        perf = [StatusItem("Uptime", 1000, StatusCategory.PERFORMANCE, unit="seconds")]
        conn = ConnectionInfo(active_count=10, max_connections=151)
        storage = StorageInfo(total_size_bytes=300, data_size_bytes=200, index_size_bytes=100)
        databases = [DatabaseBriefInfo(name="app", size_bytes=100)]
        users = [UserInfo(name="root", host="localhost", is_superuser=True)]
        binary_log = MariaDBBinaryLogInfo(log_enabled=True)
        replication = MariaDBReplicationInfo(server_id=1)

        overview = introspector._build_server_overview(
            "11.4.0",
            SessionInfo(user="root", database="app"),
            config,
            perf,
            conn,
            storage,
            databases,
            users,
            binary_log,
            replication,
        )

        assert isinstance(overview, MariaDBServerOverview)
        assert overview.server_version == "11.4.0"
        assert overview.server_vendor == "MariaDB"
        assert overview.session.user == "root"
        assert overview.configuration == config + perf
        assert overview.performance == []
        assert overview.connections is conn
        assert overview.storage is storage
        assert overview.databases == databases
        assert overview.users == users
        assert overview.binary_log is binary_log
        assert overview.replication is replication

        as_dict = overview.to_dict()
        assert as_dict["server_vendor"] == "MariaDB"
        assert as_dict["configuration"][0]["category"] == "connection"
        assert as_dict["binary_log"]["log_enabled"] is True
        assert as_dict["replication"]["server_id"] == 1


class TestLowLevelExecution:
    """Cursor plumbing in ``_execute_query`` / ``_execute_query_dict``."""

    def test_execute_query_returns_rows_and_closes_cursor(self, introspector, backend):
        cursor = backend._connection.cursor.return_value
        cursor.fetchall.return_value = [("11.4.0",)]

        rows = introspector._execute_query("SELECT VERSION()", ())

        assert rows == [("11.4.0",)]
        cursor.execute.assert_called_once_with("SELECT VERSION()", ())
        cursor.close.assert_called_once_with()

    def test_execute_query_closes_cursor_on_error(self, introspector, backend):
        cursor = backend._connection.cursor.return_value
        cursor.execute.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            introspector._execute_query("SELECT 1", ())
        cursor.close.assert_called_once_with()

    def test_execute_query_dict_lowercases_columns(self, introspector, backend):
        cursor = backend._connection.cursor.return_value
        cursor.description = [("File",), ("Position",)]
        cursor.fetchall.return_value = [("mysql-bin.000042", 1200)]

        rows = introspector._execute_query_dict("SHOW MASTER STATUS")

        assert rows == [{"file": "mysql-bin.000042", "position": 1200}]
        cursor.close.assert_called_once_with()

    def test_execute_query_dict_no_rows(self, introspector, backend):
        cursor = backend._connection.cursor.return_value
        cursor.description = [("File",)]
        cursor.fetchall.return_value = []
        assert introspector._execute_query_dict("SHOW MASTER STATUS") == []


class TestShowVariablesAndStatus:
    """``_show_variables`` / ``_show_status`` map rows and swallow errors."""

    def test_show_variables_lowercases_keys(self, introspector):
        responses = [[("MAX_CONNECTIONS", "151")], [("wait_timeout", "600")]]
        with patch.object(introspector, "_execute_query", side_effect=responses) as query:
            result = introspector._show_variables(["max_connections", "wait_timeout"])

        assert result == {"max_connections": "151", "wait_timeout": "600"}
        assert query.call_count == 2

    def test_show_variables_ignores_empty_and_errors(self, introspector):
        responses = [[("a", "1")], [], RuntimeError("server said no")]
        with patch.object(introspector, "_execute_query", side_effect=responses):
            result = introspector._show_variables(["a", "b", "c"])
        assert result == {"a": "1"}

    def test_show_status_keeps_original_key_case(self, introspector, backend):
        with patch.object(
            introspector, "_execute_query", return_value=[("Threads_connected", "42")]
        ):
            result = introspector._show_status(["Threads_connected"])

        assert result == {"Threads_connected": "42"}
        statement = backend.dialect.format_show_status_statement.call_args.args[0]
        assert statement.session is False
        assert statement.like_pattern == "Threads_connected"

    def test_show_status_ignores_errors(self, introspector):
        with patch.object(introspector, "_execute_query", side_effect=RuntimeError("boom")):
            assert introspector._show_status(["Threads_connected"]) == {}

    def test_show_status_continues_after_error(self, introspector):
        responses = [RuntimeError("boom"), [("Questions", "9000")]]
        with patch.object(introspector, "_execute_query", side_effect=responses):
            result = introspector._show_status(["Threads_connected", "Questions"])
        assert result == {"Questions": "9000"}

    def test_show_status_skips_empty_rows(self, introspector):
        responses = [[], [("Questions", "9000")]]
        with patch.object(introspector, "_execute_query", side_effect=responses):
            result = introspector._show_status(["Threads_connected", "Questions"])
        assert result == {"Questions": "9000"}

    def test_variable_and_status_name_catalogues(self, introspector):
        assert [row[0] for row in MARIADB_CONFIG_VARIABLES]
        assert [row[0] for row in MARIADB_STATUS_VARIABLES]
        assert "log_bin" in MARIADB_BINLOG_VARIABLES
        assert "server_id" in MARIADB_REPLICATION_VARIABLES


class TestMockedHighLevelMethods:
    """High-level readers driven by mocked collaborators."""

    def test_list_configuration_all(self, introspector):
        variables = {
            "max_connections": "151",
            "wait_timeout": "600",
            "character_set_server": "utf8mb4",
            "not_a_known_variable": "1",
        }
        with patch.object(introspector, "_show_variables", return_value=variables):
            items = introspector.list_configuration()

        by_name = {item.name: item for item in items}
        assert "not_a_known_variable" not in by_name
        assert len(items) == 3
        assert by_name["max_connections"].value == 151
        assert by_name["max_connections"].category is StatusCategory.CONNECTION
        assert by_name["max_connections"].unit is None
        assert by_name["wait_timeout"].value == 600
        assert by_name["wait_timeout"].unit == "seconds"
        assert by_name["character_set_server"].category is StatusCategory.CONFIGURATION
        assert by_name["character_set_server"].description == "Server character set"

    def test_list_configuration_category_filter(self, introspector):
        variables = {
            "max_connections": "151",
            "wait_timeout": "600",
            "datadir": "/var/lib/mysql",
            "character_set_server": "utf8mb4",
        }
        with patch.object(introspector, "_show_variables", return_value=variables):
            items = introspector.list_configuration(StatusCategory.CONNECTION)

        assert {item.name for item in items} == {"max_connections", "wait_timeout"}
        assert all(item.category is StatusCategory.CONNECTION for item in items)

    def test_list_configuration_empty(self, introspector):
        with patch.object(introspector, "_show_variables", return_value={}):
            assert introspector.list_configuration() == []

    def test_list_performance_metrics(self, introspector):
        statuses = {
            "Threads_connected": "10",
            "Questions": "9000",
            "Uptime": "3600",
            "unknown_status": "5",
        }
        with patch.object(introspector, "_show_status", return_value=statuses):
            items = introspector.list_performance_metrics()

        by_name = {item.name: item for item in items}
        assert "unknown_status" not in by_name
        assert len(items) == 3
        assert by_name["Threads_connected"].category is StatusCategory.CONNECTION
        assert by_name["Threads_connected"].is_readonly is True
        assert by_name["Questions"].value == 9000
        assert by_name["Uptime"].unit == "seconds"

    def test_list_performance_metrics_category_filter(self, introspector):
        statuses = {"Threads_connected": "10", "Questions": "9000", "Uptime": "3600"}
        with patch.object(introspector, "_show_status", return_value=statuses):
            items = introspector.list_performance_metrics(StatusCategory.PERFORMANCE)

        assert {item.name for item in items} == {"Questions", "Uptime"}
        assert all(item.category is StatusCategory.PERFORMANCE for item in items)

    def test_get_connection_info(self, introspector):
        with patch.object(
            introspector, "_show_status", return_value={"Threads_connected": "42"}
        ), patch.object(introspector, "_show_variables", return_value={"max_connections": "151"}):
            info = introspector.get_connection_info()

        assert isinstance(info, ConnectionInfo)
        assert info.active_count == 42
        assert info.max_connections == 151

    def test_get_connection_info_max_zero_is_none(self, introspector):
        with patch.object(
            introspector, "_show_status", return_value={"Threads_connected": "3"}
        ), patch.object(introspector, "_show_variables", return_value={"max_connections": "0"}):
            info = introspector.get_connection_info()
        assert info.active_count == 3
        assert info.max_connections is None

    def test_get_connection_info_defaults(self, introspector):
        with patch.object(introspector, "_show_status", return_value={}), patch.object(
            introspector, "_show_variables", return_value={}
        ):
            info = introspector.get_connection_info()
        assert info.active_count == 0
        assert info.max_connections is None

    def test_get_storage_info(self, introspector):
        row = {"data_bytes": "1000", "index_bytes": "250"}
        with patch.object(introspector, "_execute_query_dict", return_value=[row]):
            info = introspector.get_storage_info()

        assert isinstance(info, StorageInfo)
        assert info.data_size_bytes == 1000
        assert info.index_size_bytes == 250
        assert info.total_size_bytes == 1250

    @pytest.mark.parametrize("outcome", [[], RuntimeError("boom")])
    def test_get_storage_info_fallback(self, introspector, outcome):
        effect = outcome if isinstance(outcome, Exception) else None
        with patch.object(
            introspector, "_execute_query_dict", side_effect=effect, return_value=outcome
        ):
            info = introspector.get_storage_info()
        assert info == StorageInfo()

    def test_list_databases(self, introspector):
        rows = [
            {"schema_name": "app", "size_bytes": "1024", "table_count": "12", "view_count": "2"},
            {"schema_name": "empty"},
        ]
        with patch.object(introspector, "_execute_query_dict", return_value=rows):
            dbs = introspector.list_databases()

        assert all(isinstance(db, DatabaseBriefInfo) for db in dbs)
        assert dbs[0].name == "app"
        assert dbs[0].size_bytes == 1024
        assert dbs[0].table_count == 12
        assert dbs[0].view_count == 2
        assert dbs[1].name == "empty"
        assert dbs[1].size_bytes is None
        assert dbs[1].table_count == 0
        assert dbs[1].view_count == 0

    def test_list_databases_error(self, introspector):
        with patch.object(introspector, "_execute_query_dict", side_effect=RuntimeError("boom")):
            assert introspector.list_databases() == []

    def test_list_users(self, introspector):
        rows = [
            {"user": "root", "host": "localhost", "super_priv": "Y"},
            {"user": "app", "host": "%", "super_priv": "N"},
            {"user": "guest"},
        ]
        with patch.object(introspector, "_execute_query_dict", return_value=rows):
            users = introspector.list_users()

        assert all(isinstance(user, UserInfo) for user in users)
        assert users[0].name == "root"
        assert users[0].host == "localhost"
        assert users[0].is_superuser is True
        assert users[1].is_superuser is False
        assert users[2].host is None
        assert users[2].is_superuser is False

    def test_list_users_error(self, introspector):
        with patch.object(introspector, "_execute_query_dict", side_effect=RuntimeError("boom")):
            assert introspector.list_users() == []

    @pytest.mark.parametrize(
        "have_ssl, expected",
        [("YES", True), ("yes", True), ("NO", False), ("", False)],
    )
    def test_get_session_info_ssl(self, introspector, have_ssl, expected):
        row = {
            "cur_user": "root@localhost",
            "cur_db": "app",
            "host": "localhost",
            "have_ssl": have_ssl,
        }
        with patch.object(introspector, "_execute_query_dict", return_value=[row]):
            info = introspector.get_session_info()

        assert isinstance(info, SessionInfo)
        assert info.user == "root@localhost"
        assert info.database == "app"
        assert info.host == "localhost"
        assert info.ssl_enabled is expected

    @pytest.mark.parametrize("outcome", [[], RuntimeError("boom")])
    def test_get_session_info_fallback(self, introspector, outcome):
        effect = outcome if isinstance(outcome, Exception) else None
        with patch.object(
            introspector, "_execute_query_dict", side_effect=effect, return_value=outcome
        ):
            assert introspector.get_session_info() == SessionInfo()

    def test_get_version_string(self, introspector):
        with patch.object(introspector, "_execute_query", return_value=[("11.4.0-MariaDB",)]):
            assert introspector._get_version_string() == "11.4.0-MariaDB"

    @pytest.mark.parametrize("outcome", [[], RuntimeError("boom")])
    def test_get_version_string_unknown(self, introspector, outcome):
        effect = outcome if isinstance(outcome, Exception) else None
        with patch.object(introspector, "_execute_query", side_effect=effect, return_value=outcome):
            assert introspector._get_version_string() == "Unknown"


class TestBinaryAndReplicationWithMocks:
    """The row question is skipped or asked based on the variables."""

    @pytest.mark.parametrize("log_bin", ["OFF", "0", "false", ""])
    def test_binary_log_off_does_not_query_master_status(self, introspector, log_bin):
        variables = {"log_bin": log_bin, "binlog_format": "ROW"}
        with patch.object(introspector, "_show_variables", return_value=variables), patch.object(
            introspector, "_execute_query_dict"
        ) as query:
            info = introspector.get_binary_log_info()

        query.assert_not_called()
        assert info.log_enabled is False
        assert info.current_log_file is None

    @pytest.mark.parametrize("log_bin", ["ON", "1", "true"])
    def test_binary_log_on_queries_master_status(self, introspector, log_bin):
        variables = {"log_bin": log_bin, "binlog_format": "ROW"}
        with patch.object(introspector, "_show_variables", return_value=variables), patch.object(
            introspector, "_execute_query_dict", return_value=[_SAMPLE_MASTER_ROW]
        ):
            info = introspector.get_binary_log_info()

        assert info.log_enabled is True
        assert info.current_log_file == "mysql-bin.000042"
        assert info.current_log_position == 1200
        assert info.binlog_do_db == ["app", "reporting"]

    def test_replication_not_a_replica(self, introspector):
        with patch.object(
            introspector,
            "_show_variables",
            return_value={"server_id": "10", "log_slave_updates": "ON"},
        ), patch.object(introspector, "_execute_query_dict", return_value=[]):
            info = introspector.get_replication_info()

        assert info.server_id == 10
        assert info.log_slave_updates is True
        assert info.is_replica is False

    def test_replication_row(self, introspector):
        with patch.object(
            introspector, "_show_variables", return_value={"server_id": "10"}
        ), patch.object(introspector, "_execute_query_dict", return_value=[_SAMPLE_SLAVE_ROW]):
            info = introspector.get_replication_info()
        assert info.is_replica is True
        assert info.master_host == "10.0.0.5"
        assert info.master_port == 3306

    def test_replication_query_error_keeps_identity(self, introspector):
        with patch.object(
            introspector, "_show_variables", return_value={"server_id": "10"}
        ), patch.object(introspector, "_execute_query_dict", side_effect=RuntimeError("boom")):
            info = introspector.get_replication_info()
        assert info.server_id == 10
        assert info.is_replica is None


class TestGetOverview:
    """``get_overview`` composes every reader into one MariaDB overview."""

    def test_get_overview_composes_all_parts(self, introspector):
        parts = {
            "_get_version_string": "11.4.0-MariaDB",
            "get_session_info": SessionInfo(user="root"),
            "list_configuration": [StatusItem("a", 1, StatusCategory.CONFIGURATION)],
            "list_performance_metrics": [StatusItem("b", 2, StatusCategory.PERFORMANCE)],
            "get_connection_info": ConnectionInfo(active_count=5),
            "get_storage_info": StorageInfo(total_size_bytes=10),
            "list_databases": [DatabaseBriefInfo(name="app")],
            "list_users": [UserInfo(name="root")],
            "get_binary_log_info": MariaDBBinaryLogInfo(log_enabled=False),
            "get_replication_info": MariaDBReplicationInfo(server_id=1, is_replica=False),
        }
        patches = [
            patch.object(introspector, name, return_value=value) for name, value in parts.items()
        ]
        for item in patches:
            item.start()
        try:
            overview = introspector.get_overview()
        finally:
            for item in patches:
                item.stop()

        assert isinstance(overview, MariaDBServerOverview)
        assert overview.server_version == "11.4.0-MariaDB"
        assert overview.server_vendor == "MariaDB"
        assert overview.session is parts["get_session_info"]
        assert overview.configuration == (
            parts["list_configuration"] + parts["list_performance_metrics"]
        )
        assert overview.connections is parts["get_connection_info"]
        assert overview.storage is parts["get_storage_info"]
        assert overview.databases == parts["list_databases"]
        assert overview.users == parts["list_users"]
        assert overview.binary_log.log_enabled is False
        assert overview.replication.is_replica is False


class TestAsyncLowLevelExecution:
    """Awaited cursor plumbing in the native-async introspector."""

    @pytest.mark.asyncio
    async def test_execute_query_returns_rows_and_closes_cursor(
        self, async_introspector, async_cursor
    ):
        async_cursor.fetchall.return_value = [("11.4.0-MariaDB",)]

        rows = await async_introspector._execute_query("SELECT VERSION()", ())

        assert rows == [("11.4.0-MariaDB",)]
        async_cursor.execute.assert_awaited_once_with("SELECT VERSION()", ())
        async_cursor.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_execute_query_closes_cursor_on_error(self, async_introspector, async_cursor):
        async_cursor.execute.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await async_introspector._execute_query("SELECT 1", ())
        async_cursor.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_execute_query_dict_lowercases_columns(self, async_introspector, async_cursor):
        async_cursor.description = [("File",), ("Position",)]
        async_cursor.fetchall.return_value = [("mysql-bin.000042", 1200)]

        rows = await async_introspector._execute_query_dict("SHOW MASTER STATUS")

        assert rows == [{"file": "mysql-bin.000042", "position": 1200}]
        async_cursor.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_execute_query_dict_no_rows(self, async_introspector, async_cursor):
        async_cursor.description = [("File",)]
        async_cursor.fetchall.return_value = []
        assert await async_introspector._execute_query_dict("SHOW MASTER STATUS") == []


class TestAsyncShowVariablesAndStatus:
    """Awaited SHOW helpers map rows and swallow errors just like sync."""

    @pytest.mark.asyncio
    async def test_show_variables_lowercases_keys(self, async_introspector):
        query = AsyncMock(side_effect=[[("MAX_CONNECTIONS", "151")], [("wait_timeout", "600")]])
        with patch.object(async_introspector, "_execute_query", new=query):
            result = await async_introspector._show_variables(["max_connections", "wait_timeout"])

        assert result == {"max_connections": "151", "wait_timeout": "600"}
        assert query.await_count == 2

    @pytest.mark.asyncio
    async def test_show_variables_ignores_empty_and_errors(self, async_introspector):
        query = AsyncMock(side_effect=[[("a", "1")], [], RuntimeError("server said no")])
        with patch.object(async_introspector, "_execute_query", new=query):
            result = await async_introspector._show_variables(["a", "b", "c"])
        assert result == {"a": "1"}

    @pytest.mark.asyncio
    async def test_show_status_keeps_original_key_case(self, async_introspector, backend):
        query = AsyncMock(return_value=[("Threads_connected", "42")])
        with patch.object(async_introspector, "_execute_query", new=query):
            result = await async_introspector._show_status(["Threads_connected"])

        assert result == {"Threads_connected": "42"}
        statement = backend.dialect.format_show_status_statement.call_args.args[0]
        assert statement.session is False
        assert statement.like_pattern == "Threads_connected"

    @pytest.mark.asyncio
    async def test_show_status_ignores_errors(self, async_introspector):
        query = AsyncMock(side_effect=RuntimeError("boom"))
        with patch.object(async_introspector, "_execute_query", new=query):
            assert await async_introspector._show_status(["Threads_connected"]) == {}

    @pytest.mark.asyncio
    async def test_show_status_continues_after_error(self, async_introspector):
        query = AsyncMock(side_effect=[RuntimeError("boom"), [("Questions", "9000")]])
        with patch.object(async_introspector, "_execute_query", new=query):
            result = await async_introspector._show_status(["Threads_connected", "Questions"])
        assert result == {"Questions": "9000"}

    @pytest.mark.asyncio
    async def test_show_status_skips_empty_rows(self, async_introspector):
        query = AsyncMock(side_effect=[[], [("Questions", "9000")]])
        with patch.object(async_introspector, "_execute_query", new=query):
            result = await async_introspector._show_status(["Threads_connected", "Questions"])
        assert result == {"Questions": "9000"}


class TestAsyncMockedHighLevelMethods:
    """Every async reader is driven by mocked async collaborators."""

    @pytest.mark.asyncio
    async def test_list_configuration_all(self, async_introspector):
        variables = {
            "max_connections": "151",
            "wait_timeout": "600",
            "character_set_server": "utf8mb4",
            "not_a_known_variable": "1",
        }
        with patch.object(
            async_introspector, "_show_variables", new=AsyncMock(return_value=variables)
        ):
            items = await async_introspector.list_configuration()

        by_name = {item.name: item for item in items}
        assert "not_a_known_variable" not in by_name
        assert len(items) == 3
        assert by_name["max_connections"].value == 151
        assert by_name["max_connections"].category is StatusCategory.CONNECTION
        assert by_name["max_connections"].unit is None
        assert by_name["wait_timeout"].value == 600
        assert by_name["wait_timeout"].unit == "seconds"
        assert by_name["character_set_server"].category is StatusCategory.CONFIGURATION

    @pytest.mark.asyncio
    async def test_list_configuration_category_filter(self, async_introspector):
        variables = {
            "max_connections": "151",
            "wait_timeout": "600",
            "datadir": "/var/lib/mysql",
            "character_set_server": "utf8mb4",
        }
        with patch.object(
            async_introspector, "_show_variables", new=AsyncMock(return_value=variables)
        ):
            items = await async_introspector.list_configuration(StatusCategory.CONNECTION)

        assert {item.name for item in items} == {"max_connections", "wait_timeout"}
        assert all(item.category is StatusCategory.CONNECTION for item in items)

    @pytest.mark.asyncio
    async def test_list_configuration_empty(self, async_introspector):
        with patch.object(async_introspector, "_show_variables", new=AsyncMock(return_value={})):
            assert await async_introspector.list_configuration() == []

    @pytest.mark.asyncio
    async def test_list_performance_metrics(self, async_introspector):
        statuses = {
            "Threads_connected": "10",
            "Questions": "9000",
            "Uptime": "3600",
            "unknown_status": "5",
        }
        with patch.object(async_introspector, "_show_status", new=AsyncMock(return_value=statuses)):
            items = await async_introspector.list_performance_metrics()

        by_name = {item.name: item for item in items}
        assert "unknown_status" not in by_name
        assert len(items) == 3
        assert by_name["Threads_connected"].category is StatusCategory.CONNECTION
        assert by_name["Threads_connected"].is_readonly is True
        assert by_name["Questions"].value == 9000
        assert by_name["Uptime"].unit == "seconds"

    @pytest.mark.asyncio
    async def test_list_performance_metrics_category_filter(self, async_introspector):
        statuses = {"Threads_connected": "10", "Questions": "9000", "Uptime": "3600"}
        with patch.object(async_introspector, "_show_status", new=AsyncMock(return_value=statuses)):
            items = await async_introspector.list_performance_metrics(StatusCategory.PERFORMANCE)

        assert {item.name for item in items} == {"Questions", "Uptime"}
        assert all(item.category is StatusCategory.PERFORMANCE for item in items)

    @pytest.mark.asyncio
    async def test_get_connection_info(self, async_introspector):
        with patch.object(
            async_introspector,
            "_show_status",
            new=AsyncMock(return_value={"Threads_connected": "42"}),
        ), patch.object(
            async_introspector,
            "_show_variables",
            new=AsyncMock(return_value={"max_connections": "151"}),
        ):
            info = await async_introspector.get_connection_info()

        assert isinstance(info, ConnectionInfo)
        assert info.active_count == 42
        assert info.max_connections == 151

    @pytest.mark.asyncio
    async def test_get_connection_info_max_zero_is_none(self, async_introspector):
        with patch.object(
            async_introspector,
            "_show_status",
            new=AsyncMock(return_value={"Threads_connected": "3"}),
        ), patch.object(
            async_introspector,
            "_show_variables",
            new=AsyncMock(return_value={"max_connections": "0"}),
        ):
            info = await async_introspector.get_connection_info()
        assert info.active_count == 3
        assert info.max_connections is None

    @pytest.mark.asyncio
    async def test_get_connection_info_defaults(self, async_introspector):
        with patch.object(
            async_introspector, "_show_status", new=AsyncMock(return_value={})
        ), patch.object(async_introspector, "_show_variables", new=AsyncMock(return_value={})):
            info = await async_introspector.get_connection_info()
        assert info.active_count == 0
        assert info.max_connections is None

    @pytest.mark.asyncio
    async def test_get_storage_info(self, async_introspector):
        row = {"data_bytes": "1000", "index_bytes": "250"}
        with patch.object(
            async_introspector, "_execute_query_dict", new=AsyncMock(return_value=[row])
        ):
            info = await async_introspector.get_storage_info()

        assert isinstance(info, StorageInfo)
        assert info.data_size_bytes == 1000
        assert info.index_size_bytes == 250
        assert info.total_size_bytes == 1250

    @pytest.mark.asyncio
    @pytest.mark.parametrize("outcome", [[], RuntimeError("boom")])
    async def test_get_storage_info_fallback(self, async_introspector, outcome):
        effect = outcome if isinstance(outcome, Exception) else None
        query = AsyncMock(side_effect=effect, return_value=outcome)
        with patch.object(async_introspector, "_execute_query_dict", new=query):
            info = await async_introspector.get_storage_info()
        assert info == StorageInfo()

    @pytest.mark.asyncio
    async def test_list_databases(self, async_introspector):
        rows = [
            {"schema_name": "app", "size_bytes": "1024", "table_count": "12", "view_count": "2"},
            {"schema_name": "empty"},
        ]
        with patch.object(
            async_introspector, "_execute_query_dict", new=AsyncMock(return_value=rows)
        ):
            dbs = await async_introspector.list_databases()

        assert all(isinstance(db, DatabaseBriefInfo) for db in dbs)
        assert dbs[0].name == "app"
        assert dbs[0].size_bytes == 1024
        assert dbs[0].table_count == 12
        assert dbs[0].view_count == 2
        assert dbs[1].name == "empty"
        assert dbs[1].size_bytes is None
        assert dbs[1].table_count == 0
        assert dbs[1].view_count == 0

    @pytest.mark.asyncio
    async def test_list_databases_error(self, async_introspector):
        query = AsyncMock(side_effect=RuntimeError("boom"))
        with patch.object(async_introspector, "_execute_query_dict", new=query):
            assert await async_introspector.list_databases() == []

    @pytest.mark.asyncio
    async def test_list_users(self, async_introspector):
        rows = [
            {"user": "root", "host": "localhost", "super_priv": "Y"},
            {"user": "app", "host": "%", "super_priv": "N"},
            {"user": "guest"},
        ]
        with patch.object(
            async_introspector, "_execute_query_dict", new=AsyncMock(return_value=rows)
        ):
            users = await async_introspector.list_users()

        assert all(isinstance(user, UserInfo) for user in users)
        assert users[0].name == "root"
        assert users[0].host == "localhost"
        assert users[0].is_superuser is True
        assert users[1].is_superuser is False
        assert users[2].host is None
        assert users[2].is_superuser is False

    @pytest.mark.asyncio
    async def test_list_users_error(self, async_introspector):
        query = AsyncMock(side_effect=RuntimeError("boom"))
        with patch.object(async_introspector, "_execute_query_dict", new=query):
            assert await async_introspector.list_users() == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "have_ssl, expected", [("YES", True), ("yes", True), ("NO", False), ("", False)]
    )
    async def test_get_session_info_ssl(self, async_introspector, have_ssl, expected):
        row = {
            "cur_user": "root@localhost",
            "cur_db": "app",
            "host": "localhost",
            "have_ssl": have_ssl,
        }
        with patch.object(
            async_introspector, "_execute_query_dict", new=AsyncMock(return_value=[row])
        ):
            info = await async_introspector.get_session_info()

        assert isinstance(info, SessionInfo)
        assert info.user == "root@localhost"
        assert info.database == "app"
        assert info.host == "localhost"
        assert info.ssl_enabled is expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize("outcome", [[], RuntimeError("boom")])
    async def test_get_session_info_fallback(self, async_introspector, outcome):
        effect = outcome if isinstance(outcome, Exception) else None
        query = AsyncMock(side_effect=effect, return_value=outcome)
        with patch.object(async_introspector, "_execute_query_dict", new=query):
            assert await async_introspector.get_session_info() == SessionInfo()

    @pytest.mark.asyncio
    async def test_get_version_string(self, async_introspector):
        query = AsyncMock(return_value=[("11.4.0-MariaDB",)])
        with patch.object(async_introspector, "_execute_query", new=query):
            assert await async_introspector._get_version_string() == "11.4.0-MariaDB"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("outcome", [[], RuntimeError("boom")])
    async def test_get_version_string_unknown(self, async_introspector, outcome):
        effect = outcome if isinstance(outcome, Exception) else None
        query = AsyncMock(side_effect=effect, return_value=outcome)
        with patch.object(async_introspector, "_execute_query", new=query):
            assert await async_introspector._get_version_string() == "Unknown"


class TestAsyncBinaryAndReplicationWithMocks:
    """The async row questions are skipped/asked by the same variable rules."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("log_bin", ["OFF", "0", "false", ""])
    async def test_binary_log_off_does_not_query_master_status(self, async_introspector, log_bin):
        variables = {"log_bin": log_bin, "binlog_format": "ROW"}
        query = AsyncMock(return_value=[])
        with patch.object(
            async_introspector, "_show_variables", new=AsyncMock(return_value=variables)
        ), patch.object(async_introspector, "_execute_query_dict", new=query):
            info = await async_introspector.get_binary_log_info()

        query.assert_not_awaited()
        assert info.log_enabled is False
        assert info.current_log_file is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("log_bin", ["ON", "1", "true"])
    async def test_binary_log_on_queries_master_status(self, async_introspector, log_bin):
        variables = {"log_bin": log_bin, "binlog_format": "ROW"}
        with patch.object(
            async_introspector, "_show_variables", new=AsyncMock(return_value=variables)
        ), patch.object(
            async_introspector,
            "_execute_query_dict",
            new=AsyncMock(return_value=[_SAMPLE_MASTER_ROW]),
        ):
            info = await async_introspector.get_binary_log_info()

        assert info.log_enabled is True
        assert info.current_log_file == "mysql-bin.000042"
        assert info.current_log_position == 1200
        assert info.binlog_do_db == ["app", "reporting"]

    @pytest.mark.asyncio
    async def test_replication_not_a_replica(self, async_introspector):
        variables = {"server_id": "10", "log_slave_updates": "ON"}
        with patch.object(
            async_introspector, "_show_variables", new=AsyncMock(return_value=variables)
        ), patch.object(async_introspector, "_execute_query_dict", new=AsyncMock(return_value=[])):
            info = await async_introspector.get_replication_info()

        assert info.server_id == 10
        assert info.log_slave_updates is True
        assert info.is_replica is False

    @pytest.mark.asyncio
    async def test_replication_row(self, async_introspector):
        with patch.object(
            async_introspector, "_show_variables", new=AsyncMock(return_value={"server_id": "10"})
        ), patch.object(
            async_introspector,
            "_execute_query_dict",
            new=AsyncMock(return_value=[_SAMPLE_SLAVE_ROW]),
        ):
            info = await async_introspector.get_replication_info()
        assert info.is_replica is True
        assert info.master_host == "10.0.0.5"
        assert info.master_port == 3306

    @pytest.mark.asyncio
    async def test_replication_query_error_keeps_identity(self, async_introspector):
        with patch.object(
            async_introspector, "_show_variables", new=AsyncMock(return_value={"server_id": "10"})
        ), patch.object(
            async_introspector,
            "_execute_query_dict",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            info = await async_introspector.get_replication_info()
        assert info.server_id == 10
        assert info.is_replica is None


class TestAsyncGetOverview:
    """The async overview composes every async reader."""

    @pytest.mark.asyncio
    async def test_get_overview_composes_all_parts(self, async_introspector):
        parts = {
            "_get_version_string": "11.4.0-MariaDB",
            "get_session_info": SessionInfo(user="root"),
            "list_configuration": [StatusItem("a", 1, StatusCategory.CONFIGURATION)],
            "list_performance_metrics": [StatusItem("b", 2, StatusCategory.PERFORMANCE)],
            "get_connection_info": ConnectionInfo(active_count=5),
            "get_storage_info": StorageInfo(total_size_bytes=10),
            "list_databases": [DatabaseBriefInfo(name="app")],
            "list_users": [UserInfo(name="root")],
            "get_binary_log_info": MariaDBBinaryLogInfo(log_enabled=False),
            "get_replication_info": MariaDBReplicationInfo(server_id=1, is_replica=False),
        }
        patches = [
            patch.object(async_introspector, name, new=AsyncMock(return_value=value))
            for name, value in parts.items()
        ]
        for item in patches:
            item.start()
        try:
            overview = await async_introspector.get_overview()
        finally:
            for item in patches:
                item.stop()

        assert isinstance(overview, MariaDBServerOverview)
        assert overview.server_version == "11.4.0-MariaDB"
        assert overview.server_vendor == "MariaDB"
        assert overview.session is parts["get_session_info"]
        assert overview.configuration == (
            parts["list_configuration"] + parts["list_performance_metrics"]
        )
        assert overview.connections is parts["get_connection_info"]
        assert overview.storage is parts["get_storage_info"]
        assert overview.databases == parts["list_databases"]
        assert overview.users == parts["list_users"]
        assert overview.binary_log.log_enabled is False
        assert overview.replication.is_replica is False
