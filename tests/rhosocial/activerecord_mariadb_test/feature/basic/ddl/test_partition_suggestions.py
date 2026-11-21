# tests/rhosocial/activerecord_mariadb_test/feature/basic/ddl/test_partition_suggestions.py
"""Contract tests for MariaDB's eight partition lifecycle suggestions.

The dialect must answer all eight backend-suggestion protocols with real
expression nodes (or an explicit ``False``/``None`` tri-state), and the
expressions must be MariaDB-owned nodes that render through the dialect.
"""

import dataclasses

from rhosocial.activerecord.backend.dialect.protocols import (
    PartitionAddSuggestionSupport,
    PartitionBuildSuggestionSupport,
    PartitionDropSuggestionSupport,
    PartitionMergeSuggestionSupport,
    PartitionRetentionSuggestionSupport,
    PartitionSplitSuggestionSupport,
    PartitionTableAlterSuggestionSupport,
    PartitionTableDropSuggestionSupport,
)
from rhosocial.activerecord.backend.expression import (
    BaseExpression,
    Column,
    DropTableStatement,
)
from rhosocial.activerecord.backend.expression.statements import (
    PartitionByHashClause,
    PartitionByListClause,
    PartitionByRangeClause,
    PartitionDefinitionExpression,
)
from rhosocial.activerecord.backend.suggestion import (
    PartitionAddSuggestion,
    PartitionBuildSuggestion,
    PartitionDropSuggestion,
    PartitionMergeSuggestion,
    PartitionRetentionSuggestion,
    PartitionSplitSuggestion,
    PartitionTableAlterSuggestion,
    PartitionTableDropSuggestion,
    PartitionSuggestionRenderer,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBAddPartitionExpression,
    MariaDBCoalescePartitionExpression,
    MariaDBDropPartitionExpression,
    MariaDBPartitionByHash,
    MariaDBPartitionByKey,
    MariaDBPartitionByList,
    MariaDBPartitionByListColumns,
    MariaDBPartitionByRange,
    MariaDBPartitionByRangeColumns,
    MariaDBPartitionValue,
    MariaDBRemovePartitioningExpression,
    MariaDBReorganizePartitionExpression,
)


@dataclasses.dataclass(frozen=True)
class _Plan:
    """Minimal caller-owned plan; suggestions read it by attribute, not type."""

    table: str
    definitions: tuple


#: (method suffix, protocol, suggestion dataclass, renderer intent)
POINTS = (
    ("build", PartitionBuildSuggestionSupport, PartitionBuildSuggestion, "build"),
    (
        "table_drop",
        PartitionTableDropSuggestionSupport,
        PartitionTableDropSuggestion,
        "table_drop",
    ),
    (
        "table_alter",
        PartitionTableAlterSuggestionSupport,
        PartitionTableAlterSuggestion,
        "table_alter",
    ),
    ("add", PartitionAddSuggestionSupport, PartitionAddSuggestion, "add"),
    ("drop", PartitionDropSuggestionSupport, PartitionDropSuggestion, "drop"),
    ("split", PartitionSplitSuggestionSupport, PartitionSplitSuggestion, "split"),
    ("merge", PartitionMergeSuggestionSupport, PartitionMergeSuggestion, "merge"),
    (
        "retention",
        PartitionRetentionSuggestionSupport,
        PartitionRetentionSuggestion,
        "retention",
    ),
)

RANGE_PLAN_KINDS = ("RANGE", "RANGE COLUMNS")
HASH_PLAN_KINDS = ("HASH", "LINEAR HASH", "KEY", "LINEAR KEY")
ALL_KINDS = (
    "RANGE",
    "RANGE COLUMNS",
    "LIST",
    "LIST COLUMNS",
    "HASH",
    "LINEAR HASH",
    "KEY",
    "LINEAR KEY",
)


def _dialect():
    return MariaDBDialect()


def _plan(dialect, kind="RANGE"):
    """Build a small real RANGE plan; LIST/HASH share its definitions/tail."""
    if kind.startswith("LIST"):
        definitions = (
            PartitionDefinitionExpression(
                dialect, "p_east", in_values=(MariaDBPartitionValue(dialect, "east"),)
            ),
            PartitionDefinitionExpression(
                dialect, "p_west", in_values=(MariaDBPartitionValue(dialect, "west"),)
            ),
        )
    else:
        definitions = (
            PartitionDefinitionExpression(
                dialect, "p0", less_than=(MariaDBPartitionValue(dialect, 10),)
            ),
            PartitionDefinitionExpression(
                dialect, "p1", less_than=(MariaDBPartitionValue(dialect, 20),)
            ),
        )
    return _Plan("events", definitions)


def _strategy(dialect, word):
    """Build the strategy clause node for ``word``.

    RANGE/LIST/HASH have dedicated core clause nodes. MariaDB's other five
    spellings (the COLUMNS and LINEAR variants) still travel as words, which
    the suggestion helper accepts for backward compatibility.
    """
    keys = (Column(dialect, "id"),)
    if word == "RANGE":
        return PartitionByRangeClause(dialect, keys)
    if word == "LIST":
        return PartitionByListClause(dialect, keys)
    if word == "HASH":
        return PartitionByHashClause(dialect, keys)
    return word


def _suggest(dialect, name, strategy, plan):
    node = _strategy(dialect, strategy) if isinstance(strategy, str) else strategy
    return getattr(dialect, f"suggest_partition_{name}")(node, plan)


def test_dialect_satisfies_all_eight_protocols():
    dialect = _dialect()
    for _, protocol, _, _ in POINTS:
        assert isinstance(dialect, protocol)


def test_suggestions_accept_a_strategy_clause_node():
    dialect = _dialect()
    strategy = PartitionByRangeClause(dialect, [Column(dialect, "id")])
    plan = _plan(dialect)
    for name, _, suggestion_type, _ in POINTS:
        assert isinstance(_suggest(dialect, name, strategy, plan), suggestion_type)


def test_suggestion_values_are_frozen_tri_state():
    for _, _, suggestion_type, _ in POINTS:
        value = suggestion_type()
        assert dataclasses.is_dataclass(value)
        assert value.operations is None
        assert suggestion_type(False).operations is False
        try:
            value.operations = False  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            pass
        else:
            raise AssertionError(f"{suggestion_type.__name__} must be frozen")


def test_each_point_returns_its_own_suggestion_type():
    dialect = _dialect()
    plan = _plan(dialect)
    for name, _, suggestion_type, _ in POINTS:
        assert isinstance(_suggest(dialect, name, "RANGE", plan), suggestion_type)


def test_build_returns_real_clause_for_every_mariaDB_strategy():
    dialect = _dialect()
    expected = {
        "RANGE": MariaDBPartitionByRange,
        "RANGE COLUMNS": MariaDBPartitionByRangeColumns,
        "LIST": MariaDBPartitionByList,
        "LIST COLUMNS": MariaDBPartitionByListColumns,
        "HASH": MariaDBPartitionByHash,
        "LINEAR HASH": MariaDBPartitionByHash,
        "KEY": MariaDBPartitionByKey,
        "LINEAR KEY": MariaDBPartitionByKey,
    }
    for strategy, clause_type in expected.items():
        plan = _plan(dialect, strategy)
        operations = _suggest(dialect, "build", strategy, plan).operations
        assert isinstance(operations, tuple) and len(operations) == 1
        assert isinstance(operations[0], clause_type)
        sql, _ = operations[0].to_sql()
        assert "PARTITION BY" in sql


def test_build_returns_false_for_unknown_strategy():
    assert _suggest(_dialect(), "build", "NOT A STRATEGY", None).operations is False


def test_table_drop_unpartitions_then_drops_table():
    dialect = _dialect()
    operations = _suggest(dialect, "table_drop", "RANGE", _plan(dialect)).operations
    assert isinstance(operations, tuple) and len(operations) == 2
    assert isinstance(operations[0], MariaDBRemovePartitioningExpression)
    assert isinstance(operations[1], DropTableStatement)
    sql, _ = operations[0].to_sql()
    assert "REMOVE PARTITIONING" in sql
    sql, _ = operations[1].to_sql()
    assert "DROP TABLE" in sql


def test_table_alter_uses_coalesce_for_hash_and_remove_for_range():
    dialect = _dialect()
    plan = _plan(dialect)
    for strategy in HASH_PLAN_KINDS:
        operations = _suggest(dialect, "table_alter", strategy, plan).operations
        assert isinstance(operations, tuple) and len(operations) == 1
        assert isinstance(operations[0], MariaDBCoalescePartitionExpression)
    for strategy in RANGE_PLAN_KINDS + ("LIST", "LIST COLUMNS"):
        operations = _suggest(dialect, "table_alter", strategy, plan).operations
        assert isinstance(operations, tuple) and len(operations) == 1
        assert isinstance(operations[0], MariaDBRemovePartitioningExpression)
    assert _suggest(dialect, "table_alter", "NOT A STRATEGY", plan).operations is False


def test_add_drop_split_return_their_real_statements():
    dialect = _dialect()
    plan = _plan(dialect)
    add = _suggest(dialect, "add", "RANGE", plan).operations
    drop = _suggest(dialect, "drop", "RANGE", plan).operations
    split = _suggest(dialect, "split", "RANGE", plan).operations
    assert isinstance(add, tuple) and isinstance(add[0], MariaDBAddPartitionExpression)
    assert isinstance(drop, tuple) and isinstance(drop[0], MariaDBDropPartitionExpression)
    assert isinstance(split, tuple) and isinstance(split[0], MariaDBReorganizePartitionExpression)
    assert "ADD PARTITION" in add[0].to_sql()[0]
    assert "DROP PARTITION" in drop[0].to_sql()[0]
    assert "REORGANIZE PARTITION" in split[0].to_sql()[0]


def test_merge_is_explicitly_unsupported():
    dialect = _dialect()
    for strategy in ALL_KINDS:
        assert _suggest(dialect, "merge", strategy, _plan(dialect)).operations is False


def test_retention_drops_each_range_definition_by_less_than():
    dialect = _dialect()
    range_operations = _suggest(dialect, "retention", "RANGE", _plan(dialect)).operations
    assert isinstance(range_operations, tuple) and len(range_operations) == 2
    assert all(isinstance(op, MariaDBDropPartitionExpression) for op in range_operations)
    assert [op.partitions for op in range_operations] == [["p0"], ["p1"]]
    for strategy in ("LIST", "LIST COLUMNS") + HASH_PLAN_KINDS:
        assert (
            _suggest(dialect, "retention", strategy, _plan(dialect, strategy)).operations is False
        )


def test_false_states_are_explicit_for_unsupported_strategies():
    dialect = _dialect()
    for name, _, _, _ in POINTS:
        if name == "table_drop":
            continue
        assert _suggest(dialect, name, "WRONG", _plan(dialect)).operations is False


def test_renderer_parts_collect_the_real_expressions():
    dialect = _dialect()
    plan = _plan(dialect)
    renderer = PartitionSuggestionRenderer()
    for name, _, _, intent in POINTS:
        result = renderer.parts(dialect, intent, _strategy(dialect, "RANGE"), plan)
        if name == "merge":
            assert result is None
            continue
        assert isinstance(result, list) and result
        assert all(isinstance(expr, BaseExpression) for expr in result)


def test_build_expression_carries_plan_keys_and_definitions():
    dialect = _dialect()
    plan = _plan(dialect)
    clause = _suggest(dialect, "build", "RANGE", plan).operations[0]
    assert [key.to_sql() for key in clause.keys] == [Column(dialect, "id").to_sql()]
    assert [definition.name for definition in clause.partitions] == ["p0", "p1"]
