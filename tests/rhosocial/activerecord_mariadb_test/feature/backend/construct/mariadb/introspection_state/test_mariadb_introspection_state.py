# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/mariadb/introspection_state/test_mariadb_introspection_state.py
"""The neutral object-state API on the MariaDB introspecter.

Everything here runs without a server: rows are literal catalogue shapes and
the introspectors are driven through a scripted executor. The live counterpart
of the partition family is in ``execute/introspection/test_introspection_partitions.py``.
"""

import inspect
import pathlib
import re

import pytest

import rhosocial.activerecord.backend.impl.mariadb as mariadb_package
from rhosocial.activerecord.backend.dialect.exceptions import (
    UnsupportedFeatureError,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.introspection.introspector import (
    AsyncMariaDBIntrospector,
    MariaDBIntrospector,
    MariaDBIntrospectorMixin,
)
from rhosocial.activerecord.backend.impl.mariadb.introspection.types import (
    MariaDBConstraintInfo,
)
from rhosocial.activerecord.backend.introspection.types import (
    ConstraintState,
    DerivedObjectState,
    ItemKind,
    IndexColumnInfo,
    IndexInfo,
    IndexType,
    IntrospectionForeignKeyInfo,
    ReferentialAction,
    PartitionScheme,
    PartitionState,
    SequenceInfo,
    SequenceState,
    TableState,
)
from types import SimpleNamespace


class _FakeBackend:
    """The two facts a parser or introspector reads from its backend."""

    def __init__(self, version=(11, 4, 0), database="app"):
        self.dialect = MariaDBDialect(version)
        self.config = SimpleNamespace(database=database)


class _ScriptedExecutor:
    """A synchronous executor that hands out one canned result per call."""

    def __init__(self, results=()):
        self.results = list(results)
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        return self.results.pop(0) if self.results else []


class _AsyncScriptedExecutor(_ScriptedExecutor):
    """The awaited twin: same results, same call log."""

    async def execute(self, sql, params):
        return _ScriptedExecutor.execute(self, sql, params)


def _mixin(version=(11, 4, 0), database="app"):
    mixin = MariaDBIntrospectorMixin()
    mixin._backend = _FakeBackend(version, database)
    return mixin


TABLE_ROW = {
    "TABLE_NAME": "orders",
    "TABLE_TYPE": "BASE TABLE",
    "ENGINE": "InnoDB",
    "ROW_FORMAT": "Dynamic",
    "TABLE_COLLATION": "utf8mb4_general_ci",
    "AUTO_INCREMENT": 1,
    "TABLE_COMMENT": "orders",
    "CREATE_OPTIONS": "",
}

RANGE_ROWS = [
    {
        "PARTITION_NAME": "p2025",
        "PARTITION_METHOD": "RANGE",
        "PARTITION_EXPRESSION": "year(`created_at`)",
        "PARTITION_DESCRIPTION": "2026",
        "PARTITION_ORDINAL_POSITION": 1,
        "TABLE_ROWS": 120,
        "DATA_LENGTH": 4096,
        "INDEX_LENGTH": 1024,
        "PARTITION_COMMENT": "",
        "TABLESPACE_NAME": None,
    },
    {
        "PARTITION_NAME": "p_future",
        "PARTITION_METHOD": "RANGE",
        "PARTITION_EXPRESSION": "year(`created_at`)",
        "PARTITION_DESCRIPTION": "MAXVALUE",
        "PARTITION_ORDINAL_POSITION": 2,
        "TABLE_ROWS": 10,
        "DATA_LENGTH": 4096,
        "INDEX_LENGTH": 1024,
        "PARTITION_COMMENT": "",
        "TABLESPACE_NAME": None,
    },
]


class TestParsePartitionState:
    def test_no_rows_means_unpartitioned(self):
        state = _mixin().parse_partition_state([], "orders", "app")
        assert state.scheme is None
        assert state.bounds == ()

    def test_range_bounds_and_maxvalue(self):
        state = _mixin().parse_partition_state(RANGE_ROWS, "orders", "app")
        assert state.scheme is PartitionScheme.RANGE
        assert [bound.name for bound in state.bounds] == ["p2025", "p_future"]
        assert state.bounds[0].upper == "2026"
        assert state.bounds[0].values == ()
        assert state.bounds[-1].is_maxvalue is True
        assert state.has_default is True
        # The expression is a function, not a column list.
        assert state.key_columns == ()

    def test_column_list_expression_yields_key_columns(self):
        rows = [
            {
                "PARTITION_NAME": "p0",
                "PARTITION_METHOD": "RANGE COLUMNS",
                "PARTITION_EXPRESSION": "`region`, `id`",
                "PARTITION_DESCRIPTION": "10",
            }
        ]
        state = _mixin().parse_partition_state(rows, "orders", "app")
        assert state.scheme is PartitionScheme.RANGE
        assert state.key_columns == ("region", "id")

    def test_list_description_is_split_into_values(self):
        rows = [
            {
                "PARTITION_NAME": "p_east",
                "PARTITION_METHOD": "LIST",
                "PARTITION_EXPRESSION": "`region`",
                "PARTITION_DESCRIPTION": "'east','with,comma'",
            }
        ]
        state = _mixin().parse_partition_state(rows, "orders", "app")
        assert state.scheme is PartitionScheme.LIST
        assert state.bounds[0].values == ("east", "with,comma")
        assert state.bounds[0].upper is None

    def test_subpartitions_fold_onto_the_composite_partition(self):
        rows = [
            {
                "PARTITION_NAME": "p0",
                "SUBPARTITION_NAME": "p0sp0",
                "PARTITION_METHOD": "RANGE",
                "SUBPARTITION_METHOD": "HASH",
                "PARTITION_EXPRESSION": "`id`",
                "SUBPARTITION_EXPRESSION": "`region`",
                "PARTITION_DESCRIPTION": "10",
                "SUBPARTITION_ORDINAL_POSITION": 1,
            },
            {
                "PARTITION_NAME": "p0",
                "SUBPARTITION_NAME": "p0sp1",
                "PARTITION_METHOD": "RANGE",
                "SUBPARTITION_METHOD": "HASH",
                "PARTITION_EXPRESSION": "`id`",
                "SUBPARTITION_EXPRESSION": "`region`",
                "PARTITION_DESCRIPTION": "10",
                "SUBPARTITION_ORDINAL_POSITION": 2,
            },
            {
                "PARTITION_NAME": "p1",
                "SUBPARTITION_NAME": "p1sp0",
                "PARTITION_METHOD": "RANGE",
                "SUBPARTITION_METHOD": "HASH",
                "PARTITION_EXPRESSION": "`id`",
                "SUBPARTITION_EXPRESSION": "`region`",
                "PARTITION_DESCRIPTION": "MAXVALUE",
                "SUBPARTITION_ORDINAL_POSITION": 1,
            },
            {
                "PARTITION_NAME": "p1",
                "SUBPARTITION_NAME": "p1sp1",
                "PARTITION_METHOD": "RANGE",
                "SUBPARTITION_METHOD": "HASH",
                "PARTITION_EXPRESSION": "`id`",
                "SUBPARTITION_EXPRESSION": "`region`",
                "PARTITION_DESCRIPTION": "MAXVALUE",
                "SUBPARTITION_ORDINAL_POSITION": 2,
            },
        ]
        state = _mixin().parse_partition_state(rows, "orders", "app")
        assert state.scheme is PartitionScheme.COMPOSITE
        assert [bound.name for bound in state.bounds] == ["p0", "p1"]
        assert state.bounds[0].subpartition_count == 2
        assert state.bounds[1].subpartition_count == 2
        assert state.key_expression == "`id`"

    def test_system_time_current_partition_is_the_default(self):
        rows = [
            {
                "PARTITION_NAME": "p0",
                "PARTITION_METHOD": "SYSTEM_TIME",
                "PARTITION_EXPRESSION": "unix_timestamp(`row_end`)",
                "PARTITION_DESCRIPTION": "2026-11-26 11:00:00",
            },
            {
                "PARTITION_NAME": "pn",
                "PARTITION_METHOD": "SYSTEM_TIME",
                "PARTITION_EXPRESSION": "unix_timestamp(`row_end`)",
                "PARTITION_DESCRIPTION": "CURRENT",
            },
        ]
        state = _mixin().parse_partition_state(rows, "orders", "app")
        assert state.scheme is PartitionScheme.INTERVAL
        assert state.bounds[1].is_default is True
        assert state.has_default is True

    def test_stats_are_read_only_when_requested(self):
        state = _mixin().parse_partition_state(
            RANGE_ROWS, "orders", "app", include_stats=False
        )
        assert state.bounds[0].row_count is None
        assert state.bounds[0].size_bytes is None

        with_stats = _mixin().parse_partition_state(
            RANGE_ROWS, "orders", "app", include_stats=True
        )
        assert with_stats.bounds[0].row_count == 120
        assert with_stats.bounds[0].size_bytes == 5120


class TestSyncStateMethods:
    def test_unpartitioned_answers_scheme_none_and_no_stats_query(self):
        executor = _ScriptedExecutor([[]])
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        state = introspector.get_partition_state("orders")

        assert isinstance(state, PartitionState)
        assert state.scheme is None
        assert len(executor.calls) == 1
        assert "`TABLE_ROWS`" not in executor.calls[0][0]

    def test_unpartitioned_answers_a_partition_state_never_none(self):
        """The annotation and the runtime agree: neither answer is ``None``."""
        partition_introspector = MariaDBIntrospector(
            _FakeBackend(), _ScriptedExecutor([[]])
        )
        state = partition_introspector.get_partition_state("orders")

        table_introspector = MariaDBIntrospector(
            _FakeBackend(), _ScriptedExecutor([[TABLE_ROW], []])
        )
        table_state = table_introspector.get_table_state("orders")

        assert inspect.signature(
            MariaDBIntrospector.get_partition_state
        ).return_annotation is PartitionState
        assert isinstance(state, PartitionState)
        assert state.scheme is None
        assert isinstance(table_state.partitioning, PartitionState)
        assert table_state.partitioning.scheme is None
        assert table_state.traits == ()

    def test_stats_request_projects_the_counters(self):
        executor = _ScriptedExecutor([RANGE_ROWS])
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        state = introspector.get_partition_state("orders", include_stats=True)

        assert state.bounds[0].row_count == 120
        assert "`TABLE_ROWS`" in executor.calls[0][0]

    def test_get_table_state_carries_storage_comment_and_partitions(self):
        executor = _ScriptedExecutor([[TABLE_ROW], RANGE_ROWS])
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        state = introspector.get_table_state("orders")

        assert isinstance(state, TableState)
        assert state.kind == "regular"
        assert state.storage.engine == "InnoDB"
        assert state.storage.charset == "utf8mb4"
        assert state.storage.collation == "utf8mb4_general_ci"
        assert state.comment == "orders"
        assert state.partitioning.scheme is PartitionScheme.RANGE
        assert state.traits == ("partitioned",)

    def test_system_versioned_table_reports_an_inline_history_object(self):
        versioned_row = dict(TABLE_ROW, TABLE_TYPE="SYSTEM VERSIONED")
        executor = _ScriptedExecutor([[versioned_row], []])
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        state = introspector.get_table_state("orders")
        derived = introspector.list_derived_objects("orders")

        assert state.kind == "regular"
        assert state.traits == ("system_versioned",)
        assert isinstance(derived[0], DerivedObjectState)
        assert derived[0].kind == "history_table"
        assert derived[0].name == "orders_history"
        assert derived[0].owned_by == "orders"
        assert derived[0].raw["storage"] == "inline"
        assert derived[0].raw["materialized"] is False

    def test_list_index_states_maps_usability_and_primary(self):
        rows = [
            {
                "INDEX_NAME": "PRIMARY",
                "NON_UNIQUE": 0,
                "INDEX_TYPE": "BTREE",
                "COLUMN_NAME": "id",
                "SEQ_IN_INDEX": 1,
            },
            {
                "INDEX_NAME": "uniq_email",
                "NON_UNIQUE": 0,
                "INDEX_TYPE": "BTREE",
                "COLUMN_NAME": "email",
                "SEQ_IN_INDEX": 1,
            },
        ]
        executor = _ScriptedExecutor([rows])
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        states = introspector.list_index_states("orders")

        assert [state.name for state in states] == ["PRIMARY", "uniq_email"]
        assert states[0].backs_constraint == "PRIMARY"
        assert states[1].backs_constraint is None
        assert all(state.usable and state.visible for state in states)

    def test_list_constraint_states_covers_the_three_families(self):
        index_rows = [
            {
                "INDEX_NAME": "PRIMARY",
                "NON_UNIQUE": 0,
                "INDEX_TYPE": "BTREE",
                "COLUMN_NAME": "id",
                "SEQ_IN_INDEX": 1,
            }
        ]
        foreign_key_rows = [
            {
                "CONSTRAINT_NAME": "fk_orders_customer",
                "UPDATE_RULE": "RESTRICT",
                "DELETE_RULE": "CASCADE",
                "COLUMN_NAME": "customer_id",
                "REFERENCED_TABLE_NAME": "customers",
                "REFERENCED_COLUMN_NAME": "id",
            }
        ]
        check_rows = [
            {
                "CONSTRAINT_SCHEMA": "app",
                "TABLE_NAME": "orders",
                "CONSTRAINT_NAME": "ck_orders_total",
                "CONSTRAINT_TYPE": "CHECK",
                "CHECK_CLAUSE": "`total` >= 0",
            }
        ]
        executor = _ScriptedExecutor([index_rows, foreign_key_rows, check_rows])
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        states = introspector.list_constraint_states("orders")

        assert [state.kind for state in states] == [
            "PRIMARY KEY",
            "FOREIGN KEY",
            "CHECK",
        ]
        assert states[1].raw["referenced_table"] == "customers"
        assert states[2].raw["check_clause"] == "`total` >= 0"

    def test_list_sequence_states_has_no_owner(self):
        rows = [
            {
                "TABLE_NAME": "orders_seq",
                "START_VALUE": 1,
                "MINIMUM_VALUE": 1,
                "MAXIMUM_VALUE": 9223372036854775806,
                "INCREMENT": 1,
                "CYCLE_OPTION": "0",
                "DATA_TYPE": "bigint",
            }
        ]
        executor = _ScriptedExecutor([rows])
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        states = introspector.list_sequence_states()

        assert isinstance(states[0], SequenceState)
        assert states[0].owned_by is None
        assert states[0].start == 1
        assert states[0].increment == 1

    def test_list_schemas_reads_the_database_list(self):
        executor = _ScriptedExecutor([[{"Database": "app"}, {"Database": "mysql"}]])
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        assert introspector.list_schemas() == ["app", "mysql"]

    def test_item_exists_answers_the_kinds_mariadb_has(self):
        routine_rows = [
            {
                "ROUTINE_SCHEMA": "app",
                "ROUTINE_NAME": "app_total",
                "ROUTINE_TYPE": "FUNCTION",
                "ROUTINE_DTD_IDENTIFIER": "int",
                "PARAMETER_ORDINAL_POSITION": 1,
                "PARAMETER_MODE": "IN",
                "PARAMETER_NAME": "amount",
            }
        ]
        executor = _ScriptedExecutor(
            [[{"Database": "app"}], [TABLE_ROW], [], routine_rows]
        )
        introspector = MariaDBIntrospector(_FakeBackend(), executor)

        assert introspector.item_exists(ItemKind.SCHEMA, "app") is True
        assert introspector.item_exists(ItemKind.TABLE, "orders") is True
        assert introspector.item_exists(ItemKind.SEQUENCE, "orders_seq") is False
        assert introspector.item_exists(ItemKind.FUNCTION, "app_total") is True

    def test_item_exists_returns_false_for_a_kind_mariadb_does_not_have(self):
        introspector = MariaDBIntrospector(_FakeBackend(), _ScriptedExecutor())

        assert introspector.item_exists(ItemKind.TYPE, "order_total") is False

    def test_item_exists_refuses_a_kind_mariadb_has_without_a_query(self):
        introspector = MariaDBIntrospector(_FakeBackend(), _ScriptedExecutor())

        with pytest.raises(UnsupportedFeatureError) as caught:
            introspector.item_exists(ItemKind.INDEX, "idx_orders_created")

        assert "item_exists(index)" in str(caught.value)


class TestDeclaredItemKinds:
    """The declared kind sets are the whole of ``ItemKind``."""

    def test_the_three_declared_sets_partition_every_kind(self):
        declared = (
            MariaDBIntrospectorMixin.ITEM_KINDS_QUERIED,
            MariaDBIntrospectorMixin.ITEM_KINDS_REFUSED,
            MariaDBIntrospectorMixin.ITEM_KINDS_ABSENT,
        )

        assert declared[0].isdisjoint(declared[1])
        assert declared[0].isdisjoint(declared[2])
        assert declared[1].isdisjoint(declared[2])
        assert declared[0] | declared[1] | declared[2] == frozenset(ItemKind)

    def test_every_kind_takes_its_declared_branch(self):
        for kind in ItemKind:
            executor = _ScriptedExecutor()
            introspector = MariaDBIntrospector(_FakeBackend(), executor)

            if kind in MariaDBIntrospectorMixin.ITEM_KINDS_ABSENT:
                assert introspector.item_exists(kind, "probe") is False
            elif kind in MariaDBIntrospectorMixin.ITEM_KINDS_REFUSED:
                with pytest.raises(UnsupportedFeatureError):
                    introspector.item_exists(kind, "probe")
            else:
                # The queried branch asks the catalogue before it answers.
                assert introspector.item_exists(kind, "probe") is False
                assert executor.calls


class TestAsyncStateMethods:
    async def test_get_partition_state_unpartitioned(self):
        executor = _AsyncScriptedExecutor([[]])
        introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

        state = await introspector.get_partition_state("orders")

        assert state.scheme is None
        assert "`TABLE_ROWS`" not in executor.calls[0][0]

    async def test_unpartitioned_answers_a_partition_state_never_none(self):
        """The annotation and the runtime agree: neither answer is ``None``."""
        partition_introspector = AsyncMariaDBIntrospector(
            _FakeBackend(), _AsyncScriptedExecutor([[]])
        )
        state = await partition_introspector.get_partition_state("orders")

        table_introspector = AsyncMariaDBIntrospector(
            _FakeBackend(), _AsyncScriptedExecutor([[TABLE_ROW], []])
        )
        table_state = await table_introspector.get_table_state("orders")

        assert inspect.signature(
            AsyncMariaDBIntrospector.get_partition_state
        ).return_annotation is PartitionState
        assert isinstance(state, PartitionState)
        assert state.scheme is None
        assert isinstance(table_state.partitioning, PartitionState)
        assert table_state.partitioning.scheme is None
        assert table_state.traits == ()

    async def test_get_table_state_and_derived_objects(self):
        versioned_row = dict(TABLE_ROW, TABLE_TYPE="SYSTEM VERSIONED")
        executor = _AsyncScriptedExecutor([[versioned_row], []])
        introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

        state = await introspector.get_table_state("orders")
        derived = await introspector.list_derived_objects("orders")

        assert state.storage.charset == "utf8mb4"
        assert state.traits == ("system_versioned",)
        assert derived[0].name == "orders_history"

    async def test_list_sequence_states(self):
        rows = [
            {
                "TABLE_NAME": "orders_seq",
                "START_VALUE": 1,
                "INCREMENT": 1,
            }
        ]
        executor = _AsyncScriptedExecutor([rows])
        introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

        states = await introspector.list_sequence_states()

        assert states[0].name == "orders_seq"

    async def test_list_schemas(self):
        executor = _AsyncScriptedExecutor([[{"Database": "app"}]])
        introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

        assert await introspector.list_schemas() == ["app"]

    async def test_item_exists_returns_false_for_a_kind_mariadb_does_not_have(self):
        introspector = AsyncMariaDBIntrospector(
            _FakeBackend(), _AsyncScriptedExecutor()
        )

        assert await introspector.item_exists(ItemKind.TYPE, "order_total") is False

    async def test_item_exists_refuses_a_kind_mariadb_has_without_a_query(self):
        introspector = AsyncMariaDBIntrospector(
            _FakeBackend(), _AsyncScriptedExecutor()
        )

        with pytest.raises(UnsupportedFeatureError) as caught:
            await introspector.item_exists(ItemKind.INDEX, "idx_orders_created")

        assert "item_exists(index)" in str(caught.value)

    async def test_every_kind_takes_its_declared_branch(self):
        for kind in ItemKind:
            executor = _AsyncScriptedExecutor()
            introspector = AsyncMariaDBIntrospector(_FakeBackend(), executor)

            if kind in MariaDBIntrospectorMixin.ITEM_KINDS_ABSENT:
                assert await introspector.item_exists(kind, "probe") is False
            elif kind in MariaDBIntrospectorMixin.ITEM_KINDS_REFUSED:
                with pytest.raises(UnsupportedFeatureError):
                    await introspector.item_exists(kind, "probe")
            else:
                # The queried branch asks the catalogue before it answers.
                assert await introspector.item_exists(kind, "probe") is False
                assert executor.calls


class TestParserMappings:
    """Pure parser projections that do not need an executor."""

    def test_index_state_keeps_the_index_type_and_columns(self):
        index = IndexInfo(
            name="idx_orders_created",
            table_name="orders",
            schema="app",
            is_unique=False,
            index_type=IndexType.BTREE,
            columns=[IndexColumnInfo(name="created_at", ordinal_position=1)],
        )
        state = MariaDBIntrospectorMixin().parse_index_states(
            [index], "orders", "app"
        )[0]
        assert state.method == "BTREE"
        assert state.raw["columns"] == ("created_at",)

    def test_constraint_state_marks_check_as_validated_and_enforced(self):
        state = MariaDBIntrospectorMixin().parse_constraint_states(
            [],
            [
                IntrospectionForeignKeyInfo(
                    name="fk",
                    table_name="orders",
                    schema="app",
                    columns=["customer_id"],
                    referenced_table="customers",
                    referenced_columns=["id"],
                    on_update=ReferentialAction.RESTRICT,
                    on_delete=ReferentialAction.CASCADE,
                )
            ],
            [
                MariaDBConstraintInfo(
                    schema="app",
                    table_name="orders",
                    name="ck",
                    check_clause="`total` >= 0",
                )
            ],
            "orders",
            "app",
        )
        assert isinstance(state[0], ConstraintState)
        assert state[1].kind == "CHECK"
        assert state[1].validated is True
        assert state[1].enforced is True
        assert state[1].deferred is False

    def test_sequence_state_carries_the_declared_facts(self):
        sequence = SequenceInfo(
            name="s",
            schema="app",
            start_value=1,
            minimum_value=1,
            maximum_value=10,
            increment=2,
            cycle=True,
            data_type="bigint",
        )
        state = MariaDBIntrospectorMixin().parse_sequence_states([sequence])[0]
        assert state.owned_by is None
        assert state.raw["maximum_value"] == 10
        assert state.raw["cycle"] is True

# ---------------------------------------------------------------------------
# Guard: the partitioning slot is never optional
# ---------------------------------------------------------------------------

#: The shipped package tree; ``__path__`` because the editable install resolves
#: the package through a PEP 420 namespace finder where ``__file__`` is ``None``.
PACKAGE_ROOT = pathlib.Path(next(iter(mariadb_package.__path__)))

#: Repository root: ``PACKAGE_ROOT`` is ``src/rhosocial/activerecord/backend/
#: impl/mariadb``, so ``src`` is five parents up and the tests sit beside it.
REPO_ROOT = PACKAGE_ROOT.parents[5]

SRC_ROOT = REPO_ROOT / "src"

#: The repository's own test tree, a sibling of ``src``.
TESTS_ROOT = REPO_ROOT / "tests"

_SKIPPED_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    ".worktree",
}

#: The spellings that would make a partitioning slot optional again. The
#: annotation form is included: core made ``TableState.partitioning``
#: non-optional, so an ``Optional`` annotation is the same defect as a guard
#: or a ``None`` default. No leading word boundary: a longer variable such as
#: ``state_partitioning`` is the same slot under a fuller name.
PARTITIONING_NONE_PATTERNS = (
    re.compile(r"partitioning\s*=\s*None\b"),
    re.compile(r"partitioning\s+is\s+None\b"),
    re.compile(r"partitioning\s+is\s+not\s+None\b"),
    re.compile(r"partitioning\s*:\s*Optional\b"),
)


def _python_files(root):
    """Every module under ``root``, skipping virtualenvs and caches."""
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(
            part in _SKIPPED_DIR_NAMES for part in path.relative_to(root).parts
        )
    )


def _partitioning_none_sites(paths):
    """Return ``(path, lineno, line)`` for each optional-partitioning spelling."""
    sites = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            if any(pattern.search(line) for pattern in PARTITIONING_NONE_PATTERNS):
                sites.append((path, lineno, line.strip()))
    return sites


class TestPartitioningIsNeverNoneGuard:
    """Neither ``src`` nor the tests may treat partitioning as optional."""

    def test_the_guard_scans_both_trees(self):
        src_files = _python_files(SRC_ROOT)
        test_files = _python_files(TESTS_ROOT)
        assert src_files, f"no modules found under {SRC_ROOT}"
        assert test_files, f"no modules found under {TESTS_ROOT}"
        assert any(path.name == "introspector.py" for path in src_files)
        assert any(path.name == pathlib.Path(__file__).name for path in test_files)

    def test_no_module_treats_partitioning_as_optional(self):
        sites = _partitioning_none_sites(
            _python_files(SRC_ROOT) + _python_files(TESTS_ROOT)
        )
        assert not sites, (
            "These sites treat partitioning as optional: "
            f"{sites}. Core's ``TableState.partitioning`` is never ``None``; "
            "an unpartitioned table answers an empty ``PartitionState`` whose "
            "``scheme`` is ``None``."
        )

    def test_the_guard_reports_a_synthetic_violation(self, tmp_path):
        """The scan is not vacuous: every spelling it rejects is recognised."""
        offender = tmp_path / "offending.py"
        offender.write_text(
            "\n".join(
                [
                    "state_partitioning" + " = None",
                    "if table.partitioning" + " is None:",
                    "if table.partitioning" + " is not None:",
                    "def parse(partitioning" + ": Optional[PartitionState]):",
                ]
            ),
            encoding="utf-8",
        )
        sites = _partitioning_none_sites([offender])
        assert len(sites) == len(PARTITIONING_NONE_PATTERNS), sites
