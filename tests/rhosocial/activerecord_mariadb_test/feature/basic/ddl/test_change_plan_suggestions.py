# tests/rhosocial/activerecord_mariadb_test/feature/basic/ddl/test_change_plan_suggestions.py
"""Contract tests for MariaDB's four change-plan suggestion protocols.

Each point is answered with a tri-state value: a tuple of real expression
nodes, or ``False`` when the MariaDB grammar / existing node set cannot express
the change, or ``None`` when nothing needs doing. Tests here pin the exact
rendered SQL of every supported chain and record the evidence behind each
refusal.
"""

import inspect
import re

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import (
    AddIndexAction,
    AddTableConstraintAction,
    ColumnDefinition,
    DropIndexAction,
    DropTableConstraintAction,
    IndexDefinition,
    TableConstraint,
    TableExcludeConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import ModifyColumnAction
from rhosocial.activerecord.backend.suggestion import (
    ColumnReorderSuggestion,
    PartitionSchemeChangeSuggestion,
    TableConstraintChangeSuggestion,
    TableIndexChangeSuggestion,
)
from rhosocial.activerecord.backend.suggestion.protocols import (
    ColumnReorderSuggestionSupport,
    PartitionSchemeChangeSuggestionSupport,
    TableConstraintChangeSuggestionSupport,
    TableIndexChangeSuggestionSupport,
)
from rhosocial.activerecord.migration.schema_change import _freeze

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBCoalescePartitionExpression,
    MariaDBDropPartitionExpression,
    MariaDBPartitionValue,
    MariaDBRemovePartitioningExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.suggestion.column_reorder_suggestion import (
    UNSUPPORTED_REASON as REORDER_REASON,
)
from rhosocial.activerecord.backend.impl.mariadb.suggestion.partition_scheme_change_suggestion import (
    ADD_SCHEME_UNSUPPORTED_REASON,
    NON_DESTRUCTIVE_EVIDENCE,
    PARTITION_REMOVAL_UNSUPPORTED_REASON,
    REBUILD_UNSUPPORTED_REASON,
)
from rhosocial.activerecord.backend.impl.mariadb.suggestion.table_constraint_change_suggestion import (
    AMBIGUOUS_BRANCH_REASON,
)


def _dialect(version=(13, 1, 1)):
    return MariaDBDialect(version=version)


def _sql(operations):
    return [operation.to_sql()[0] for operation in operations]


def _projection(dialect, fields):
    """The shape core's ``_freeze`` gives a change point's declaration."""
    return ("params", tuple(sorted((key, _freeze(value)) for key, value in fields.items())))


def _unique(dialect, name, column):
    return TableConstraint(dialect, branch=TableUniqueConstraint(dialect, [column]), name=name)


# --- registration and the tri-state value ---------------------------------


def test_dialect_satisfies_four_change_plan_protocols():
    dialect = _dialect()
    for protocol in (
        ColumnReorderSuggestionSupport,
        TableConstraintChangeSuggestionSupport,
        TableIndexChangeSuggestionSupport,
        PartitionSchemeChangeSuggestionSupport,
    ):
        assert isinstance(dialect, protocol)


def test_all_four_answers_keep_the_frozen_tri_state():
    for cls in (
        ColumnReorderSuggestion,
        TableConstraintChangeSuggestion,
        TableIndexChangeSuggestion,
        PartitionSchemeChangeSuggestion,
    ):
        point = cls(operations=False)
        assert point.state == "unaddressable"
        assert cls(operations=None).state == "absent"
        assert cls(operations=()).state == "actions"
        try:
            point.operations = None
        except Exception as error:
            assert type(error).__name__ == "FrozenInstanceError"
        else:
            raise AssertionError(f"{cls.__name__} must be frozen")


# --- column reorder ---------------------------------------------------------


def test_column_reorder_is_explicitly_unaddressable():
    dialect = _dialect()
    point = ColumnReorderSuggestion(
        table_name="events",
        old_order=("id", "created_at"),
        new_order=("created_at", "id"),
        reordered_columns=("id", "created_at"),
    )
    answer = dialect.suggest_column_reorder(point)
    assert answer.operations is False
    assert answer.state == "unaddressable"


def test_column_reorder_refusal_evidence_is_the_missing_column_definition():
    # The point carries names only.
    point = ColumnReorderSuggestion(reordered_columns=("id", "created_at"))
    assert all(isinstance(name, str) for name in point.reordered_columns)
    # The one reorder-capable node needs a full definition, including a type.
    assert inspect.signature(ModifyColumnAction.__init__).parameters["column"].default is (
        inspect.Parameter.empty
    )
    assert inspect.signature(ColumnDefinition.__init__).parameters["data_type"].default is (
        inspect.Parameter.empty
    )
    assert "MODIFY COLUMN" in REORDER_REASON
    assert "ColumnDefinition" in REORDER_REASON
    assert "Drop + add" in REORDER_REASON


# --- table constraint change ------------------------------------------------


def test_constraint_change_renders_drop_then_add():
    dialect = _dialect()
    old = _unique(dialect, "uq_old", "id")
    new = _unique(dialect, "uq_new", "created_at")
    answer = dialect.suggest_table_constraint_change(
        TableConstraintChangeSuggestion(
            table_name="events", old_constraints=(old,), new_constraints=(new,)
        )
    )
    assert answer.state == "actions"
    assert isinstance(answer.operations[0].actions[0], DropTableConstraintAction)
    assert isinstance(answer.operations[1].actions[0], AddTableConstraintAction)
    assert _sql(answer.operations) == [
        "ALTER TABLE `events`  DROP CONSTRAINT `uq_old`",
        "ALTER TABLE `events`  ADD CONSTRAINT `uq_new` UNIQUE (`created_at`)",
    ]


def test_constraint_add_from_frozen_projection_with_explicit_kind():
    dialect = _dialect()
    projection = _projection(
        dialect,
        {
            "kind": "UNIQUE",
            "name": "uq_frozen",
            "branch": _projection(dialect, {"kind": "UNIQUE", "columns": ("created_at",)}),
        },
    )
    answer = dialect.suggest_table_constraint_change(
        TableConstraintChangeSuggestion(table_name="events", new_constraints=(projection,))
    )
    assert answer.state == "actions"
    assert _sql(answer.operations) == [
        "ALTER TABLE `events`  ADD CONSTRAINT `uq_frozen` UNIQUE (`created_at`)"
    ]


def test_constraint_drop_below_the_drop_constraint_floor_uses_drop_index():
    old_dialect = _dialect((10, 1, 4))
    assert old_dialect.supports_drop_constraint() is False
    constraint = _unique(old_dialect, "uq_old", "id")
    answer = old_dialect.suggest_table_constraint_change(
        TableConstraintChangeSuggestion(table_name="events", old_constraints=(constraint,))
    )
    assert answer.state == "actions"
    assert isinstance(answer.operations[0].actions[0], DropIndexAction)
    assert _sql(answer.operations) == ["ALTER TABLE `events`  DROP INDEX `uq_old`"]


def test_primary_key_drop_uses_drop_primary_key_on_every_version():
    for version in ((10, 1, 4), (13, 1, 1)):
        dialect = _dialect(version)
        constraint = TableConstraint(
            dialect, branch=TablePrimaryKeyConstraint(dialect, ["id"]), name="pk_x"
        )
        answer = dialect.suggest_table_constraint_change(
            TableConstraintChangeSuggestion(table_name="events", old_constraints=(constraint,))
        )
        assert answer.state == "actions"
        assert _sql(answer.operations) == ["ALTER TABLE `events`  DROP PRIMARY KEY"]


def test_ambiguous_frozen_constraint_add_is_refused():
    dialect = _dialect()
    frozen = _freeze(_unique(dialect, "uq_created", "created_at"))
    # Core's projection drops the branch class: columns alone cannot say
    # whether this is PRIMARY KEY or UNIQUE.
    assert "kind" not in frozen[1][0][1][1][0]
    answer = dialect.suggest_table_constraint_change(
        TableConstraintChangeSuggestion(table_name="events", new_constraints=(frozen,))
    )
    assert answer.operations is False
    assert "PRIMARY KEY" in AMBIGUOUS_BRANCH_REASON
    assert "UNIQUE" in AMBIGUOUS_BRANCH_REASON


def test_constraint_kinds_mariDB_has_no_add_node_for_are_refused():
    dialect = _dialect()
    exclude = TableConstraint(
        dialect,
        branch=TableExcludeConstraint(dialect, ["id"]),
        name="ex_id",
    )
    assert (
        dialect.suggest_table_constraint_change(
            TableConstraintChangeSuggestion(table_name="events", new_constraints=(exclude,))
        ).operations
        is False
    )

    frozen_check = _projection(
        dialect,
        {
            "name": "ck_id",
            "branch": _projection(dialect, {"condition": _freeze("id > 0")}),
        },
    )
    assert (
        dialect.suggest_table_constraint_change(
            TableConstraintChangeSuggestion(table_name="events", new_constraints=(frozen_check,))
        ).operations
        is False
    )


def test_constraint_traits_mariDB_cannot_spell_are_refused():
    dialect = _dialect()
    deferrable = TableConstraint(
        dialect, branch=TableUniqueConstraint(dialect, ["id"]), name="uq_id", deferrable=True
    )
    assert dialect.supports_deferrable_constraint() is False
    assert (
        dialect.suggest_table_constraint_change(
            TableConstraintChangeSuggestion(table_name="events", new_constraints=(deferrable,))
        ).operations
        is False
    )


def test_no_constraint_change_returns_none():
    dialect = _dialect()
    constraint = _unique(dialect, "uq_id", "id")
    answer = dialect.suggest_table_constraint_change(
        TableConstraintChangeSuggestion(
            table_name="events",
            old_constraints=(constraint,),
            new_constraints=(_freeze(constraint),),
        )
    )
    assert answer.operations is None
    assert answer.state == "absent"


# --- table index change -----------------------------------------------------


def test_index_change_renders_drop_then_add():
    dialect = _dialect()
    assert dialect.supports_alter_table_index_actions() is True
    old = _freeze(IndexDefinition(dialect, "idx_old", ["id"]))
    new = _freeze(IndexDefinition(dialect, "idx_new", ["created_at"]))
    answer = dialect.suggest_table_index_change(
        TableIndexChangeSuggestion(table_name="events", old_indexes=(old,), new_indexes=(new,))
    )
    assert answer.state == "actions"
    assert isinstance(answer.operations[0].actions[0], DropIndexAction)
    assert isinstance(answer.operations[1].actions[0], AddIndexAction)
    assert _sql(answer.operations) == [
        "ALTER TABLE `events`  DROP INDEX `idx_old`",
        "ALTER TABLE `events`  ADD INDEX `idx_new` (`created_at`)",
    ]


def test_no_index_change_returns_none():
    dialect = _dialect()
    index = _freeze(IndexDefinition(dialect, "idx_id", ["id"]))
    answer = dialect.suggest_table_index_change(
        TableIndexChangeSuggestion(table_name="events", old_indexes=(index,), new_indexes=(index,))
    )
    assert answer.operations is None


def test_unique_index_add_is_refused_because_add_index_action_ignores_unique():
    dialect = _dialect()
    unique = _freeze(IndexDefinition(dialect, "uq_idx", ["id"], unique=True))
    answer = dialect.suggest_table_index_change(
        TableIndexChangeSuggestion(table_name="events", new_indexes=(unique,))
    )
    assert answer.operations is False
    # Evidence: the node's formatter has no UNIQUE slot, so emitting one would
    # silently downgrade a unique index to a plain one.
    sql, _ = AddIndexAction(dialect, IndexDefinition(dialect, "x", ["id"], unique=True)).to_sql()
    assert sql == "ADD INDEX `x` (`id`)"


def test_drop_index_if_exists_follows_the_dialect_probe():
    dialect = _dialect()
    assert dialect.supports_index_if_exists() is True
    index = _freeze(IndexDefinition(dialect, "idx_id", ["id"], if_exists=True))
    answer = dialect.suggest_table_index_change(
        TableIndexChangeSuggestion(table_name="events", old_indexes=(index,))
    )
    assert answer.state == "actions"
    assert _sql(answer.operations) == ["ALTER TABLE `events`  DROP INDEX IF EXISTS `idx_id`"]

    monkeypatched = _dialect()
    monkeypatched.supports_index_if_exists = lambda: False
    assert (
        monkeypatched.suggest_table_index_change(
            TableIndexChangeSuggestion(table_name="events", old_indexes=(index,))
        ).operations
        is False
    )


def test_index_change_is_gated_by_alter_table_index_actions(monkeypatch):
    dialect = _dialect()
    monkeypatch.setattr(dialect, "supports_alter_table_index_actions", lambda: False)
    answer = dialect.suggest_table_index_change(
        TableIndexChangeSuggestion(
            table_name="events", new_indexes=(_freeze(IndexDefinition(dialect, "i", ["id"])),)
        )
    )
    assert answer.operations is False


# --- partition scheme change ------------------------------------------------


def _partition_projection(dialect, method="RANGE", keys=("id",), **extra):
    fields = {
        "method": method,
        "keys": tuple(Column(dialect, key) for key in keys),
    }
    fields.update(extra)
    return _projection(dialect, fields)


def _definition(dialect, name, bound):
    from rhosocial.activerecord.backend.expression.statements import PartitionDefinitionExpression

    return PartitionDefinitionExpression(
        dialect, name, less_than=(MariaDBPartitionValue(dialect, bound),)
    )


def test_partition_scheme_change_removes_partitioning():
    dialect = _dialect()
    answer = dialect.suggest_partition_scheme_change(
        PartitionSchemeChangeSuggestion(
            table_name="events",
            old_partition=_partition_projection(dialect),
            new_partition=None,
        )
    )
    assert answer.state == "actions"
    assert isinstance(answer.operations[0], MariaDBRemovePartitioningExpression)
    assert _sql(answer.operations) == ["ALTER TABLE `events` REMOVE PARTITIONING"]
    # Official semantics: REMOVE PARTITIONING leaves the data unaffected.
    assert any(
        "REMOVE PARTITIONING removes all partitioning" in line for line in NON_DESTRUCTIVE_EVIDENCE
    )


def test_adding_partitioning_to_an_existing_table_is_refused():
    dialect = _dialect()
    answer = dialect.suggest_partition_scheme_change(
        PartitionSchemeChangeSuggestion(
            table_name="events", new_partition=_partition_projection(dialect)
        )
    )
    assert answer.operations is False
    assert "ALTER TABLE ... PARTITION BY" in ADD_SCHEME_UNSUPPORTED_REASON


def test_method_or_key_change_is_refused_with_rebuild_evidence():
    dialect = _dialect()
    for old, new in (
        (_partition_projection(dialect, "RANGE"), _partition_projection(dialect, "HASH")),
        (_partition_projection(dialect, "RANGE"), _partition_projection(dialect, "RANGE", ("ts",))),
    ):
        answer = dialect.suggest_partition_scheme_change(
            PartitionSchemeChangeSuggestion(
                table_name="events", old_partition=old, new_partition=new
            )
        )
        assert answer.operations is False
    assert "cannot convert" in REBUILD_UNSUPPORTED_REASON


def test_identical_partition_projection_returns_none():
    dialect = _dialect()
    scheme = _partition_projection(dialect)
    answer = dialect.suggest_partition_scheme_change(
        PartitionSchemeChangeSuggestion(
            table_name="events", old_partition=scheme, new_partition=scheme
        )
    )
    assert answer.operations is None


def test_partition_definition_change_reuses_add_but_refuses_unauthorized_drop():
    dialect = _dialect()
    p0, p1, p2 = (
        _definition(dialect, name, bound) for name, bound in (("p0", 10), ("p1", 20), ("p2", 30))
    )
    full = _partition_projection(dialect, definitions=(p0, p1, p2))
    shorter = _partition_projection(dialect, definitions=(p1, p2))
    grown = _partition_projection(dialect, definitions=(p0, p1, p2, _definition(dialect, "p3", 40)))

    # "p0" missing from the new definition is not permission to discard its
    # rows; DROP PARTITION needs an explicit retention cutoff.
    dropped = dialect.suggest_partition_scheme_change(
        PartitionSchemeChangeSuggestion(
            table_name="events", old_partition=full, new_partition=shorter
        )
    )
    assert dropped.operations is False
    assert dropped.state == "unaddressable"
    assert "retention cutoff" in PARTITION_REMOVAL_UNSUPPORTED_REASON
    assert "scheme-change point does not carry that authorization" in (
        PARTITION_REMOVAL_UNSUPPORTED_REASON
    )

    added = dialect.suggest_partition_scheme_change(
        PartitionSchemeChangeSuggestion(
            table_name="events", old_partition=full, new_partition=grown
        )
    )
    assert added.state == "actions"
    assert _sql(added.operations) == [
        "ALTER TABLE `events` ADD PARTITION (PARTITION `p3` VALUES LESS THAN (40))"
    ]
    assert any(line.startswith("ADD PARTITION adds") for line in NON_DESTRUCTIVE_EVIDENCE)


def test_partition_retention_is_only_cutoff_driven():
    dialect = _dialect()
    p0, p1, p2 = (
        _definition(dialect, name, bound) for name, bound in (("p0", 10), ("p1", 20), ("p2", 30))
    )
    full = _partition_projection(dialect, definitions=(p0, p1, p2))
    shorter = _partition_projection(dialect, definitions=(p1, p2))
    with_cutoff = _partition_projection(dialect, definitions=(p1, p2), cutoff=15)

    without = dialect.suggest_partition_scheme_change(
        PartitionSchemeChangeSuggestion(
            table_name="events", old_partition=full, new_partition=shorter
        )
    )
    with_cut = dialect.suggest_partition_scheme_change(
        PartitionSchemeChangeSuggestion(
            table_name="events", old_partition=full, new_partition=with_cutoff
        )
    )
    assert without.operations is False
    assert isinstance(with_cut.operations[0], MariaDBDropPartitionExpression)
    assert _sql(with_cut.operations) == ["ALTER TABLE `events` DROP PARTITION `p0`"]
    assert (
        dialect.suggest_partition_retention(
            "RANGE", type("Plan", (), {"table": None, "definitions": (p0,), "cutoff": None})()
        ).operations
        is False
    )


def test_hash_partition_count_shrink_reuses_coalesce():
    dialect = _dialect()
    old = _partition_projection(dialect, method="HASH", partitions_count=5)
    new = _partition_projection(dialect, method="HASH", partitions_count=3)
    answer = dialect.suggest_partition_scheme_change(
        PartitionSchemeChangeSuggestion(table_name="events", old_partition=old, new_partition=new)
    )
    assert answer.state == "actions"
    assert isinstance(answer.operations[0], MariaDBCoalescePartitionExpression)
    assert _sql(answer.operations) == ["ALTER TABLE `events` COALESCE PARTITION 2"]
    # Official semantics: COALESCE merges the removed partitions' rows into
    # the remaining ones, so it does not discard data the way DROP does.
    assert any(
        "COALESCE PARTITION reduces" in line and "merged" in line
        for line in NON_DESTRUCTIVE_EVIDENCE
    )


# --- structural safety guard ------------------------------------------------


#: Node classes that destroy a whole table/schema regardless of SQL spelling.
_DESTRUCTIVE_CLASS_NAMES = frozenset(
    {"DropTableStatement", "DropSchemaStatement", "DropDatabaseStatement"}
)
#: Destructive DDL keywords, matched against every rendered statement.
_DESTRUCTIVE_SQL = re.compile(r"\bDROP\s+(TABLE|SCHEMA|DATABASE|PARTITION)\b", re.I)


def _assert_no_unauthorized_data_loss(label, operations, drop_partition_authorized=False):
    """Check a returned chain by node class name *and* by rendered SQL.

    A change point is a declaration diff, not a delete authorization. Only a
    point carrying a retention cutoff authorizes DROP PARTITION; DROP TABLE
    and DROP SCHEMA are never authorized by any of the four points.
    """
    for operation in operations:
        name = type(operation).__name__
        assert name not in _DESTRUCTIVE_CLASS_NAMES, (label, name)
        assert not (name == "MariaDBDropPartitionExpression" and not drop_partition_authorized), (
            label,
            name,
        )
        sql, _ = operation.to_sql()
        match = _DESTRUCTIVE_SQL.search(sql)
        if match is not None:
            assert match.group(1).upper() == "PARTITION" and drop_partition_authorized, (
                label,
                name,
                sql,
            )


def test_no_change_plan_chain_carries_unauthorized_data_loss():
    """Every actionable answer is data-preserving unless the point authorizes it."""
    dialect = _dialect()
    p0, p1, p2 = (
        _definition(dialect, name, bound) for name, bound in (("p0", 10), ("p1", 20), ("p2", 30))
    )
    full = _partition_projection(dialect, definitions=(p0, p1, p2))
    shorter = _partition_projection(dialect, definitions=(p1, p2))
    with_cutoff = _partition_projection(dialect, definitions=(p1, p2), cutoff=15)
    grown = _partition_projection(dialect, definitions=(p0, p1, p2, _definition(dialect, "p3", 40)))

    # One case per protocol, plus every partition-scheme chain shape. The last
    # field records whether that point carries an explicit retention cutoff.
    cases = (
        (
            "column_reorder",
            "suggest_column_reorder",
            ColumnReorderSuggestion(
                table_name="events", old_order=("id",), new_order=("ts",), reordered_columns=("id",)
            ),
            False,
        ),
        (
            "constraint_change",
            "suggest_table_constraint_change",
            TableConstraintChangeSuggestion(
                table_name="events",
                old_constraints=(_unique(dialect, "uq_old", "id"),),
                new_constraints=(_unique(dialect, "uq_new", "created_at"),),
            ),
            False,
        ),
        (
            "index_change",
            "suggest_table_index_change",
            TableIndexChangeSuggestion(
                table_name="events",
                old_indexes=(_freeze(IndexDefinition(dialect, "idx_old", ["id"])),),
                new_indexes=(_freeze(IndexDefinition(dialect, "idx_new", ["created_at"])),),
            ),
            False,
        ),
        (
            "partition_scheme_remove",
            "suggest_partition_scheme_change",
            PartitionSchemeChangeSuggestion(
                table_name="events", old_partition=full, new_partition=None
            ),
            False,
        ),
        (
            "partition_scheme_shrink_without_cutoff",
            "suggest_partition_scheme_change",
            PartitionSchemeChangeSuggestion(
                table_name="events", old_partition=full, new_partition=shorter
            ),
            False,
        ),
        (
            "partition_scheme_shrink_with_cutoff",
            "suggest_partition_scheme_change",
            PartitionSchemeChangeSuggestion(
                table_name="events", old_partition=full, new_partition=with_cutoff
            ),
            True,
        ),
        (
            "partition_scheme_grow",
            "suggest_partition_scheme_change",
            PartitionSchemeChangeSuggestion(
                table_name="events", old_partition=full, new_partition=grown
            ),
            False,
        ),
        (
            "partition_scheme_coalesce",
            "suggest_partition_scheme_change",
            PartitionSchemeChangeSuggestion(
                table_name="events",
                old_partition=_partition_projection(dialect, method="HASH", partitions_count=5),
                new_partition=_partition_projection(dialect, method="HASH", partitions_count=3),
            ),
            False,
        ),
    )

    seen_classes = set()
    authorized_drops = 0
    for label, method, point, authorized in cases:
        answer = getattr(dialect, method)(point)
        operations = answer.operations if isinstance(answer.operations, tuple) else ()
        _assert_no_unauthorized_data_loss(label, operations, authorized)
        for operation in operations:
            seen_classes.add(type(operation).__name__)
            sql, _ = operation.to_sql()
            if "DROP PARTITION" in sql:
                assert authorized, (label, sql)
                authorized_drops += 1

    # Guard against a vacuous pass: the chains checked must include each
    # supported shape, and exactly one point-authorized DROP PARTITION.
    assert {
        "AlterTableStatement",
        "MariaDBAddPartitionExpression",
        "MariaDBCoalescePartitionExpression",
        "MariaDBDropPartitionExpression",
        "MariaDBRemovePartitioningExpression",
    }.issubset(seen_classes)
    assert authorized_drops == 1
