# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/mariadb/status_families/test_mariadb_status_families.py
"""Offline assertions on MariaDB's own status families and storage slots.

Nothing here talks to a server. Two things are pinned:

* the SQL the two new SHOW nodes render -- ``SHOW MASTER STATUS`` and
  ``SHOW SLAVE STATUS`` are what MariaDB receives when the binlog and
  replication families are asked, and what a node renders is what the
  server sees;
* the parsing -- what a canned row becomes, and what an *empty* or
  unaskable answer becomes. The three-state rule (not asked / asked with
  nothing / asked with an answer) is the reason a family can answer "not a
  replica" without confusing it with "unknown".

Where a collector is exercised rather than a parser, a stub connection
replays canned answers by (statement, parameters); the statements above
that boundary -- the nodes, the parsers, the overview subclass -- are the
production path itself.
"""

import inspect
from dataclasses import fields as dataclass_fields

from rhosocial.activerecord.backend.introspection import SequenceInfo as CoreSequenceInfo
from rhosocial.activerecord.backend.introspection.status import ServerOverview
from rhosocial.activerecord.backend.introspection.types import (
    IntrospectionTableInfo,
    TableType,
)

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.show import (
    ShowMasterStatusStatement,
    ShowSlaveStatusStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.introspection import (
    AsyncMariaDBStatusIntrospector,
)
from rhosocial.activerecord.backend.impl.mariadb.introspection import (
    SequenceInfo as MariaDBSequenceInfo,
)
from rhosocial.activerecord.backend.impl.mariadb.introspection import MariaDBStatusIntrospector
from rhosocial.activerecord.backend.impl.mariadb.introspection.status_types import (
    MariaDBBinaryLogInfo,
    MariaDBReplicationInfo,
    MariaDBServerOverview,
)


def _dialect() -> MariaDBDialect:
    return MariaDBDialect(version=(11, 4, 0))


class _ScriptedBackend:
    """A backend whose connection replays canned answers.

    Each answer is keyed by the (statement, parameters) pair the introspector
    renders, which is the exact tuple an executor would send. An ask with no
    scripted answer yields no rows -- the live behaviour of a feature the
    connected server does not have -- and is remembered in ``seen``.
    """

    def __init__(self, scripts):
        self.dialect = _dialect()
        self._scripts = scripts
        self.seen = []
        self._cursor_rows = []
        self._connection = self

    def cursor(self):
        return self

    def execute(self, sql, params=()):
        self.seen.append(sql)
        for scripted_sql, scripted_params, rows in self._scripts:
            if sql == scripted_sql and params == scripted_params:
                self._cursor_rows = rows
                return
        self._cursor_rows = []

    def fetchall(self):
        return self._cursor_rows

    @property
    def description(self):
        return None

    def close(self):
        return None


def _variable_script(name, value):
    """The answer ``SHOW VARIABLES LIKE '<name>'`` returns for one variable.

    MariaDB answers the name it was asked for, in that casing, so the stub
    hands back one (Name, Value) row.
    """
    return ("SHOW VARIABLES LIKE %s", (name,), [(name, value)])


# ---------------------------------------------------------------------------
# The statements
# ---------------------------------------------------------------------------


class TestShowReplicationStatements:
    """The two SHOW nodes the families run render MariaDB's own commands."""

    def test_show_master_status(self):
        assert ShowMasterStatusStatement(_dialect()).to_sql() == ("SHOW MASTER STATUS", ())

    def test_show_slave_status(self):
        assert ShowSlaveStatusStatement(_dialect()).to_sql() == ("SHOW SLAVE STATUS", ())

    def test_no_parameters_are_bound(self):
        """No bind values on either command: nothing is interpolated."""
        for expr in (ShowMasterStatusStatement(_dialect()), ShowSlaveStatusStatement(_dialect())):
            _, params = expr.to_sql()
            assert params == ()


# ---------------------------------------------------------------------------
# The overview subclass
# ---------------------------------------------------------------------------


class TestMariaDBServerOverview:
    """The overview is core's shape plus this engine's two families."""

    def test_is_a_server_overview_subclass(self):
        assert issubclass(MariaDBServerOverview, ServerOverview)

    def test_core_slots_survive_and_the_own_ones_start_empty(self):
        overview = MariaDBServerOverview(server_version="11.4.0", server_vendor="MariaDB")
        for slot in (
            "server_version",
            "server_vendor",
            "configuration",
            "performance",
            "connections",
            "storage",
            "databases",
            "users",
        ):
            assert hasattr(overview, slot)
        assert overview.binary_log is None
        assert overview.replication is None

    def test_to_dict_serializes_the_engine_families(self):
        """``to_dict()`` is field-driven, so the two families need no re-declaration.

        A consumer reading the overview as JSON sees the binlog and
        replication families beside the core ones -- which is the point of
        rules §5: an engine's facts travel on its own class, and the core
        shape does not widen to hold them.
        """
        overview = MariaDBServerOverview(
            server_version="11.4.0",
            server_vendor="MariaDB",
            binary_log=MariaDBBinaryLogInfo(log_enabled=True, log_format="ROW"),
            replication=MariaDBReplicationInfo(server_id=42),
        )
        payload = overview.to_dict()
        assert payload["binary_log"]["log_enabled"] is True
        assert payload["binary_log"]["log_format"] == "ROW"
        assert payload["replication"]["server_id"] == 42
        # A switch the server did not answer stays None rather than
        # becoming False on the way out.
        assert payload["replication"]["is_replica"] is None

    def test_get_overview_signature_is_the_core_one(self):
        """The covariant return keeps the core signature -- LSP intact."""
        signature = inspect.signature(MariaDBStatusIntrospector.get_overview)
        assert list(signature.parameters) == ["self"]
        assert issubclass(MariaDBServerOverview, ServerOverview)

    def test_replication_carries_no_galera_family(self):
        """Galera's cluster state is not a field the connected server can answer.

        The ``wsrep_*`` variables exist only on a Galera build; claiming a
        slot for them would assert a fact a stock server cannot report.
        Keeping the field list clear is what keeps it so.
        """
        names = {f.name for f in dataclass_fields(MariaDBReplicationInfo)}
        assert names.isdisjoint({"wsrep_cluster_name", "cluster_size", "galera", "cluster_status"})


# ---------------------------------------------------------------------------
# The binlog family
# ---------------------------------------------------------------------------


class TestBinaryLogParsing:
    """What canned rows become, and what an empty answer becomes."""

    def test_log_on_reports_the_row_it_is_writing(self):
        introspector = MariaDBStatusIntrospector(_ScriptedBackend([]))
        info = introspector.parse_binary_log_info(
            {
                "log_bin": "ON",
                "binlog_format": "ROW",
                "gtid_binlog_pos": "0-1-5",
                "gtid_strict_mode": "OFF",
            },
            [
                {
                    "file": "binlog.000001",
                    "position": "1234",
                    "binlog_do_db": "app,logs",
                    "binlog_ignore_db": "sys",
                    "executed_gtid_set": "0-1-5",
                }
            ],
        )
        assert info.log_enabled is True
        assert info.log_format == "ROW"
        assert info.current_log_file == "binlog.000001"
        assert info.current_log_position == 1234
        assert info.binlog_do_db == ["app", "logs"]
        assert info.binlog_ignore_db == ["sys"]
        assert info.executed_gtid_set == "0-1-5"
        assert info.gtid_binlog_pos == "0-1-5"
        assert info.gtid_strict_mode is False

    def test_log_off_answers_the_variables_and_no_row(self):
        """With the log off MariaDB answers the row question with an empty set.

        The variables still answer -- the format and the switches are real
        facts -- while the current file and position stay ``None``: the
        server said nothing about them, and nothing is zeroed.
        """
        introspector = MariaDBStatusIntrospector(_ScriptedBackend([]))
        info = introspector.parse_binary_log_info(
            {
                "log_bin": "OFF",
                "binlog_format": "MIXED",
                "gtid_binlog_pos": "0-1-1",
                "gtid_strict_mode": "ON",
            },
            [],
        )
        assert info.log_enabled is False
        assert info.log_format == "MIXED"
        assert info.current_log_file is None
        assert info.current_log_position is None
        assert info.executed_gtid_set is None
        assert info.binlog_do_db == []
        assert info.binlog_ignore_db == []

    def test_empty_filter_is_no_filter(self):
        introspector = MariaDBStatusIntrospector(_ScriptedBackend([]))
        info = introspector.parse_binary_log_info(
            {"log_bin": "ON"},
            [
                {
                    "file": "b.1",
                    "position": 1,
                    "binlog_do_db": "",
                    "binlog_ignore_db": "",
                }
            ],
        )
        assert info.binlog_do_db == []
        assert info.binlog_ignore_db == []

    def test_not_reported_stays_none(self):
        """An unanswered variable is None, never False."""
        introspector = MariaDBStatusIntrospector(_ScriptedBackend([]))
        info = introspector.parse_binary_log_info({"binlog_format": "ROW"}, [])
        assert info.log_enabled is None
        assert info.gtid_strict_mode is None
        assert info.gtid_binlog_pos is None

    def test_collector_reads_the_switch_before_spending_the_round_trip(self):
        """With ``log_bin`` answered OFF, ``SHOW MASTER STATUS`` is not sent.

        The empty set it would return carries no fact the variable did not
        already say, so the question is not asked.
        """
        backend = _ScriptedBackend(
            [
                _variable_script("log_bin", "OFF"),
                _variable_script("binlog_format", "ROW"),
                _variable_script("gtid_binlog_pos", "0-1-1"),
                _variable_script("gtid_strict_mode", "ON"),
            ]
        )
        introspector = MariaDBStatusIntrospector(backend)
        info = introspector.get_binary_log_info()
        assert info.log_enabled is False
        assert info.log_format == "ROW"
        assert not any("MASTER STATUS" in sql for sql in backend.seen)


# ---------------------------------------------------------------------------
# The replication family
# ---------------------------------------------------------------------------


class TestReplicationParsing:
    """The replica side, its absence, and the question that cannot be asked."""

    def test_replica_row_fills_the_connection(self):
        introspector = MariaDBStatusIntrospector(_ScriptedBackend([]))
        info = introspector.parse_replication_info(
            {"server_id": "7", "log_slave_updates": "ON"},
            [
                {
                    "slave_io_running": "Yes",
                    "slave_sql_running": "Yes",
                    "master_host": "primary.local",
                    "master_port": "3306",
                    "master_user": "replicator",
                    "seconds_behind_master": "12",
                    "master_log_file": "binlog.000009",
                    "read_master_log_pos": "99",
                    "relay_master_log_file": "binlog.000009",
                    "slave_io_state": "Waiting for master to send event",
                    "using_gtid": "1",
                    "gtid_io_pos": "0-2-8",
                }
            ],
        )
        assert info.is_replica is True
        assert info.server_id == 7
        assert info.log_slave_updates is True
        assert info.slave_io_running == "Yes"
        assert info.slave_sql_running == "Yes"
        assert info.master_host == "primary.local"
        assert info.master_port == 3306
        assert info.master_user == "replicator"
        assert info.seconds_behind_master == 12
        assert info.master_log_file == "binlog.000009"
        assert info.read_master_log_pos == 99
        assert info.relay_master_log_file == "binlog.000009"
        assert info.slave_io_state == "Waiting for master to send event"
        assert info.using_gtid == "1"
        assert info.gtid_io_pos == "0-2-8"

    def test_empty_answer_is_not_a_replica(self):
        """``SHOW SLAVE STATUS`` with no row means "pulls from nothing"."""
        introspector = MariaDBStatusIntrospector(_ScriptedBackend([]))
        info = introspector.parse_replication_info(
            {"server_id": "7", "log_slave_updates": "OFF"}, []
        )
        assert info.is_replica is False
        assert info.master_host is None
        assert info.server_id == 7

    def test_unaskable_stays_none(self):
        """A question that raised is not an answer of "not a replica"."""
        introspector = MariaDBStatusIntrospector(_ScriptedBackend([]))
        info = introspector.parse_replication_info(
            {"server_id": "7", "log_slave_updates": "OFF"}, None
        )
        assert info.is_replica is None
        assert info.server_id == 7

    def test_server_id_zero_is_kept(self):
        """``0`` is a valid identity -- no identity -- not a missing value."""
        introspector = MariaDBStatusIntrospector(_ScriptedBackend([]))
        info = introspector.parse_replication_info({"server_id": "0"}, [])
        assert info.server_id == 0

    def test_null_columns_are_not_zeroed(self):
        """NULL from the server reads as ``None``, per the family's rule."""
        introspector = MariaDBStatusIntrospector(_ScriptedBackend([]))
        info = introspector.parse_replication_info(
            {"server_id": "1"},
            [{"slave_io_running": "No", "seconds_behind_master": None}],
        )
        assert info.is_replica is True
        assert info.seconds_behind_master is None
        assert info.master_port is None


# ---------------------------------------------------------------------------
# Sync/async parity
# ---------------------------------------------------------------------------


class TestSyncAsyncParity:
    """The families answer through the same parsers and the same statements."""

    def test_async_collectors_are_coroutines(self):
        for name in ("get_overview", "get_binary_log_info", "get_replication_info"):
            assert inspect.iscoroutinefunction(getattr(AsyncMariaDBStatusIntrospector, name))

    def test_sync_collectors_are_not_coroutines(self):
        for name in ("get_overview", "get_binary_log_info", "get_replication_info"):
            assert not inspect.iscoroutinefunction(getattr(MariaDBStatusIntrospector, name))

    def test_async_parsers_are_the_same_functions(self):
        """The parsing is the shared half, not a second implementation."""
        for name in ("parse_binary_log_info", "parse_replication_info"):
            assert getattr(MariaDBStatusIntrospector, name) is getattr(
                AsyncMariaDBStatusIntrospector, name
            )


# ---------------------------------------------------------------------------
# The per-table storage slots
# ---------------------------------------------------------------------------


class TestStorageSlots:
    """The narrow storage slots are filled, and absence is not a zero."""

    @staticmethod
    def _parser():
        """The table-list parser with a default schema, and nothing else.

        ``parse_tables`` is pure Python: a backend is not part of the answer,
        so the parser is driven directly rather than through a database.
        """
        from rhosocial.activerecord.backend.impl.mariadb.introspection.introspector import (
            MariaDBIntrospectorMixin,
        )

        class Parser(MariaDBIntrospectorMixin):
            @property
            def default_schema(self):
                return "app"

        return Parser()

    def test_row_plus_index_shape_fills_all_three_slots(self):
        tables = self._parser().parse_tables(
            [
                {
                    "TABLE_NAME": "users",
                    "TABLE_TYPE": "BASE TABLE",
                    "TABLE_ROWS": 12,
                    "DATA_LENGTH": 16384,
                    "INDEX_LENGTH": 4096,
                }
            ],
            schema=None,
        )
        table = tables[0]
        assert isinstance(table, IntrospectionTableInfo)
        assert table.name == "users"
        assert table.size_bytes == 16384 + 4096
        assert table.data_size_bytes == 16384
        assert table.index_size_bytes == 4096

    def test_view_row_reports_neither_and_stays_none(self):
        """A view has no storage: the NULLs stay None, and the sum is not zero."""
        tables = self._parser().parse_tables(
            [
                {
                    "TABLE_NAME": "user_view",
                    "TABLE_TYPE": "VIEW",
                    "TABLE_ROWS": None,
                    "DATA_LENGTH": None,
                    "INDEX_LENGTH": None,
                }
            ],
            schema=None,
        )
        table = tables[0]
        assert table.table_type == TableType.VIEW
        assert table.size_bytes is None
        assert table.data_size_bytes is None
        assert table.index_size_bytes is None

    def test_one_side_reported_sums_only_what_was_reported(self):
        tables = self._parser().parse_tables(
            [
                {
                    "TABLE_NAME": "half",
                    "TABLE_TYPE": "BASE TABLE",
                    "DATA_LENGTH": 2048,
                    "INDEX_LENGTH": None,
                }
            ],
            schema=None,
        )
        table = tables[0]
        assert table.data_size_bytes == 2048
        assert table.index_size_bytes is None
        assert table.size_bytes == 2048


# ---------------------------------------------------------------------------
# The sequence projection
# ---------------------------------------------------------------------------


class TestSequenceProjection:
    """MariaDB's sequence projects onto core's common minimum."""

    def test_projection_maps_the_answerable_slots(self):
        sequence = MariaDBSequenceInfo(
            name="customer_ids",
            schema="app",
            start_value=1000,
            minimum_value=1,
            maximum_value=10**9,
            increment=1,
            cycle=True,
            cache_size=None,
            data_type="bigint",
        )
        projected = sequence.to_core()
        assert isinstance(projected, CoreSequenceInfo)
        assert projected.name == "customer_ids"
        assert projected.schema == "app"
        assert projected.data_type == "bigint"
        assert projected.start_value == 1000
        assert projected.minimum_value == 1
        assert projected.maximum_value == 10**9
        assert projected.increment == 1
        assert projected.cycle is True
        assert projected.cache_size is None

    def test_projection_leaves_the_unreadable_slot_none(self):
        """``last_value`` has no view on MariaDB, so it is not invented."""
        projected = MariaDBSequenceInfo(name="seq", schema="app").to_core()
        assert projected.last_value is None
        assert projected.start_value is None
        assert projected.cycle is None


# ---------------------------------------------------------------------------
# The CLI rides the families in the same change (rules §6)
# ---------------------------------------------------------------------------


class TestStatusCliTypes:
    """The two families are offered by the parser and serialize untouched."""

    def test_new_types_are_registered(self):
        from rhosocial.activerecord.backend.impl.mariadb.cli.status import STATUS_TYPES

        assert "binlog" in STATUS_TYPES
        assert "replication" in STATUS_TYPES

    def test_types_are_accepted_by_the_parser(self):
        """An offered type is a parsed type: no handler-only family."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        for status_type in ("binlog", "replication"):
            args = parse_args(["status", status_type, "--database", "db"])
            assert args.type == status_type
            assert args.is_async is False

    def test_types_are_rejected_when_not_a_type(self):
        """``help`` (or any other word) stays an argparse refusal, exit 2."""
        import pytest as _pytest

        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with _pytest.raises(SystemExit) as refusal:
            parse_args(["status", "galera", "--database", "db"])
        assert refusal.value.code == 2

    def test_new_types_serialize_without_a_change(self):
        """``_serialize_for_output`` recurses whatever module a type came from.

        The two families are DB-free here: the collector produced them
        from canned rows above, and the JSON path is the generic
        dataclass walk -- a new module needs no name in it.
        """
        from rhosocial.activerecord.backend.impl.mariadb.cli.status import (
            _serialize_for_output,
        )

        overview = MariaDBServerOverview(
            server_version="11.4.0",
            server_vendor="MariaDB",
            binary_log=MariaDBBinaryLogInfo(log_enabled=True, log_format="ROW"),
            replication=MariaDBReplicationInfo(server_id=1, is_replica=False),
        )
        payload = _serialize_for_output(overview)
        assert payload["binary_log"]["log_enabled"] is True
        assert payload["binary_log"]["log_format"] == "ROW"
        assert payload["replication"]["server_id"] == 1
        assert payload["replication"]["is_replica"] is False
