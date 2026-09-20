# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_partition_expressions.py
"""Tests for MariaDB-owned partition DDL expressions and their formatting."""

import pytest

from rhosocial.activerecord.backend.expression import Column, PartitionDefinition
from rhosocial.activerecord.backend.expression.statements import SubpartitionDefinition
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBPartitionByHash,
    MariaDBPartitionByKey,
    MariaDBPartitionByList,
    MariaDBPartitionByListColumns,
    MariaDBPartitionByRange,
    MariaDBPartitionByRangeColumns,
    MariaDBPartitionDefinition,
    MariaDBPartitionMaxValue,
    MariaDBPartitionValue,
    MariaDBSubpartitionDefinition,
)


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

    return MariaDBDialect(version=(10, 6, 0))


def _value(dialect, value):
    return MariaDBPartitionValue(dialect, value)


# ---------------------------------------------------------------------------
# Definitions derive from the generic declarations
# ---------------------------------------------------------------------------


def test_partition_definition_derives_generic():
    definition = MariaDBPartitionDefinition(name="p0", less_than=[object()])
    assert isinstance(definition, PartitionDefinition)


def test_subpartition_definition_derives_generic():
    assert isinstance(MariaDBSubpartitionDefinition(name="sp0"), SubpartitionDefinition)


def test_partition_definition_requires_boundary():
    with pytest.raises(ValueError, match="less_than or in_values"):
        MariaDBPartitionDefinition(name="p0")


def test_partition_definition_rejects_both_boundaries():
    with pytest.raises(ValueError, match="mutually exclusive"):
        MariaDBPartitionDefinition(name="p0", less_than=[object()], in_values=[object()])


# ---------------------------------------------------------------------------
# Clause rendering
# ---------------------------------------------------------------------------


def test_partition_by_range_with_definitions(dialect):
    expr = MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            MariaDBPartitionDefinition("p0", less_than=[_value(dialect, "2024-01-01")]),
            MariaDBPartitionDefinition("pmax", less_than=[MariaDBPartitionMaxValue(dialect)]),
        ],
    )
    sql, _ = expr.to_sql()
    assert sql == (
        " PARTITION BY RANGE (`created_at`) "
        "(PARTITION `p0` VALUES LESS THAN ('2024-01-01'), "
        "PARTITION `pmax` VALUES LESS THAN (MAXVALUE))"
    )


def test_partition_by_range_columns(dialect):
    sql, _ = MariaDBPartitionByRangeColumns(dialect, [Column(dialect, "a")]).to_sql()
    assert sql == " PARTITION BY RANGE COLUMNS (`a`)"


def test_partition_by_list_columns_multi_column(dialect):
    expr = MariaDBPartitionByListColumns(
        dialect,
        [Column(dialect, "a"), Column(dialect, "b")],
        partitions=[
            MariaDBPartitionDefinition(
                "p0",
                in_values=[
                    [_value(dialect, "a"), _value(dialect, "x")],
                    [_value(dialect, "b"), _value(dialect, "y")],
                ],
            )
        ],
    )
    sql, _ = expr.to_sql()
    assert sql == (
        " PARTITION BY LIST COLUMNS (`a`, `b`) "
        "(PARTITION `p0` VALUES IN (('a', 'x'), ('b', 'y')))"
    )


def test_partition_by_list_single_column(dialect):
    expr = MariaDBPartitionByList(
        dialect,
        [Column(dialect, "region")],
        partitions=[
            MariaDBPartitionDefinition("p0", in_values=[_value(dialect, "east")])
        ],
    )
    sql, _ = expr.to_sql()
    assert sql == " PARTITION BY LIST (`region`) (PARTITION `p0` VALUES IN ('east'))"


def test_partition_by_hash_with_count(dialect):
    sql, _ = MariaDBPartitionByHash(dialect, [Column(dialect, "id")], partitions_count=4).to_sql()
    assert sql == " PARTITION BY HASH (`id`) PARTITIONS 4"


def test_partition_by_linear_hash(dialect):
    sql, _ = MariaDBPartitionByHash(
        dialect, [Column(dialect, "id")], partitions_count=2, linear=True
    ).to_sql()
    assert sql == " PARTITION BY LINEAR HASH (`id`) PARTITIONS 2"


def test_partition_by_key_empty(dialect):
    sql, _ = MariaDBPartitionByKey(dialect, partitions_count=2).to_sql()
    assert sql == " PARTITION BY KEY () PARTITIONS 2"


def test_partition_by_hash_invalid_count(dialect):
    with pytest.raises(ValueError, match="positive integer"):
        MariaDBPartitionByHash(dialect, [Column(dialect, "id")], partitions_count=0).to_sql()


# ---------------------------------------------------------------------------
# Values, options, subpartitions
# ---------------------------------------------------------------------------


def test_partition_value_formats(dialect):
    assert dialect.format_partition_value(_value(dialect, None)) == ("NULL", ())
    assert dialect.format_partition_value(_value(dialect, 42)) == ("42", ())
    assert dialect.format_partition_value(_value(dialect, "o'brien")) == ("'o''brien'", ())
    assert dialect.format_partition_value(MariaDBPartitionMaxValue(dialect)) == ("MAXVALUE", ())


def test_partition_value_rejects_bool(dialect):
    with pytest.raises(TypeError, match="bool"):
        dialect.format_partition_value(_value(dialect, True))


def test_partition_definition_options(dialect):
    expr = MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "a")],
        partitions=[
            MariaDBPartitionDefinition(
                "p0",
                less_than=[_value(dialect, 1)],
                dialect_options={"comment": "first"},
            )
        ],
    )
    sql, _ = expr.to_sql()
    assert sql.endswith("PARTITION `p0` VALUES LESS THAN (1) COMMENT 'first')")


def test_partition_definition_rejects_unknown_option(dialect):
    expr = MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "a")],
        partitions=[
            MariaDBPartitionDefinition(
                "p0", less_than=[_value(dialect, 1)], dialect_options={"bogus": 1}
            )
        ],
    )
    with pytest.raises(ValueError, match="Unsupported partition definition option"):
        expr.to_sql()


def test_partition_definition_with_subpartitions(dialect):
    expr = MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "a")],
        partitions=[
            MariaDBPartitionDefinition(
                "p0",
                less_than=[_value(dialect, 1)],
                subpartition_definitions=[MariaDBSubpartitionDefinition(name="s0")],
            )
        ],
    )
    sql, _ = expr.to_sql()
    assert sql.endswith("(PARTITION `p0` VALUES LESS THAN (1) (SUBPARTITION `s0`))")


def test_subpartition_definition_empty_name():
    with pytest.raises(ValueError, match="non-empty string"):
        MariaDBSubpartitionDefinition(name="")


# ---------------------------------------------------------------------------
# Capability gating
# ---------------------------------------------------------------------------


def test_partition_clause_unsupported_method(dialect):
    from rhosocial.activerecord.backend.expression import PartitionClause

    clause = PartitionClause(dialect, "RANGE", [Column(dialect, "a")])
    clause.method = "BOGUS"
    with pytest.raises(ValueError, match="Invalid MariaDB partition method"):
        dialect.format_partition_clause(clause)
