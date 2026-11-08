# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_partition_maintenance.py
"""Unit tests for MariaDB partition maintenance and subpartition limits.

These tests never connect to a server, except for the opt-in live test at the
end, which is skipped unless a configured MariaDB scenario accepts a TCP
connection.  A fake backend supplies the snapshot rows and records the SQL
that ``ensure`` / ``drop_before`` would send.
"""

from datetime import date, datetime

import pytest

from mariadb_live_server import mariadb_server_available

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBAddPartitionExpression,
    MariaDBAnalyzePartitionExpression,
    MariaDBCoalescePartitionExpression,
    MariaDBCheckPartitionExpression,
    MariaDBDropPartitionExpression,
    MariaDBGetPartitionsExpression,
    MariaDBOptimizePartitionExpression,
    MariaDBPartitionByList,
    MariaDBPartitionByRange,
    MariaDBPartitionByRangeColumns,
    MariaDBPartitionDefinition,
    MariaDBPartitionMaxValue,
    MariaDBPartitionValue,
    MariaDBRebuildPartitionExpression,
    MariaDBReorganizePartitionExpression,
    MariaDBRepairPartitionExpression,
    MariaDBTruncatePartitionExpression,
    MariaDBRemovePartitioningExpression,
    MariaDBSubpartitionClause,
    MariaDBSubpartitionDefinition,
    MariaDBSubpartitionStrategy,
)
from rhosocial.activerecord.backend.partition import (
    AsyncPartitionEnsurer,
    AsyncPartitionInventory,
    AsyncPartitionRetention,
    AsyncPartitionValidator,
    PartitionEnsurer,
    PartitionInventory,
    PartitionReport as CorePartitionReport,
    PartitionRetention,
    PartitionValidator,
)
from rhosocial.activerecord.backend.impl.mariadb.partition_maintenance import (
    AsyncMariaDBPartitionMaintenance,
    MariaDBPartitionMaintenance,
    MariaDBPartitionPlan,
    MariaDBPartitionReport,
    build_report,
    plan_additions,
    select_drops,
)


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


def _value(dialect, value):
    return MariaDBPartitionValue(dialect, value)


def _definition(dialect, name, upper_bound):
    if upper_bound is None:
        return MariaDBPartitionDefinition(
            name=name, less_than=[MariaDBPartitionMaxValue(dialect)]
        )
    return MariaDBPartitionDefinition(name=name, less_than=[_value(dialect, upper_bound)])


def _rows(*partitions):
    rows = []
    for name, description, subnames in partitions:
        if not subnames:
            rows.append(
                {
                    "name": name,
                    "subname": None,
                    "method": "RANGE",
                    "submethod": None,
                    "description": description,
                    "table_rows": 1,
                    "data_length": 2,
                    "index_length": 3,
                }
            )
            continue
        for index, subname in enumerate(subnames):
            rows.append(
                {
                    "name": name,
                    "subname": subname,
                    "method": "RANGE",
                    "submethod": "HASH",
                    "description": description,
                    "table_rows": index + 1,
                    "data_length": 2,
                    "index_length": 3,
                }
            )
    return rows


def _single_row(name, description, method="RANGE"):
    """Build one ``information_schema.PARTITIONS`` row with the given method."""
    return {
        "name": name,
        "subname": None,
        "method": method,
        "submethod": None,
        "description": description,
        "table_rows": 1,
        "data_length": 2,
        "index_length": 3,
    }


class FakeBackend:
    """Minimal backend surface used by the maintenance class."""

    def __init__(self, rows):
        self.dialect = MariaDBDialect(version=(10, 6, 0))
        self._rows = rows
        self.executed = []

    def fetch_all(self, sql, params=None):
        return list(self._rows)

    def execute(self, sql, params=None):
        self.executed.append((sql, params))


class FakeAsyncBackend(FakeBackend):
    """Async counterpart of :class:`FakeBackend`."""

    async def fetch_all(self, sql, params=None):
        return list(self._rows)

    async def execute(self, sql, params=None):
        self.executed.append((sql, params))


# --- subpartition capability limits ----------------------------------------


def test_subpartition_hash_and_key_are_accepted(dialect):
    for strategy in (
        MariaDBSubpartitionStrategy.HASH,
        MariaDBSubpartitionStrategy.KEY,
        MariaDBSubpartitionStrategy.LINEAR_HASH,
        MariaDBSubpartitionStrategy.LINEAR_KEY,
    ):
        clause = MariaDBSubpartitionClause(
            dialect, strategy=strategy,
            expression=Column(dialect, "id"), count=2,
        )
        sql, params = clause.to_sql()
        assert f"SUBPARTITION BY {strategy.value}" in sql
        assert "`id`" in sql
        assert "SUBPARTITIONS 2" in sql
        assert params == ()


@pytest.mark.parametrize(
    "strategy",
    [
        MariaDBSubpartitionStrategy.HASH,
        MariaDBSubpartitionStrategy.KEY,
        MariaDBSubpartitionStrategy.LINEAR_HASH,
        MariaDBSubpartitionStrategy.LINEAR_KEY,
    ],
)
def test_subpartition_requires_column_list(dialect, strategy):
    """Every HASH/KEY subpartition form needs a column list."""
    with pytest.raises(ValueError, match="requires an expression"):
        MariaDBSubpartitionClause(dialect, strategy=strategy, count=2)


@pytest.mark.parametrize("strategy", ["RANGE", "RANGE COLUMNS", "LIST", "LIST COLUMNS"])
def test_subpartition_range_and_list_are_refused_by_name(dialect, strategy):
    with pytest.raises(UnsupportedFeatureError, match="SUBPARTITION BY"):
        MariaDBSubpartitionClause(dialect, strategy=strategy)


def test_subpartition_range_is_not_silently_downgraded(dialect):
    with pytest.raises(UnsupportedFeatureError) as caught:
        MariaDBSubpartitionClause(dialect, strategy="RANGE")
    assert "RANGE" in caught.value.feature_name
    assert "HASH" in (caught.value.suggestion or "")


def test_explicit_per_partition_subpartition_definitions(dialect):
    expression = MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            MariaDBPartitionDefinition(
                "p2026",
                less_than=[_value(dialect, "2027-01-01")],
                subpartition_definitions=[
                    MariaDBSubpartitionDefinition("p2026_s0"),
                    MariaDBSubpartitionDefinition("p2026_s1"),
                ],
            ),
            MariaDBPartitionDefinition(
                "p2027",
                less_than=[_value(dialect, "2028-01-01")],
                subpartition_definitions=[MariaDBSubpartitionDefinition("p2027_s0")],
            ),
        ],
        subpartition_by=MariaDBSubpartitionClause(
            dialect,
            strategy=MariaDBSubpartitionStrategy.HASH,
            expression=Column(dialect, "tenant_id"),
            count=2,
        ),
    )

    sql, params = expression.to_sql()

    assert sql.index("SUBPARTITION BY HASH") < sql.index("PARTITION `p2026`")
    assert "`p2026_s0`" in sql and "`p2026_s1`" in sql
    assert "`p2027_s0`" in sql
    assert params == ()


def test_subpartition_by_range_columns_and_list(dialect):
    expression = MariaDBPartitionByRangeColumns(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[_definition(dialect, "p0", "2026-01-01")],
        subpartition_by=MariaDBSubpartitionClause(
            dialect, strategy=MariaDBSubpartitionStrategy.KEY,
            expression=Column(dialect, "id"), count=1
        ),
    )
    sql, _ = expression.to_sql()
    assert "SUBPARTITION BY KEY" in sql
    assert "`id`" in sql

    list_expression = MariaDBPartitionByList(
        dialect,
        [Column(dialect, "region")],
        partitions=[
            MariaDBPartitionDefinition("p_east", in_values=[_value(dialect, "east")])
        ],
        subpartition_by=MariaDBSubpartitionClause(
            dialect, strategy=MariaDBSubpartitionStrategy.HASH,
            expression=Column(dialect, "id"), count=2
        ),
    )
    list_sql, _ = list_expression.to_sql()
    assert "PARTITION BY LIST" in list_sql
    assert "SUBPARTITION BY HASH" in list_sql


# --- maintenance expressions -----------------------------------------------


def test_add_drop_truncate_and_reorganize_expressions(dialect):
    table = Table(dialect, "events")
    definitions = [_definition(dialect, "p2026_03", "2026-04-01")]

    add_sql, add_params = MariaDBAddPartitionExpression(
        dialect, table, definitions
    ).to_sql()
    assert add_sql.startswith("ALTER TABLE `events` ADD PARTITION")
    assert "p2026_03" in add_sql
    assert add_params == ()

    drop_sql, _ = MariaDBDropPartitionExpression(dialect, table, ["p2026_03"]).to_sql()
    assert drop_sql == "ALTER TABLE `events` DROP PARTITION `p2026_03`"

    truncate_sql, _ = MariaDBTruncatePartitionExpression(
        dialect, table, ["p2026_03"]
    ).to_sql()
    assert truncate_sql == "ALTER TABLE `events` TRUNCATE PARTITION `p2026_03`"

    reorganize_sql, reorganize_params = MariaDBReorganizePartitionExpression(
        dialect,
        table,
        "p2026_03",
        [
            _definition(dialect, "p2026_03a", "2026-03-15"),
            _definition(dialect, "p2026_03b", "2026-04-01"),
        ],
    ).to_sql()
    assert "REORGANIZE PARTITION `p2026_03` INTO" in reorganize_sql
    assert "p2026_03a" in reorganize_sql and "p2026_03b" in reorganize_sql
    assert reorganize_params == ()


def test_remaining_maintenance_expressions(dialect):
    table = Table(dialect, "events")
    cases = [
        (MariaDBRemovePartitioningExpression(dialect, table), "REMOVE PARTITIONING"),
        (MariaDBCoalescePartitionExpression(dialect, table, 2), "COALESCE PARTITION 2"),
        (MariaDBAnalyzePartitionExpression(dialect, table, ["p0"]), "ANALYZE PARTITION"),
        (MariaDBCheckPartitionExpression(dialect, table, ["p0"]), "CHECK PARTITION"),
        (MariaDBOptimizePartitionExpression(dialect, table, ["p0"]), "OPTIMIZE PARTITION"),
        (MariaDBRebuildPartitionExpression(dialect, table, ["p0"]), "REBUILD PARTITION"),
        (MariaDBRepairPartitionExpression(dialect, table, ["p0"]), "REPAIR PARTITION"),
    ]
    for expression, expected in cases:
        sql, params = expression.to_sql()
        assert expected in sql
        assert params == ()


def test_partition_name_lists_are_validated(dialect):
    table = Table(dialect, "events")
    with pytest.raises(ValueError, match="positive integer"):
        MariaDBCoalescePartitionExpression(dialect, table, 0)
    with pytest.raises(ValueError, match="partitions must not be empty"):
        MariaDBAnalyzePartitionExpression(dialect, table, []).to_sql()
    with pytest.raises(ValueError, match="partitions must not be empty"):
        MariaDBAddPartitionExpression(dialect, table, []).to_sql()


def test_get_partitions_expression(dialect):
    sql, params = MariaDBGetPartitionsExpression(dialect, "events").to_sql()
    assert "SELECT" in sql.upper()
    assert "TABLE_NAME" in sql
    assert "PARTITION_NAME" in sql
    assert params == ("events",)
    with pytest.raises(ValueError, match="must not be empty"):
        MariaDBGetPartitionsExpression(dialect, "  ")


# --- plan validation and planning ------------------------------------------


def test_plan_requires_unique_names_and_ascending_bounds(dialect):
    with pytest.raises(ValueError, match="must be unique"):
        MariaDBPartitionPlan(
            "events",
            (_definition(dialect, "p1", 10), _definition(dialect, "p1", 20)),
        )
    with pytest.raises(ValueError, match="ascending order"):
        MariaDBPartitionPlan(
            "events",
            (_definition(dialect, "p1", 20), _definition(dialect, "p2", 10)),
        )
    with pytest.raises(ValueError, match="MAXVALUE partition must be the last"):
        MariaDBPartitionPlan(
            "events",
            (_definition(dialect, "pmax", None), _definition(dialect, "p1", 10)),
        )


def test_plan_additions_adds_only_missing_ascending(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    additions, skipped = plan_additions(plan, ["p2026_01"])
    assert [definition.name for definition in additions] == ["p2026_02", "p2026_03"]
    assert skipped == []


def test_plan_additions_skips_below_maximum_and_after_maxvalue(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    additions, skipped = plan_additions(plan, ["p2026_01", "p2026_03"])
    assert additions == []
    assert [name for name, _ in skipped] == ["p2026_02"]
    assert "REORGANIZE" in skipped[0][1]

    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    additions, skipped = plan_additions(plan, ["p2026", "pmax"])
    assert additions == []
    assert [name for name, _ in skipped] == ["p2027"]
    assert "MAXVALUE" in skipped[0][1]


def test_plan_additions_reports_unknown_existing_partition(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
        ),
    )
    additions, skipped = plan_additions(plan, ["p_legacy", "p2026"])
    assert additions == []
    assert [name for name, _ in skipped] == ["p2027"]
    assert "not named by the plan" in skipped[0][1]


def test_select_drops_uses_whole_range_at_or_before_cutoff(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    dropped, skipped = select_drops(
        plan, ["p2026_01", "p2026_02", "p2026_03"], date(2026, 3, 1)
    )
    assert dropped == ["p2026_01", "p2026_02"]
    assert skipped == []


def test_select_drops_keeps_last_when_cutoff_matches_its_bound(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    dropped, skipped = select_drops(
        plan, ["p2026_01", "p2026_02"], date(2026, 3, 1)
    )
    assert dropped == ["p2026_01"]
    assert [name for name, _ in skipped] == ["p2026_02"]
    assert "last partition" in skipped[0][1]


def test_select_drops_keeps_last_partition(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    dropped, skipped = select_drops(
        plan, ["p2026_01", "p2026_02"], datetime(2026, 4, 1)
    )
    assert dropped == ["p2026_01"]
    assert [name for name, _ in skipped] == ["p2026_02"]
    assert "last partition" in skipped[0][1]


def test_select_drops_rejects_list_plan(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (MariaDBPartitionDefinition("p_a", in_values=[_value(dialect, "a")]),),
    )
    with pytest.raises(ValueError, match="RANGE plans"):
        select_drops(plan, ["p_a"], 100)


# --- report building and operations ----------------------------------------


def test_build_report_flat_tree_with_subpartitions():
    report = build_report(
        "events",
        _rows(
            ("p2026", "2027-01-01", ("p2026_s0", "p2026_s1")),
            ("p2027", "2028-01-01", ()),
        ),
    )
    assert isinstance(report, MariaDBPartitionReport)
    assert report.partition_names == ("p2026", "p2027")
    parent = report.partitions[0]
    assert parent.parent is None
    assert parent.extras["children"] == ("p2026_s0", "p2026_s1")
    assert parent.row_count == 3
    assert parent.size_bytes == 10
    child = report.partitions[1]
    assert child.parent == "p2026"
    assert child.method == "HASH"
    assert child.bound is None


def test_ensure_executes_one_add_statement(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    backend = FakeBackend(_rows(("p2026_01", "2026-02-01", ()),))
    maintenance = MariaDBPartitionMaintenance(backend)

    report = maintenance.ensure(plan)

    assert report.added == ("p2026_02",)
    assert len(backend.executed) == 1
    sql, params = backend.executed[0]
    assert sql.startswith("ALTER TABLE `events` ADD PARTITION")
    assert "p2026_02" in sql
    assert params == ()


def test_ensure_dry_run_sends_no_sql(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    backend = FakeBackend(_rows(("p2026_01", "2026-02-01", ()),))
    maintenance = MariaDBPartitionMaintenance(backend)

    report = maintenance.ensure(plan, dry_run=True)
    assert report.added == ("p2026_02",)
    assert report.dry_run is True
    assert backend.executed == []


def test_ensure_reorganizes_maxvalue_for_a_new_boundary(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026", "2027-01-01", ()),
            ("pmax", "MAXVALUE", ()),
        )
    )
    maintenance = MariaDBPartitionMaintenance(backend)

    report = maintenance.ensure(plan)

    assert report.added == ("p2027",)
    assert report.missing == (("events", "p2027"),)
    assert report.skipped == ()
    assert len(backend.executed) == 1
    sql, params = backend.executed[0]
    assert sql.startswith("ALTER TABLE `events` REORGANIZE PARTITION `pmax` INTO")
    assert "PARTITION `p2027` VALUES LESS THAN ('2028-01-01')" in sql
    assert "PARTITION `pmax` VALUES LESS THAN (MAXVALUE)" in sql
    assert params == ()


def test_ensure_reorganizes_following_partition_to_fill_a_gap(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_03", "2026-04-01", ()),
        )
    )
    maintenance = MariaDBPartitionMaintenance(backend)

    report = maintenance.ensure(plan)

    assert report.added == ("p2026_02",)
    assert report.skipped == ()
    assert len(backend.executed) == 1
    sql, params = backend.executed[0]
    assert sql.startswith(
        "ALTER TABLE `events` REORGANIZE PARTITION `p2026_03` INTO"
    )
    assert "PARTITION `p2026_02` VALUES LESS THAN ('2026-03-01')" in sql
    assert "PARTITION `p2026_03` VALUES LESS THAN ('2026-04-01')" in sql
    assert params == ()


def test_ensure_skips_a_boundary_drift(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-15", ()),
        )
    )
    maintenance = MariaDBPartitionMaintenance(backend)

    report = maintenance.ensure(plan)

    assert report.added == ()
    assert [name for name, _ in report.skipped] == ["p2026_02"]
    reason = report.skipped[0][1]
    assert "PARTITION_DESCRIPTION" in reason
    assert "boundary drift" in reason
    assert backend.executed == []


def test_ensure_skips_an_existing_partition_the_plan_does_not_name(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026", "2027-01-01", ()),
            ("p_legacy", "2030-01-01", ()),
        )
    )
    maintenance = MariaDBPartitionMaintenance(backend)

    report = maintenance.ensure(plan)

    assert report.added == ()
    assert [name for name, _ in report.skipped] == ["p2027"]
    assert "not named by the plan" in report.skipped[0][1]
    assert backend.executed == []


def test_list_fills_missing_pairs_and_keeps_orphans(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p_legacy", "2026-05-01", ()),
        )
    )
    maintenance = MariaDBPartitionMaintenance(backend)

    report = maintenance.list("events", plan=plan)

    assert report.missing == (
        ("events", "p2026_02"),
        ("events", "p2026_03"),
    )
    assert report.orphans == ("p_legacy",)
    assert backend.executed == []


def test_validate_reports_missing_orphans_and_drift(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    backend = FakeBackend(
        [
            _single_row("p2026_01", "2026-02-15"),
            _single_row("p2026_02", "2026-03-01", method="LIST"),
            _single_row("p_legacy", "2026-05-01"),
        ]
    )
    maintenance = MariaDBPartitionMaintenance(backend)

    report = maintenance.validate(plan)

    assert report.missing == (
        ("events", "p2026_03"),
        ("events", "pmax"),
    )
    assert report.orphans == ("p_legacy",)
    issues = "\n".join(report.issues)
    assert "p2026_01" in issues and "PARTITION_DESCRIPTION" in issues
    assert "boundary drift" in issues
    assert "p2026_02" in issues and "PARTITION_METHOD is LIST" in issues
    assert "method drift" in issues
    assert backend.executed == []


def test_validate_accepts_a_plan_that_matches_the_catalogue(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026", "2027-01-01", ()),
            ("pmax", "MAXVALUE", ()),
        )
    )
    maintenance = MariaDBPartitionMaintenance(backend)

    report = maintenance.validate(plan)

    assert report.missing == ()
    assert report.orphans == ()
    assert report.issues == ()


def test_drop_before_dry_run_and_execution(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_02", "2026-03-01", ()),
            ("p2026_03", "2026-04-01", ()),
        )
    )
    maintenance = MariaDBPartitionMaintenance(backend)

    dry = maintenance.drop_before(plan, date(2026, 3, 1))
    assert dry.dropped == ("p2026_01", "p2026_02")
    assert dry.dry_run is True
    assert backend.executed == []

    maintenance.drop_before(plan, date(2026, 3, 1), dry_run=False)
    sql, params = backend.executed[0]
    assert sql.startswith("ALTER TABLE `events` DROP PARTITION")
    assert "p2026_01" in sql and "p2026_02" in sql
    assert params == ()


def test_list_marks_orphans_only_when_plan_given():
    backend = FakeBackend(_rows(("p2026_01", "2026-02-01", ()),))
    maintenance = MariaDBPartitionMaintenance(backend)

    assert maintenance.list("events").orphans == ()
    plan = MariaDBPartitionPlan(
        "events",
        (
            MariaDBPartitionDefinition(
                "p2026_02", less_than=[_value(backend.dialect, "2026-03-01")]
            ),
        ),
    )
    assert maintenance.list("events", plan=plan).orphans == ("p2026_01",)


@pytest.mark.asyncio
async def test_async_maintenance_matches_sync_behaviour(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    backend = FakeAsyncBackend(_rows(("p2026_01", "2026-02-01", ()),))
    maintenance = AsyncMariaDBPartitionMaintenance(backend)

    ensured = await maintenance.ensure(plan)
    assert ensured.added == ("p2026_02",)
    assert backend.executed[-1][0].startswith("ALTER TABLE `events` ADD PARTITION")

    backend._rows = _rows(
        ("p2026_01", "2026-02-01", ()),
        ("p2026_02", "2026-03-01", ()),
    )
    dropped = await maintenance.drop_before(plan, date(2026, 3, 1), dry_run=False)
    assert dropped.dropped == ("p2026_01",)
    assert backend.executed[-1][0].startswith("ALTER TABLE `events` DROP PARTITION")


@pytest.mark.asyncio
async def test_async_ensure_reorganizes_maxvalue(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    backend = FakeAsyncBackend(
        _rows(
            ("p2026", "2027-01-01", ()),
            ("pmax", "MAXVALUE", ()),
        )
    )
    maintenance = AsyncMariaDBPartitionMaintenance(backend)

    report = await maintenance.ensure(plan)

    assert report.added == ("p2027",)
    assert report.skipped == ()
    sql, params = backend.executed[-1]
    assert sql.startswith("ALTER TABLE `events` REORGANIZE PARTITION `pmax` INTO")
    assert "PARTITION `p2027` VALUES LESS THAN ('2028-01-01')" in sql
    assert params == ()


@pytest.mark.asyncio
async def test_async_ensure_reorganizes_following_partition_for_gap(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeAsyncBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_03", "2026-04-01", ()),
        )
    )
    maintenance = AsyncMariaDBPartitionMaintenance(backend)

    report = await maintenance.ensure(plan)

    assert report.added == ("p2026_02",)
    assert report.skipped == ()
    sql, params = backend.executed[-1]
    assert sql.startswith(
        "ALTER TABLE `events` REORGANIZE PARTITION `p2026_03` INTO"
    )
    assert "PARTITION `p2026_02` VALUES LESS THAN ('2026-03-01')" in sql
    assert params == ()


@pytest.mark.asyncio
async def test_async_validate_reports_drift(dialect):
    plan = MariaDBPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    backend = FakeAsyncBackend(
        [
            _single_row("p2026_01", "2026-02-15"),
            _single_row("p2026_02", "2026-03-01", method="LIST"),
        ]
    )
    maintenance = AsyncMariaDBPartitionMaintenance(backend)

    report = await maintenance.validate(plan)

    assert report.missing == ()
    assert report.orphans == ()
    issues = "\n".join(report.issues)
    assert "PARTITION_DESCRIPTION" in issues and "boundary drift" in issues
    assert "PARTITION_METHOD is LIST" in issues and "method drift" in issues


def test_report_is_the_core_contract_type():
    assert MariaDBPartitionReport is CorePartitionReport


def test_the_sync_executor_offers_inventory_ensure_retention_and_validation():
    executor = MariaDBPartitionMaintenance(FakeBackend([]))

    assert isinstance(executor, PartitionInventory)
    assert isinstance(executor, PartitionEnsurer)
    assert isinstance(executor, PartitionRetention)
    assert isinstance(executor, PartitionValidator)


def test_the_async_executor_offers_inventory_ensure_retention_and_validation():
    executor = AsyncMariaDBPartitionMaintenance(FakeAsyncBackend([]))

    assert isinstance(executor, AsyncPartitionInventory)
    assert isinstance(executor, AsyncPartitionEnsurer)
    assert isinstance(executor, AsyncPartitionRetention)
    assert isinstance(executor, AsyncPartitionValidator)


@pytest.mark.skipif(
    not mariadb_server_available(),
    reason="no MariaDB server reachable from the configured scenarios",
)
def test_live_ensure_reorganizes_maxvalue_and_validate_agrees(
    mariadb_backend_single,
):
    """The live server accepts the MAXVALUE reorganisation ensure plans."""
    table = "partition_maintenance_live"
    backend = mariadb_backend_single
    backend.executescript(
        f"DROP TABLE IF EXISTS `{table}`; "
        f"CREATE TABLE `{table}` (`id` INT NOT NULL, PRIMARY KEY (`id`)) "
        f"ENGINE=InnoDB PARTITION BY RANGE (`id`) ("
        f"PARTITION p0 VALUES LESS THAN (10), "
        f"PARTITION pmax VALUES LESS THAN (MAXVALUE))"
    )
    try:
        dialect = backend.dialect
        plan = MariaDBPartitionPlan(
            table,
            (
                _definition(dialect, "p0", 10),
                _definition(dialect, "p10", 20),
                _definition(dialect, "pmax", None),
            ),
        )
        maintenance = MariaDBPartitionMaintenance(backend)

        ensured = maintenance.ensure(plan)
        assert ensured.added == ("p10",)
        assert ensured.skipped == ()

        listed = maintenance.list(table, plan=plan)
        assert listed.partition_names == ("p0", "p10", "pmax")
        assert listed.missing == ()

        validated = maintenance.validate(plan)
        assert validated.issues == ()
    finally:
        backend.executescript(f"DROP TABLE IF EXISTS `{table}`")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not mariadb_server_available(),
    reason="no MariaDB server reachable from the configured scenarios",
)
async def test_live_async_ensure_reorganizes_maxvalue_and_validate_agrees(
    async_mariadb_backend_single,
):
    """The async executor sends the same MAXVALUE reorganisation as the sync one."""
    table = "partition_maintenance_live_async"
    backend = async_mariadb_backend_single
    await backend.executescript(
        f"DROP TABLE IF EXISTS `{table}`; "
        f"CREATE TABLE `{table}` (`id` INT NOT NULL, PRIMARY KEY (`id`)) "
        f"ENGINE=InnoDB PARTITION BY RANGE (`id`) ("
        f"PARTITION p0 VALUES LESS THAN (10), "
        f"PARTITION pmax VALUES LESS THAN (MAXVALUE))"
    )
    try:
        dialect = backend.dialect
        plan = MariaDBPartitionPlan(
            table,
            (
                _definition(dialect, "p0", 10),
                _definition(dialect, "p10", 20),
                _definition(dialect, "pmax", None),
            ),
        )
        maintenance = AsyncMariaDBPartitionMaintenance(backend)

        ensured = await maintenance.ensure(plan)
        assert ensured.added == ("p10",)
        assert ensured.skipped == ()

        listed = await maintenance.list(table, plan=plan)
        assert listed.partition_names == ("p0", "p10", "pmax")
        assert listed.missing == ()

        validated = await maintenance.validate(plan)
        assert validated.issues == ()
    finally:
        await backend.executescript(f"DROP TABLE IF EXISTS `{table}`")
