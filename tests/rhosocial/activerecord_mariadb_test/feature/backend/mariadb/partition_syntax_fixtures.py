# tests/rhosocial/activerecord_mariadb_test/feature/backend/mariadb/partition_syntax_fixtures.py
"""Case metadata for the MariaDB partition syntax matrix.

The matrix is data, not code: each case names one MariaDB partition syntax
family, the builders that render it, the fragments the renderer must (or must
not) emit, and optional planning, refusal, and live hooks.  The test module is
one set of assertions driven by this table, so adding a family means adding a
row rather than another test function.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Optional, Tuple

import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBAddPartitionExpression,
    MariaDBAnalyzePartitionExpression,
    MariaDBCoalescePartitionExpression,
    MariaDBCheckPartitionExpression,
    MariaDBDropPartitionExpression,
    MariaDBGetPartitionsExpression,
    MariaDBOptimizePartitionExpression,
    MariaDBPartitionByHash,
    MariaDBPartitionByKey,
    MariaDBPartitionByList,
    MariaDBPartitionByListColumns,
    MariaDBPartitionByRange,
    MariaDBPartitionByRangeColumns,
    MariaDBPartitionDefinition,
    MariaDBPartitionMaxValue,
    MariaDBPartitionOptions,
    MariaDBPartitionValue,
    MariaDBRebuildPartitionExpression,
    MariaDBReorganizePartitionExpression,
    MariaDBRemovePartitioningExpression,
    MariaDBRepairPartitionExpression,
    MariaDBSubpartitionClause,
    MariaDBSubpartitionDefinition,
    MariaDBSubpartitionStrategy,
    MariaDBTruncatePartitionExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.partition_maintenance import (
    MariaDBPartitionPlan,
)

#: A builder receives the dialect and returns one expression or a sequence.
Builder = Callable[[MariaDBDialect], Any]


@dataclass(frozen=True)
class PartitionSyntaxCase:
    """One row of the MariaDB partition syntax matrix.

    Attributes:
        name: Stable fixture id and case name.
        description: Human-readable statement of what the case covers.
        builders: Callables that build the expressions to render; a builder
            may return one expression or a sequence of expressions.
        required_fragments: Substrings every rendering must contain.
        forbidden_fragments: Substrings no rendering may contain.
        ordered_fragments: Substrings that must appear in this order.
        expected_params: Expected parameter tuple for every rendering, when
            the case cares about parameters.
        refusal_builder: Callable that must raise ``UnsupportedFeatureError``.
        refused_feature: Expected fragment of the raised feature name.
        plan_builder: Callable returning a valid ``MariaDBPartitionPlan``.
        existing_partitions: Existing partition names used by planning.
        expected_additions: Names ``plan_additions`` should return.
        expected_skipped: Names ``plan_additions`` should skip.
        invalid_plan_builder: Callable building a plan that must be refused.
        invalid_plan_error: Fragment of the refusal message.
        drop_cutoff: Cutoff value passed to ``drop_before``.
        expected_dropped: Names ``drop_before`` should drop.
        exercise_maintenance: Run ensure/list/drop_before with a fake backend.
        live_setup: Optional callable for a future live MariaDB scenario.
        live_check: Optional callable validating the live setup result.
    """

    name: str
    description: str
    builders: Tuple[Builder, ...] = ()
    required_fragments: Tuple[str, ...] = ()
    forbidden_fragments: Tuple[str, ...] = ()
    ordered_fragments: Tuple[str, ...] = ()
    expected_params: Optional[Tuple[Any, ...]] = None
    refusal_builder: Optional[Builder] = None
    refused_feature: str = ""
    plan_builder: Optional[Builder] = None
    existing_partitions: Tuple[str, ...] = ()
    expected_additions: Tuple[str, ...] = ()
    expected_skipped: Tuple[str, ...] = ()
    invalid_plan_builder: Optional[Builder] = None
    invalid_plan_error: str = ""
    drop_cutoff: Any = None
    expected_dropped: Tuple[str, ...] = ()
    exercise_maintenance: bool = False
    live_setup: Optional[Callable[[Any], Any]] = None
    live_check: Optional[Callable[[Any], Any]] = None


def _value(dialect: MariaDBDialect, value: Any) -> MariaDBPartitionValue:
    """Build a MariaDB partition boundary value."""
    return MariaDBPartitionValue(dialect, value)


def _range_definition(
    dialect: MariaDBDialect,
    name: str,
    upper_bound: Any,
) -> MariaDBPartitionDefinition:
    """Build a RANGE definition with one ``less_than`` bound."""
    return MariaDBPartitionDefinition(
        name=name,
        less_than=[_value(dialect, upper_bound)],
    )


def _maxvalue_definition(
    dialect: MariaDBDialect,
    name: str,
) -> MariaDBPartitionDefinition:
    """Build a RANGE definition terminated by ``MAXVALUE``."""
    return MariaDBPartitionDefinition(
        name=name,
        less_than=[MariaDBPartitionMaxValue(dialect)],
    )


def _build_range(dialect: MariaDBDialect):
    return MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            _range_definition(dialect, "p0", "2024-01-01"),
            _maxvalue_definition(dialect, "pmax"),
        ],
    )


def _build_range_columns(dialect: MariaDBDialect):
    return MariaDBPartitionByRangeColumns(
        dialect,
        [Column(dialect, "a")],
        partitions=[_range_definition(dialect, "p0", 10)],
    )


def _build_list(dialect: MariaDBDialect):
    return MariaDBPartitionByList(
        dialect,
        [Column(dialect, "region")],
        partitions=[
            MariaDBPartitionDefinition(
                name="p_east",
                in_values=[_value(dialect, "east")],
            )
        ],
    )


def _build_list_columns(dialect: MariaDBDialect):
    return MariaDBPartitionByListColumns(
        dialect,
        [Column(dialect, "a"), Column(dialect, "b")],
        partitions=[
            MariaDBPartitionDefinition(
                name="p0",
                in_values=[
                    [_value(dialect, "a"), _value(dialect, "x")],
                    [_value(dialect, "b"), _value(dialect, "y")],
                ],
            )
        ],
    )


def _build_hash(dialect: MariaDBDialect):
    return MariaDBPartitionByHash(
        dialect,
        [Column(dialect, "id")],
        partitions_count=4,
    )


def _build_key(dialect: MariaDBDialect):
    return MariaDBPartitionByKey(dialect, partitions_count=2)


def _build_linear_hash(dialect: MariaDBDialect):
    return MariaDBPartitionByHash(
        dialect,
        [Column(dialect, "id")],
        partitions_count=2,
        linear=True,
    )


def _build_linear_key(dialect: MariaDBDialect):
    return MariaDBPartitionByKey(
        dialect,
        [Column(dialect, "id")],
        partitions_count=2,
        linear=True,
    )


def _build_hash_subpartition(dialect: MariaDBDialect):
    return MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            MariaDBPartitionDefinition(
                name="p2026",
                less_than=[_value(dialect, "2027-01-01")],
                subpartition_definitions=[
                    MariaDBSubpartitionDefinition(name="p2026_s0"),
                    MariaDBSubpartitionDefinition(name="p2026_s1"),
                ],
            )
        ],
        subpartition_by=MariaDBSubpartitionClause(
            dialect,
            strategy=MariaDBSubpartitionStrategy.HASH,
            expression=Column(dialect, "tenant_id"),
            count=2,
        ),
    )


def _build_key_subpartition(dialect: MariaDBDialect):
    return MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[_range_definition(dialect, "p2026", "2027-01-01")],
        subpartition_by=MariaDBSubpartitionClause(
            dialect,
            strategy=MariaDBSubpartitionStrategy.KEY,
            expression=Column(dialect, "id"),
            count=2,
        ),
    )


def _refuse_range_subpartition(dialect: MariaDBDialect):
    return MariaDBSubpartitionClause(dialect, strategy="RANGE")


def _refuse_list_subpartition(dialect: MariaDBDialect):
    return MariaDBSubpartitionClause(dialect, strategy="LIST")


def _build_partition_options(dialect: MariaDBDialect):
    return MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "a")],
        partitions=[
            MariaDBPartitionDefinition(
                name="p0",
                less_than=[_value(dialect, 1)],
                partition_options=MariaDBPartitionOptions(
                    engine="InnoDB",
                    comment="first",
                    max_rows=1000,
                    tablespace="ts_hot",
                ),
            )
        ],
    )


def _build_lifecycle_add_drop(dialect: MariaDBDialect):
    table = Table(dialect, "events")
    return (
        MariaDBAddPartitionExpression(
            dialect,
            table,
            [_range_definition(dialect, "p2026_03", "2026-04-01")],
        ),
        MariaDBDropPartitionExpression(dialect, table, ["p2026_01"]),
    )


def _build_lifecycle_truncate(dialect: MariaDBDialect):
    return MariaDBTruncatePartitionExpression(
        dialect,
        Table(dialect, "events"),
        ["p2026_03"],
    )


def _build_lifecycle_reorganize(dialect: MariaDBDialect):
    return MariaDBReorganizePartitionExpression(
        dialect,
        Table(dialect, "events"),
        "p2026_03",
        [
            _range_definition(dialect, "p2026_03a", "2026-03-15"),
            _range_definition(dialect, "p2026_03b", "2026-04-01"),
        ],
    )


def _build_lifecycle_remove(dialect: MariaDBDialect):
    return MariaDBRemovePartitioningExpression(dialect, Table(dialect, "events"))


def _build_lifecycle_coalesce(dialect: MariaDBDialect):
    return MariaDBCoalescePartitionExpression(
        dialect,
        Table(dialect, "events"),
        2,
    )


def _build_lifecycle_actions(dialect: MariaDBDialect):
    table = Table(dialect, "events")
    return (
        MariaDBAnalyzePartitionExpression(dialect, table, ["p0"]),
        MariaDBCheckPartitionExpression(dialect, table, ["p0"]),
        MariaDBOptimizePartitionExpression(dialect, table, ["p0"]),
        MariaDBRebuildPartitionExpression(dialect, table, ["p0"]),
        MariaDBRepairPartitionExpression(dialect, table, ["p0"]),
    )


def _build_get_partitions(dialect: MariaDBDialect):
    return MariaDBGetPartitionsExpression(dialect, "events")


def _build_list_plan(dialect: MariaDBDialect) -> MariaDBPartitionPlan:
    return MariaDBPartitionPlan(
        "events",
        (
            MariaDBPartitionDefinition(
                name="p_east",
                in_values=[_value(dialect, "east")],
            ),
            MariaDBPartitionDefinition(
                name="p_west",
                in_values=[_value(dialect, "west")],
            ),
        ),
    )


def _build_mixed_plan(dialect: MariaDBDialect) -> MariaDBPartitionPlan:
    return MariaDBPartitionPlan(
        "events",
        (
            _range_definition(dialect, "p2026", "2027-01-01"),
            MariaDBPartitionDefinition(
                name="p_east",
                in_values=[_value(dialect, "east")],
            ),
        ),
    )


def _build_range_maxvalue_plan(dialect: MariaDBDialect) -> MariaDBPartitionPlan:
    return MariaDBPartitionPlan(
        "events",
        (
            _range_definition(dialect, "p2026", "2027-01-01"),
            _range_definition(dialect, "p2027", "2028-01-01"),
            _maxvalue_definition(dialect, "pmax"),
        ),
    )


def _build_invalid_maxvalue_plan(dialect: MariaDBDialect) -> MariaDBPartitionPlan:
    return MariaDBPartitionPlan(
        "events",
        (
            _maxvalue_definition(dialect, "pmax"),
            _range_definition(dialect, "p2026", "2027-01-01"),
        ),
    )


def _build_maintenance_plan(dialect: MariaDBDialect) -> MariaDBPartitionPlan:
    return MariaDBPartitionPlan(
        "events",
        (
            _range_definition(dialect, "p2026_01", "2026-02-01"),
            _range_definition(dialect, "p2026_02", "2026-03-01"),
            _range_definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )


CASES: Tuple[PartitionSyntaxCase, ...] = (
    PartitionSyntaxCase(
        name="range",
        description="RANGE partitioning terminated by a MAXVALUE partition",
        builders=(_build_range,),
        required_fragments=(
            "PARTITION BY RANGE (`created_at`)",
            "PARTITION `p0` VALUES LESS THAN ('2024-01-01')",
            "PARTITION `pmax` VALUES LESS THAN (MAXVALUE)",
        ),
        forbidden_fragments=("RANGE COLUMNS", "VALUES IN", "PARTITIONS 4"),
    ),
    PartitionSyntaxCase(
        name="range_columns",
        description="RANGE COLUMNS partitioning over a column key",
        builders=(_build_range_columns,),
        required_fragments=(
            "PARTITION BY RANGE COLUMNS (`a`)",
            "PARTITION `p0` VALUES LESS THAN (10)",
        ),
        forbidden_fragments=("PARTITION BY RANGE (`a`)", "VALUES IN"),
    ),
    PartitionSyntaxCase(
        name="list",
        description="Single-column LIST partitioning",
        builders=(_build_list,),
        required_fragments=(
            "PARTITION BY LIST (`region`)",
            "PARTITION `p_east` VALUES IN ('east')",
        ),
        forbidden_fragments=("LIST COLUMNS", "VALUES LESS THAN"),
        plan_builder=_build_list_plan,
        existing_partitions=("p_east",),
        expected_additions=("p_west",),
        invalid_plan_builder=_build_mixed_plan,
        invalid_plan_error="either less_than",
    ),
    PartitionSyntaxCase(
        name="list_columns",
        description="Multi-column LIST COLUMNS partitioning",
        builders=(_build_list_columns,),
        required_fragments=(
            "PARTITION BY LIST COLUMNS (`a`, `b`)",
            "VALUES IN (('a', 'x'), ('b', 'y'))",
        ),
        forbidden_fragments=("VALUES LESS THAN",),
    ),
    PartitionSyntaxCase(
        name="hash",
        description="HASH partitioning with a partition count",
        builders=(_build_hash,),
        required_fragments=("PARTITION BY HASH (`id`) PARTITIONS 4",),
        forbidden_fragments=("LINEAR", "SUBPARTITION"),
    ),
    PartitionSyntaxCase(
        name="key",
        description="KEY partitioning with an empty key list and a count",
        builders=(_build_key,),
        required_fragments=("PARTITION BY KEY () PARTITIONS 2",),
        forbidden_fragments=("LINEAR", "SUBPARTITION"),
    ),
    PartitionSyntaxCase(
        name="linear_hash",
        description="LINEAR HASH partitioning with a partition count",
        builders=(_build_linear_hash,),
        required_fragments=("PARTITION BY LINEAR HASH (`id`) PARTITIONS 2",),
        forbidden_fragments=("PARTITION BY HASH",),
    ),
    PartitionSyntaxCase(
        name="linear_key",
        description="LINEAR KEY partitioning with an explicit key and count",
        builders=(_build_linear_key,),
        required_fragments=("PARTITION BY LINEAR KEY (`id`) PARTITIONS 2",),
        forbidden_fragments=("PARTITION BY KEY",),
    ),
    PartitionSyntaxCase(
        name="range_maxvalue",
        description="MAXVALUE is the last RANGE boundary and plan validation",
        builders=(_build_range,),
        required_fragments=("PARTITION `pmax` VALUES LESS THAN (MAXVALUE)",),
        ordered_fragments=("PARTITION `p0`", "PARTITION `pmax`", "MAXVALUE"),
        forbidden_fragments=("VALUES IN",),
        plan_builder=_build_range_maxvalue_plan,
        existing_partitions=("p2026", "pmax"),
        expected_skipped=("p2027",),
        invalid_plan_builder=_build_invalid_maxvalue_plan,
        invalid_plan_error="MAXVALUE partition must be the last",
    ),
    PartitionSyntaxCase(
        name="hash_subpartition",
        description="RANGE with SUBPARTITION BY HASH and explicit subpartitions",
        builders=(_build_hash_subpartition,),
        required_fragments=(
            "PARTITION BY RANGE (`created_at`) SUBPARTITION BY HASH "
            "(`tenant_id`) SUBPARTITIONS 2",
            "SUBPARTITION `p2026_s0`",
            "SUBPARTITION `p2026_s1`",
        ),
        forbidden_fragments=("SUBPARTITION BY RANGE", "SUBPARTITION BY LIST"),
    ),
    PartitionSyntaxCase(
        name="key_subpartition",
        description="RANGE with SUBPARTITION BY KEY and an explicit key expression",
        builders=(_build_key_subpartition,),
        required_fragments=("SUBPARTITION BY KEY (`id`) SUBPARTITIONS 2",),
        forbidden_fragments=(
            "SUBPARTITION BY HASH",
            "SUBPARTITION BY RANGE",
            "SUBPARTITION BY LIST",
        ),
    ),
    PartitionSyntaxCase(
        name="range_subpartition_refused",
        description="SUBPARTITION BY RANGE is refused by name",
        refusal_builder=_refuse_range_subpartition,
        refused_feature="SUBPARTITION BY RANGE",
    ),
    PartitionSyntaxCase(
        name="list_subpartition_refused",
        description="SUBPARTITION BY LIST is refused by name",
        refusal_builder=_refuse_list_subpartition,
        refused_feature="SUBPARTITION BY LIST",
    ),
    PartitionSyntaxCase(
        name="partition_options",
        description="Typed partition options are rendered in keyword order",
        builders=(_build_partition_options,),
        required_fragments=(
            "PARTITION `p0` VALUES LESS THAN (1) ENGINE `InnoDB` "
            "COMMENT 'first' MAX_ROWS 1000 TABLESPACE `ts_hot`",
        ),
        forbidden_fragments=("DATA DIRECTORY", "INDEX DIRECTORY"),
    ),
    PartitionSyntaxCase(
        name="lifecycle_add_drop",
        description="ADD PARTITION and DROP PARTITION statements",
        builders=(_build_lifecycle_add_drop,),
        required_fragments=(
            "ALTER TABLE `events` ADD PARTITION",
            "ALTER TABLE `events` DROP PARTITION `p2026_01`",
        ),
        forbidden_fragments=("TRUNCATE PARTITION", "REORGANIZE PARTITION"),
    ),
    PartitionSyntaxCase(
        name="lifecycle_truncate",
        description="TRUNCATE PARTITION statement",
        builders=(_build_lifecycle_truncate,),
        required_fragments=("ALTER TABLE `events` TRUNCATE PARTITION `p2026_03`",),
        forbidden_fragments=("DROP PARTITION",),
    ),
    PartitionSyntaxCase(
        name="lifecycle_reorganize",
        description="REORGANIZE PARTITION ... INTO replacement definitions",
        builders=(_build_lifecycle_reorganize,),
        required_fragments=(
            "ALTER TABLE `events` REORGANIZE PARTITION `p2026_03` INTO",
            "PARTITION `p2026_03a` VALUES LESS THAN ('2026-03-15')",
            "PARTITION `p2026_03b` VALUES LESS THAN ('2026-04-01')",
        ),
        forbidden_fragments=("DROP PARTITION",),
    ),
    PartitionSyntaxCase(
        name="lifecycle_remove",
        description="REMOVE PARTITIONING statement",
        builders=(_build_lifecycle_remove,),
        required_fragments=("ALTER TABLE `events` REMOVE PARTITIONING",),
        forbidden_fragments=("ADD PARTITION", "DROP PARTITION"),
    ),
    PartitionSyntaxCase(
        name="lifecycle_coalesce",
        description="COALESCE PARTITION statement",
        builders=(_build_lifecycle_coalesce,),
        required_fragments=("ALTER TABLE `events` COALESCE PARTITION 2",),
        forbidden_fragments=("ADD PARTITION", "DROP PARTITION"),
    ),
    PartitionSyntaxCase(
        name="lifecycle_analyze_check_optimize_rebuild_repair",
        description="The five ALTER TABLE maintenance actions",
        builders=(_build_lifecycle_actions,),
        required_fragments=(
            "ANALYZE PARTITION `p0`",
            "CHECK PARTITION `p0`",
            "OPTIMIZE PARTITION `p0`",
            "REBUILD PARTITION `p0`",
            "REPAIR PARTITION `p0`",
        ),
        forbidden_fragments=("DROP PARTITION", "TRUNCATE PARTITION"),
    ),
    PartitionSyntaxCase(
        name="lifecycle_get_partitions",
        description="GET PARTITIONS reads information_schema.PARTITIONS",
        builders=(_build_get_partitions,),
        required_fragments=(
            "FROM `information_schema`.`PARTITIONS`",
            "`PARTITION_NAME`",
            "`PARTITION_METHOD`",
            "`PARTITION_DESCRIPTION`",
            "ORDER BY `PARTITION_NAME` ASC",
        ),
        forbidden_fragments=("PARTITION BY",),
        expected_params=("events",),
    ),
    PartitionSyntaxCase(
        name="maintenance_ensure_list_drop_before",
        description="Plan, ensure, list, and drop_before with a fake backend",
        plan_builder=_build_maintenance_plan,
        existing_partitions=("p2026_01",),
        expected_additions=("p2026_02", "p2026_03"),
        drop_cutoff=date(2026, 3, 1),
        expected_dropped=("p2026_01", "p2026_02"),
        exercise_maintenance=True,
    ),
)


@pytest.fixture(params=CASES, ids=[case.name for case in CASES])
def partition_syntax_case(request: pytest.FixtureRequest) -> PartitionSyntaxCase:
    """Yield each row of the MariaDB partition syntax matrix."""
    return request.param
