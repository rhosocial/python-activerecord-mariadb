# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/partition/test_partition_expression_limits.py
"""Unit tests for MariaDB partition expression rendering and subpartition limits.

These tests are entirely offline: they render expression nodes through the
MariaDB dialect and assert on the emitted SQL and on expression-level errors.
"""

import pytest

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


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


def _value(dialect, value):
    return MariaDBPartitionValue(dialect, value)


def _definition(dialect, name, upper_bound):
    if upper_bound is None:
        return MariaDBPartitionDefinition(name=name, less_than=[MariaDBPartitionMaxValue(dialect)])
    return MariaDBPartitionDefinition(name=name, less_than=[_value(dialect, upper_bound)])


# --- subpartition capability limits ----------------------------------------


def test_subpartition_hash_and_key_are_accepted(dialect):
    for strategy in (
        MariaDBSubpartitionStrategy.HASH,
        MariaDBSubpartitionStrategy.KEY,
        MariaDBSubpartitionStrategy.LINEAR_HASH,
        MariaDBSubpartitionStrategy.LINEAR_KEY,
    ):
        clause = MariaDBSubpartitionClause(
            dialect,
            strategy=strategy,
            expression=Column(dialect, "id"),
            count=2,
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
            dialect,
            strategy=MariaDBSubpartitionStrategy.KEY,
            expression=Column(dialect, "id"),
            count=1,
        ),
    )
    sql, _ = expression.to_sql()
    assert "SUBPARTITION BY KEY" in sql
    assert "`id`" in sql

    list_expression = MariaDBPartitionByList(
        dialect,
        [Column(dialect, "region")],
        partitions=[MariaDBPartitionDefinition("p_east", in_values=[_value(dialect, "east")])],
        subpartition_by=MariaDBSubpartitionClause(
            dialect,
            strategy=MariaDBSubpartitionStrategy.HASH,
            expression=Column(dialect, "id"),
            count=2,
        ),
    )
    list_sql, _ = list_expression.to_sql()
    assert "PARTITION BY LIST" in list_sql
    assert "SUBPARTITION BY HASH" in list_sql


# --- maintenance expressions -----------------------------------------------


def test_add_drop_truncate_and_reorganize_expressions(dialect):
    table = Table(dialect, "events")
    definitions = [_definition(dialect, "p2026_03", "2026-04-01")]

    add_sql, add_params = MariaDBAddPartitionExpression(dialect, table, definitions).to_sql()
    assert add_sql.startswith("ALTER TABLE `events` ADD PARTITION")
    assert "p2026_03" in add_sql
    assert add_params == ()

    drop_sql, _ = MariaDBDropPartitionExpression(dialect, table, ["p2026_03"]).to_sql()
    assert drop_sql == "ALTER TABLE `events` DROP PARTITION `p2026_03`"

    truncate_sql, _ = MariaDBTruncatePartitionExpression(dialect, table, ["p2026_03"]).to_sql()
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
