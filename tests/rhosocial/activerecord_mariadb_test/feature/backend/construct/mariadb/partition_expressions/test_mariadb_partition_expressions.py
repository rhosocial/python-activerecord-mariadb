# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/mariadb/partition_expressions/test_mariadb_partition_expressions.py  # noqa: E501
"""Tests for MariaDB-owned partition DDL expressions and their formatting."""

import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import (
    PartitionDefinitionExpression,
    PartitionOptionsExpression,
    SubpartitionDefinitionExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition import (
    MariaDBPartitionByHash,
    MariaDBPartitionByKey,
    MariaDBPartitionByList,
    MariaDBPartitionByListColumns,
    MariaDBPartitionByRange,
    MariaDBPartitionByRangeColumns,
    MariaDBPartitionMaxValue,
    MariaDBPartitionValue,
)


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

    return MariaDBDialect(version=(10, 6, 0))


def _value(dialect, value):
    return MariaDBPartitionValue(dialect, value)


# ---------------------------------------------------------------------------
# Definitions are core expression nodes
# ---------------------------------------------------------------------------


def test_partition_definition_is_expression_node(dialect):
    definition = PartitionDefinitionExpression(dialect, name="p0", less_than=[object()])
    assert isinstance(definition, PartitionDefinitionExpression)


def test_subpartition_definition_is_expression_node(dialect):
    assert isinstance(
        SubpartitionDefinitionExpression(dialect, name="sp0"), SubpartitionDefinitionExpression
    )


def test_partition_definition_requires_boundary(dialect):
    definition = PartitionDefinitionExpression(dialect, "p0")
    with pytest.raises(ValueError, match="less_than or in_values"):
        dialect.render_partition_definition(definition)


def test_partition_definition_rejects_both_boundaries(dialect):
    with pytest.raises(ValueError, match="mutually exclusive"):
        PartitionDefinitionExpression(
            dialect, name="p0", less_than=[object()], in_values=[object()]
        )


# ---------------------------------------------------------------------------
# Clause rendering
# ---------------------------------------------------------------------------


def test_partition_by_range_with_definitions(dialect):
    expr = MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            PartitionDefinitionExpression(dialect, "p0", less_than=[_value(dialect, "2024-01-01")]),
            PartitionDefinitionExpression(
                dialect, "pmax", less_than=[MariaDBPartitionMaxValue(dialect)]
            ),
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
            PartitionDefinitionExpression(
                dialect,
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
            PartitionDefinitionExpression(dialect, "p0", in_values=[_value(dialect, "east")])
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
    assert dialect.format_partition_max_value(MariaDBPartitionMaxValue(dialect)) == (
        "MAXVALUE",
        (),
    )


def test_partition_boundary_kinds_name_their_own_formatter(dialect):
    """A value and the MAXVALUE token are distinct kinds, not one formatter.

    The value node carries a literal; the MAXVALUE node is the bare word and
    is the piece the server's RANGE grammar gates. Each names its own
    formatter, and neither formatter inspects the sibling class -- a
    structure-level assertion, because the rendered words alone would stay
    identical while the dispatch silently regressed.
    """
    import inspect

    max_value = MariaDBPartitionMaxValue(dialect)
    value = _value(dialect, 42)

    assert max_value.format_method == "format_partition_max_value"
    assert value.format_method == "format_partition_value"
    assert max_value.format_method != value.format_method

    assert max_value.to_sql() == ("MAXVALUE", ())
    assert value.to_sql() == ("42", ())

    max_source = inspect.getsource(type(dialect).format_partition_max_value)
    value_source = inspect.getsource(type(dialect).format_partition_value)
    assert "MariaDBPartitionValue" not in max_source
    assert "MariaDBPartitionMaxValue" not in value_source


def test_partition_value_rejects_bool(dialect):
    with pytest.raises(TypeError, match="bool"):
        dialect.format_partition_value(_value(dialect, True))


def test_partition_definition_options(dialect):
    expr = MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "a")],
        partitions=[
            PartitionDefinitionExpression(
                dialect,
                "p0",
                less_than=[_value(dialect, 1)],
                options=PartitionOptionsExpression(dialect, {"comment": "first"}),
            )
        ],
    )
    sql, _ = expr.to_sql()
    assert sql.endswith("PARTITION `p0` VALUES LESS THAN (1) COMMENT 'first')")


def test_partition_definition_options_are_formatted(dialect):
    definition = PartitionDefinitionExpression(
        dialect,
        "p0",
        less_than=[_value(dialect, 1)],
        options=PartitionOptionsExpression(
            dialect,
            {
                "engine": "InnoDB",
                "comment": "tenant's partition",
                "max_rows": 1000,
                "tablespace": "ts_hot",
            },
        ),
    )
    sql, params = dialect.render_partition_definition(definition)
    assert "ENGINE" in sql and "InnoDB" in sql
    assert "COMMENT" in sql and "tenant''s partition" in sql
    assert "MAX_ROWS 1000" in sql
    assert "TABLESPACE" in sql and "ts_hot" in sql
    assert params == ()


def test_partition_definition_options_reject_invalid_options(dialect):
    with pytest.raises(TypeError, match="engine option must be a non-empty string"):
        dialect.render_partition_definition_options(
            PartitionOptionsExpression(dialect, {"engine": ""})
        )
    with pytest.raises(TypeError, match="max_rows option"):
        dialect.render_partition_definition_options(
            PartitionOptionsExpression(dialect, {"max_rows": -1})
        )


def test_partition_definition_rejects_invalid_partition_options(dialect):
    with pytest.raises(TypeError, match="partition_options must be a PartitionOptionsExpression"):
        dialect.render_partition_definition_options("invalid")


def test_partition_definition_with_subpartitions(dialect):
    expr = MariaDBPartitionByRange(
        dialect,
        [Column(dialect, "a")],
        partitions=[
            PartitionDefinitionExpression(
                dialect,
                "p0",
                less_than=[_value(dialect, 1)],
                subpartitions=[SubpartitionDefinitionExpression(dialect, name="s0")],
            )
        ],
    )
    sql, _ = expr.to_sql()
    assert sql.endswith("(PARTITION `p0` VALUES LESS THAN (1) (SUBPARTITION `s0`))")


def test_subpartition_definition_empty_name(dialect):
    with pytest.raises(ValueError, match="non-empty string"):
        SubpartitionDefinitionExpression(dialect, name="")


# ---------------------------------------------------------------------------
# Capability gating
# ---------------------------------------------------------------------------


def test_partition_clause_unsupported_method(dialect):
    from rhosocial.activerecord.backend.expression import PartitionClause

    clause = PartitionClause(dialect, "RANGE", [Column(dialect, "a")])
    clause.method = "BOGUS"
    with pytest.raises(ValueError, match="Invalid MariaDB partition method"):
        dialect.format_partition_clause(clause)
