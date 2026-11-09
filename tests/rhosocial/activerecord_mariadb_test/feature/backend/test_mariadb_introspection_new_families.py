# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_introspection_new_families.py
"""Unit and parser tests for partitions, routines, constraints and identity.

Everything here runs without a server: the parsers are pure Python over
literal rows, and the introspectors are driven through a recording executor.
The SQL each introspector sends is pinned separately in
``test_mariadb_introspection_queries.py``; this file is about what the rows
become once they are read, which is the half a live-only test cannot cover on
a machine without MariaDB.
"""

from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.introspection.introspector import (
    AsyncMariaDBIntrospector,
    MariaDBIntrospector,
    MariaDBIntrospectorMixin,
)
from rhosocial.activerecord.backend.impl.mariadb.introspection.types import (
    MariaDBConstraintInfo,
    MariaDBPartitionInfo,
    MariaDBRoutineInfo,
    MariaDBRoutineParameterInfo,
)


class _FakeBackend:
    """The two facts a parser or introspector reads from its backend."""

    def __init__(self, version=(11, 4, 0), database="app"):
        self.dialect = MariaDBDialect(version)
        self.config = SimpleNamespace(database=database)


class _RecordingExecutor:
    """A synchronous executor that returns canned rows and records the SQL."""

    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        return self.rows


class _AsyncRecordingExecutor(_RecordingExecutor):
    """The awaited twin: same rows, same call log."""

    async def execute(self, sql, params):
        return _RecordingExecutor.execute(self, sql, params)


def _mixin(version=(11, 4, 0), database="app"):
    """A bare mixin with just enough backend for the parse methods."""
    mixin = MariaDBIntrospectorMixin()
    mixin._backend = _FakeBackend(version, database)
    return mixin


# ---------------------------------------------------------------------------
# Partitions
# ---------------------------------------------------------------------------


class TestParsePartitions:
    def test_range_partition_keeps_boundary_and_size(self):
        rows = [
            {
                "PARTITION_NAME": "p2026_01",
                "PARTITION_METHOD": "RANGE",
                "PARTITION_EXPRESSION": "YEAR(created_at)",
                "PARTITION_DESCRIPTION": "2026",
                "PARTITION_ORDINAL_POSITION": 1,
                "TABLE_ROWS": 120,
                "DATA_LENGTH": 4096,
                "INDEX_LENGTH": 1024,
                "PARTITION_COMMENT": "january",
            }
        ]
        result = _mixin().parse_partitions(rows, "orders", "app")

        assert len(result) == 1
        assert result[0] == MariaDBPartitionInfo(
            schema="app",
            table_name="orders",
            partition_name="p2026_01",
            partition_method="RANGE",
            partition_expression="YEAR(created_at)",
            partition_description="2026",
            partition_ordinal_position=1,
            table_rows=120,
            data_length=4096,
            index_length=1024,
            partition_comment="january",
        )

    def test_subpartition_row_is_identified(self):
        rows = [
            {
                "PARTITION_NAME": "p0",
                "SUBPARTITION_NAME": "sp1",
                "PARTITION_METHOD": "RANGE",
                "SUBPARTITION_METHOD": "HASH",
                "PARTITION_ORDINAL_POSITION": 1,
                "SUBPARTITION_ORDINAL_POSITION": 2,
            }
        ]
        info = _mixin().parse_partitions(rows, "orders", "app")[0]

        assert info.is_subpartition is True
        assert info.subpartition_method == "HASH"
        assert info.subpartition_ordinal_position == 2

    def test_total_length_is_none_when_neither_side_is_reported(self):
        info = MariaDBPartitionInfo(schema="app", table_name="t", partition_name="p0")
        assert info.total_length is None

    def test_total_length_adds_the_reported_side_only(self):
        info = MariaDBPartitionInfo(
            schema="app", table_name="t", partition_name="p0", data_length=10
        )
        assert info.total_length == 10

    def test_missing_catalog_values_stay_none(self):
        """A server that reports no size must not look like a zero-byte partition."""
        info = _mixin().parse_partitions(
            [{"PARTITION_NAME": "p0", "PARTITION_METHOD": "LIST"}], "orders", "app"
        )[0]
        assert info.table_rows is None
        assert info.data_length is None
        assert info.index_length is None


# ---------------------------------------------------------------------------
# Routines
# ---------------------------------------------------------------------------


def _routine_row(**overrides):
    """One joined ROUTINES/PARAMETERS row with the usual catalog defaults."""
    row = {
        "ROUTINE_SCHEMA": "app",
        "ROUTINE_NAME": "app_cleanup",
        "ROUTINE_TYPE": "PROCEDURE",
        "ROUTINE_DATA_TYPE": "",
        "ROUTINE_DTD_IDENTIFIER": "",
        "ROUTINE_BODY": "SQL",
        "EXTERNAL_LANGUAGE": None,
        "IS_DETERMINISTIC": "NO",
        "SQL_DATA_ACCESS": "MODIFIES SQL DATA",
        "SECURITY_TYPE": "DEFINER",
        "ROUTINE_COMMENT": "cleanup",
        "DEFINER": "root@localhost",
        "CREATED": "2026-01-01 00:00:00",
        "LAST_ALTERED": "2026-01-02 00:00:00",
        "PARAMETER_ORDINAL_POSITION": None,
        "PARAMETER_MODE": None,
        "PARAMETER_NAME": None,
        "PARAMETER_DATA_TYPE": None,
        "PARAMETER_DTD_IDENTIFIER": None,
    }
    row.update(overrides)
    return row


class TestParseRoutines:
    def test_parameters_are_grouped_under_the_routine(self):
        rows = [
            _routine_row(PARAMETER_ORDINAL_POSITION=1, PARAMETER_MODE="IN",
                         PARAMETER_NAME="month", PARAMETER_DATA_TYPE="varchar",
                         PARAMETER_DTD_IDENTIFIER="varchar(7)"),
            _routine_row(PARAMETER_ORDINAL_POSITION=2, PARAMETER_MODE="OUT",
                         PARAMETER_NAME="deleted", PARAMETER_DATA_TYPE="int",
                         PARAMETER_DTD_IDENTIFIER="int"),
        ]
        info = _mixin().parse_routines(rows, "app")[0]

        assert info.name == "app_cleanup"
        assert info.kind == "PROCEDURE"
        assert [p.ordinal_position for p in info.parameters] == [1, 2]
        assert info.parameters[0].name == "month"
        assert info.parameters[0].data_type_full == "varchar(7)"
        assert info.parameters[1].mode == "OUT"

    def test_a_function_return_row_is_not_a_parameter(self):
        """``PARAMETERS`` reports the return value at ordinal 0; it is not an arg."""
        rows = [
            _routine_row(PARAMETER_ORDINAL_POSITION=0, PARAMETER_MODE=None,
                         PARAMETER_NAME=None, PARAMETER_DATA_TYPE="int",
                         PARAMETER_DTD_IDENTIFIER="int"),
            _routine_row(PARAMETER_ORDINAL_POSITION=1, PARAMETER_MODE="IN",
                         PARAMETER_NAME="x", PARAMETER_DATA_TYPE="int",
                         PARAMETER_DTD_IDENTIFIER="int"),
        ]
        info = _mixin().parse_routines(rows, "app")[0]

        assert len(info.parameters) == 1
        assert info.parameters[0].ordinal_position == 1

    def test_function_and_procedure_sharing_a_name_stay_separate(self):
        """The grouping key includes the kind, not just the name."""
        rows = [
            _routine_row(ROUTINE_NAME="app_helper", ROUTINE_TYPE="PROCEDURE"),
            _routine_row(
                ROUTINE_NAME="app_helper",
                ROUTINE_TYPE="FUNCTION",
                ROUTINE_DTD_IDENTIFIER="int",
                IS_DETERMINISTIC="YES",
            ),
        ]
        routines = _mixin().parse_routines(rows, "app")

        assert [r.kind for r in routines] == ["PROCEDURE", "FUNCTION"]
        assert routines[0].return_type is None
        assert routines[1].return_type == "int"
        assert routines[1].deterministic is True

    def test_language_falls_back_to_the_routine_body(self):
        info = _mixin().parse_routines([_routine_row()], "app")[0]
        assert info.language == "SQL"

    def test_external_language_wins_when_present(self):
        info = _mixin().parse_routines(
            [_routine_row(EXTERNAL_LANGUAGE="EXTERNAL")], "app"
        )[0]
        assert info.language == "EXTERNAL"

    def test_get_style_lookup_narrows_on_kind(self):
        rows = [
            _routine_row(ROUTINE_NAME="app_helper", ROUTINE_TYPE="PROCEDURE"),
            _routine_row(
                ROUTINE_NAME="app_helper",
                ROUTINE_TYPE="FUNCTION",
                ROUTINE_DTD_IDENTIFIER="int",
            ),
        ]
        mixin = _mixin()

        assert mixin.parse_routine_info(rows, "app_helper", "app").kind == "PROCEDURE"
        result = mixin.parse_routine_info(
            rows, "app_helper", "app", kind="FUNCTION"
        )
        assert result is not None
        assert result.return_type == "int"

    def test_absent_routine_is_none(self):
        assert _mixin().parse_routine_info([], "missing", "app") is None

    def test_unknown_boolean_spelling_is_false(self):
        """Anything that is not the known affirmative is not a yes."""
        info = _mixin().parse_routines(
            [_routine_row(IS_DETERMINISTIC="MAYBE")], "app"
        )[0]
        assert info.deterministic is False

    def test_unreported_boolean_is_none(self):
        info = _mixin().parse_routines(
            [_routine_row(IS_DETERMINISTIC=None)], "app"
        )[0]
        assert info.deterministic is None

    def test_timestamps_are_rendered_as_text(self):
        from datetime import datetime

        row = _routine_row(CREATED=datetime(2026, 1, 1, 0, 0, 0))
        info = _mixin().parse_routines([row], "app")[0]
        assert info.created == "2026-01-01 00:00:00"


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


class TestParseConstraints:
    def test_check_clause_and_identity_are_carried(self):
        rows = [
            {
                "CONSTRAINT_SCHEMA": "app",
                "TABLE_NAME": "orders",
                "CONSTRAINT_NAME": "ck_orders_total",
                "CONSTRAINT_TYPE": "CHECK",
                "CHECK_CLAUSE": "`total` >= 0",
            }
        ]
        result = _mixin().parse_constraints(rows, "orders", "app")

        assert result == [
            MariaDBConstraintInfo(
                schema="app",
                table_name="orders",
                name="ck_orders_total",
                constraint_type="CHECK",
                check_clause="`total` >= 0",
            )
        ]

    def test_enforced_is_not_invented(self):
        """MariaDB's catalog has no ENFORCED column; ``None`` means not reported."""
        info = _mixin().parse_constraints(
            [{"CONSTRAINT_NAME": "ck", "CONSTRAINT_TYPE": "CHECK"}], "orders", "app"
        )[0]
        assert info.enforced is None

    def test_rows_without_a_clause_keep_none(self):
        """A LEFT JOIN miss is "not reported", not an empty expression."""
        info = _mixin().parse_constraints(
            [{"CONSTRAINT_NAME": "ck", "CONSTRAINT_TYPE": "CHECK"}], "orders", "app"
        )[0]
        assert info.check_clause is None


# ---------------------------------------------------------------------------
# Identity: AUTO_INCREMENT in the column list
# ---------------------------------------------------------------------------


class TestAutoIncrementColumnParsing:
    """The identity audit: AUTO_INCREMENT must be visible in column info."""

    @staticmethod
    def _column_row(**overrides):
        row = {
            "COLUMN_NAME": "id",
            "ORDINAL_POSITION": 1,
            "COLUMN_DEFAULT": None,
            "IS_NULLABLE": "NO",
            "DATA_TYPE": "int",
            "COLUMN_TYPE": "int(11)",
            "COLUMN_KEY": "PRI",
            "EXTRA": "",
            "COLUMN_COMMENT": "",
            "CHARACTER_SET_NAME": None,
            "COLLATION_NAME": None,
            "CHARACTER_MAXIMUM_LENGTH": None,
            "NUMERIC_PRECISION": 10,
            "NUMERIC_SCALE": 0,
            "SRID": None,
        }
        row.update(overrides)
        return row

    def test_auto_increment_is_reported(self):
        columns = _mixin().parse_columns(
            [self._column_row(EXTRA="auto_increment")], "users", "app"
        )
        assert columns[0].is_auto_increment is True

    def test_plain_column_is_not_auto_increment(self):
        columns = _mixin().parse_columns([self._column_row()], "users", "app")
        assert columns[0].is_auto_increment is False

    def test_extra_with_other_flags_still_detects_auto_increment(self):
        """``EXTRA`` can carry several tokens; the marker is one of them."""
        columns = _mixin().parse_columns(
            [self._column_row(EXTRA="auto_increment on update CURRENT_TIMESTAMP")],
            "users",
            "app",
        )
        assert columns[0].is_auto_increment is True

    def test_identity_column_is_not_confused_with_auto_increment(self):
        """MariaDB reports no identity token here; the parser must not invent one."""
        columns = _mixin().parse_columns(
            [self._column_row(EXTRA="DEFAULT_GENERATED")], "users", "app"
        )
        assert columns[0].is_auto_increment is False


# ---------------------------------------------------------------------------
# Introspector methods: sync and async parity
# ---------------------------------------------------------------------------


PARTITION_ROWS = [
    {"TABLE_SCHEMA": "app", "TABLE_NAME": "orders", "PARTITION_NAME": "p0",
     "PARTITION_METHOD": "RANGE", "PARTITION_DESCRIPTION": "2026",
     "PARTITION_ORDINAL_POSITION": 1},
]

ROUTINE_ROWS = [
    _routine_row(ROUTINE_NAME="app_cleanup", PARAMETER_ORDINAL_POSITION=1,
                 PARAMETER_MODE="IN", PARAMETER_NAME="month"),
    _routine_row(ROUTINE_NAME="app_total", ROUTINE_TYPE="FUNCTION",
                 ROUTINE_DTD_IDENTIFIER="int", PARAMETER_ORDINAL_POSITION=1,
                 PARAMETER_MODE="IN", PARAMETER_NAME="amount"),
]

CONSTRAINT_ROWS = [
    {"CONSTRAINT_SCHEMA": "app", "TABLE_NAME": "orders",
     "CONSTRAINT_NAME": "ck_orders_total", "CONSTRAINT_TYPE": "CHECK",
     "CHECK_CLAUSE": "`total` >= 0"},
]


class TestSyncIntrospectorFamilies:
    def test_list_partitions_reads_and_caches(self):
        executor = _RecordingExecutor(PARTITION_ROWS)
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        first = introspector.list_partitions("orders")
        second = introspector.list_partitions("orders")

        assert len(first) == 1
        assert first[0].partition_name == "p0"
        assert first == second
        assert len(executor.calls) == 1

    def test_list_routines_reads_and_caches(self):
        executor = _RecordingExecutor(ROUTINE_ROWS)
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        first = introspector.list_routines()
        second = introspector.list_routines()

        assert [r.name for r in first] == ["app_cleanup", "app_total"]
        assert first[1].return_type == "int"
        assert first == second
        assert len(executor.calls) == 1

    def test_get_routine_info_returns_the_named_one(self):
        executor = _RecordingExecutor(ROUTINE_ROWS)
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        info = introspector.get_routine_info("app_total")

        assert info is not None
        assert info.kind == "FUNCTION"
        assert len(executor.calls) == 1
        assert "`r`.`ROUTINE_NAME` = %s" in executor.calls[0][0]

    def test_get_routine_info_miss_is_not_cached(self):
        executor = _RecordingExecutor([])
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        assert introspector.get_routine_info("missing") is None
        assert introspector.get_routine_info("missing") is None
        assert len(executor.calls) == 2

    def test_list_constraints_reads_and_caches(self):
        executor = _RecordingExecutor(CONSTRAINT_ROWS)
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        first = introspector.list_constraints("orders")
        second = introspector.list_constraints("orders")

        assert len(first) == 1
        assert first[0].check_clause == "`total` >= 0"
        assert first == second
        assert len(executor.calls) == 1

    def test_list_constraints_on_10_2_0_sends_no_query(self):
        """Below 10.2.1 there is no CHECK_CONSTRAINTS view to read."""
        executor = _RecordingExecutor(CONSTRAINT_ROWS)
        introspector = MariaDBIntrospector(
            _FakeBackend(version=(10, 2, 0)), executor
        )

        assert introspector.list_constraints("orders") == []
        assert executor.calls == []
        # The empty answer is cached, so a second ask also costs nothing.
        assert introspector.list_constraints("orders") == []
        assert executor.calls == []

    def test_list_constraints_on_10_2_1_reads(self):
        executor = _RecordingExecutor(CONSTRAINT_ROWS)
        introspector = MariaDBIntrospector(
            _FakeBackend(version=(10, 2, 1)), executor
        )

        assert len(introspector.list_constraints("orders")) == 1
        assert len(executor.calls) == 1

    def test_a_schema_argument_is_bound_and_resolved(self):
        executor = _RecordingExecutor(PARTITION_ROWS)
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        introspector.list_partitions("orders", schema="other")

        assert executor.calls[0][1] == ("other", "orders")


class TestAsyncIntrospectorFamilies:
    async def test_list_partitions(self):
        executor = _AsyncRecordingExecutor(PARTITION_ROWS)
        introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

        result = await introspector.list_partitions("orders")

        assert len(result) == 1
        assert len(executor.calls) == 1

    async def test_list_routines(self):
        executor = _AsyncRecordingExecutor(ROUTINE_ROWS)
        introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

        result = await introspector.list_routines()

        assert [r.name for r in result] == ["app_cleanup", "app_total"]
        assert result[1].parameters[0].name == "amount"

    async def test_get_routine_info(self):
        executor = _AsyncRecordingExecutor(ROUTINE_ROWS)
        introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

        info = await introspector.get_routine_info("app_total")

        assert info is not None
        assert info.kind == "FUNCTION"

    async def test_get_routine_info_miss_is_not_cached(self):
        executor = _AsyncRecordingExecutor([])
        introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

        assert await introspector.get_routine_info("missing") is None
        assert await introspector.get_routine_info("missing") is None
        assert len(executor.calls) == 2

    async def test_list_constraints(self):
        executor = _AsyncRecordingExecutor(CONSTRAINT_ROWS)
        introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

        result = await introspector.list_constraints("orders")

        assert len(result) == 1
        assert len(executor.calls) == 1

    async def test_list_constraints_on_10_2_0_sends_no_query(self):
        executor = _AsyncRecordingExecutor(CONSTRAINT_ROWS)
        introspector = AsyncMariaDBIntrospector(
            _FakeBackend(version=(10, 2, 0)), executor
        )

        assert await introspector.list_constraints("orders") == []
        assert executor.calls == []


class TestResultTypeShape:
    """The records are frozen and expose the derived answers only."""

    def test_partition_info_is_frozen(self):
        info = MariaDBPartitionInfo(schema="app", table_name="t")
        with pytest.raises(FrozenInstanceError):
            info.partition_name = "p0"  # type: ignore[misc]

    def test_routine_parameters_are_a_tuple(self):
        info = MariaDBRoutineInfo(
            schema="app",
            name="f",
            kind="FUNCTION",
            parameters=(MariaDBRoutineParameterInfo(ordinal_position=1),),
        )
        assert isinstance(info.parameters, tuple)

    def test_routine_kind_drives_is_function(self):
        assert MariaDBRoutineInfo(schema="app", name="f", kind="FUNCTION").is_function
        assert not MariaDBRoutineInfo(schema="app", name="p", kind="PROCEDURE").is_function
