# tests/rhosocial/activerecord_mariadb_test/feature/query/mariadb/test_mariadb_explain_deep.py
"""Backend-local, deep EXPLAIN tests for MariaDB.

The shared testsuite contract only asserts that EXPLAIN *can run*. This file
interprets what MariaDB actually returns, using the expression system for every
constructed statement (no raw SQL, per the REV2 rule):

* Construction level (no DB): every EXPLAIN capability is a parameterless
  switch, gated at 10.6 for ``ANALYZE`` / ``FORMAT=JSON`` / ``FORMAT=TRADITIONAL``
  and answering False for ``TEXT``/``XML``/``YAML``/``TREE``. The formatter
  renders ``EXPLAIN [ANALYZE] [FORMAT=<TYPE>] ...`` with an equals sign
  (MariaDB's spelling, unlike core's ``FORMAT <TYPE>``), and raises for an
  option MariaDB has no spelling for rather than dropping it.
* Execution level (real DB in CI): the default tabular plan yields opaque dict
  rows keyed by MariaDB's columns -- ``select_type`` / ``table`` / ``type`` /
  ``key`` / ``Extra`` ... -- from which scan-vs-index evidence is read. The
  public ``Model.query().explain(...).aggregate()`` path is used throughout.

Two DB-level cases deliberately do **not** appear here:

* ``EXPLAIN ANALYZE ...`` is emitted by the dialect renderer with the
  PostgreSQL / MySQL-8 spelling, which MariaDB rejects with errno 1064; only
  the capability gate and the rendered text are pinned (a backend limitation,
  reported with this change).
* MariaDB's ``format_create_table_statement`` drops the ``partition=`` field of
  a ``CreateTableStatement``, so a partitioned table cannot be created through
  the expression system. Per the REV2 rule no hand-built DDL is substituted;
  only the partition expression's rendered clause is pinned construction-level.

Construction-level tests run without a database; DB-level tests use the
directory-owned scenario database and are gated by ``supports_*`` probes.
"""

from typing import Any, Dict, List, Optional, Tuple

import pytest
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    AllColumnsWildcard,
    Column,
    ComparisonPredicate,
    ExplainStatement,
    Literal,
    QueryStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.statements import (
    ExplainFormat,
    ExplainOptions,
    ExplainType,
    PartitionDefinitionExpression,
)

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBPartitionByRangeColumns,
    MariaDBPartitionMaxValue,
    MariaDBPartitionValue,
)

_BASE_SQL = "SELECT `id`, `name` FROM `users` WHERE `id` = %s"


def _dialect(version=(11, 4, 0)) -> MariaDBDialect:
    return MariaDBDialect(version=version)


def _query(dialect: MariaDBDialect) -> QueryStatement:
    """The statement wrapped by EXPLAIN in the rendering tests."""
    return QueryStatement(
        dialect=dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, 1)),
        ),
    )


def _render(options: Optional[ExplainOptions] = None, version=(11, 4, 0)) -> Tuple[str, tuple]:
    dialect = _dialect(version)
    expr = ExplainStatement(dialect, statement=_query(dialect), options=options)
    return expr.to_sql()


def _cell(row: Dict[str, Any], name: str) -> Optional[Any]:
    """Read one plan column case-insensitively (driver column casing varies)."""
    target = name.lower()
    for key, value in row.items():
        if str(key).lower() == target:
            return value
    return None


def _col(plan: List[Dict[str, Any]], name: str) -> List[Any]:
    """Collect a named column from plan rows, skipping rows that omit it."""
    values = []
    for row in plan:
        value = _cell(row, name)
        if value is not None:
            values.append(value)
    return values


@pytest.mark.mariadb
class TestMariaDBExplainCapabilities:
    """Capability probes are pure version gates; no DB needed."""

    @pytest.mark.parametrize(
        "version, expected",
        [
            ((10, 5, 0), False),
            ((10, 6, 0), True),
            ((11, 4, 0), True),
            ((13, 1, 1), True),
        ],
    )
    def test_supports_explain_analyze(self, version, expected):
        assert _dialect(version).supports_explain_analyze() is expected

    @pytest.mark.parametrize(
        "switch, expected_on_10_6",
        [
            ("supports_explain_format_json", True),
            ("supports_explain_format_traditional", True),
            ("supports_explain_format_text", False),
            ("supports_explain_format_tree", False),
            ("supports_explain_format_xml", False),
            ("supports_explain_format_yaml", False),
            # MariaDB's grammar has none of the option keywords below.
            ("supports_explain_verbose", False),
            ("supports_explain_costs", False),
            ("supports_explain_buffers", False),
            ("supports_explain_timing", False),
            ("supports_explain_settings", False),
            ("supports_explain_wal", False),
        ],
    )
    def test_support_switch_answers(self, switch, expected_on_10_6):
        dialect = _dialect((10, 6, 0))
        assert getattr(dialect, switch)() is expected_on_10_6

    def test_supports_explain_format_before_10_6(self):
        dialect = _dialect((10, 5, 4))
        assert dialect.supports_explain_format_json() is False
        assert dialect.supports_explain_format_traditional() is False
        assert dialect.supports_explain_analyze() is False

    def test_explain_plan_and_partitioning_are_declared(self):
        dialect = _dialect()
        assert dialect.supports_explain_plan() is True
        assert dialect.supports_table_partitioning() is True
        assert dialect.supports_range_columns_partitioning() is True


@pytest.mark.mariadb
class TestMariaDBExplainRendering:
    """format_explain_statement / ExplainStatement.to_sql without a DB."""

    def test_basic_explain_preserves_statement_and_params(self):
        sql, params = _render()
        assert sql == f"EXPLAIN {_BASE_SQL}"
        assert params == (1,)

    def test_empty_options_same_as_none(self):
        assert _render(ExplainOptions()) == _render()

    def test_analyze_boolean_flag(self):
        sql, params = _render(ExplainOptions(analyze=True))
        assert sql == f"EXPLAIN ANALYZE {_BASE_SQL}"
        assert params == (1,)

    def test_analyze_via_type(self):
        sql, _ = _render(ExplainOptions(type=ExplainType.ANALYZE))
        assert sql == f"EXPLAIN ANALYZE {_BASE_SQL}"

    def test_format_uses_equals_sign(self):
        sql, _ = _render(ExplainOptions(format=ExplainFormat.JSON))
        assert sql == f"EXPLAIN FORMAT=JSON {_BASE_SQL}"
        assert "FORMAT JSON" not in sql

    def test_format_traditional(self):
        sql, _ = _render(ExplainOptions(format=ExplainFormat.TRADITIONAL))
        assert sql == f"EXPLAIN FORMAT=TRADITIONAL {_BASE_SQL}"

    def test_analyze_and_format_combined(self):
        sql, _ = _render(ExplainOptions(analyze=True, format=ExplainFormat.JSON))
        assert sql == f"EXPLAIN ANALYZE FORMAT=JSON {_BASE_SQL}"

    def test_costs_off_is_refused_not_emitted(self):
        # MariaDB has no COSTS option. Dropping it silently would answer a
        # different question than the caller asked, so the formatter refuses.
        with pytest.raises(UnsupportedFeatureError):
            _render(ExplainOptions(costs=False))

    def test_verbose_is_refused_not_emitted(self):
        # MariaDB's spelling is EXTENDED; VERBOSE is not in its grammar.
        with pytest.raises(UnsupportedFeatureError):
            _render(ExplainOptions(verbose=True))

    def test_render_matches_dialect_formatter(self):
        dialect = _dialect()
        query = QueryStatement(
            dialect=dialect,
            select=[AllColumnsWildcard(dialect)],
            from_=Table(dialect, "users"),
        )
        expr = ExplainStatement(dialect, statement=query, options=ExplainOptions())
        assert expr.to_sql() == dialect.format_explain_statement(expr)

    @pytest.mark.parametrize(
        "fmt",
        [ExplainFormat.TEXT, ExplainFormat.TREE, ExplainFormat.XML, ExplainFormat.YAML],
    )
    def test_formats_mariadb_does_not_accept_are_refused(self, fmt):
        # The switch answers False and the formatter enforces the same answer.
        with pytest.raises(UnsupportedFeatureError):
            _render(ExplainOptions(format=fmt))

    def test_analyze_below_10_6_is_refused(self):
        with pytest.raises(UnsupportedFeatureError):
            _render(ExplainOptions(analyze=True), version=(10, 5, 0))

    def test_format_json_below_10_6_is_refused(self):
        with pytest.raises(UnsupportedFeatureError):
            _render(ExplainOptions(format=ExplainFormat.JSON), version=(10, 5, 0))

    @pytest.mark.parametrize(
        "options",
        [
            ExplainOptions(buffers=True),
            ExplainOptions(timing=True, analyze=True),
            ExplainOptions(settings=True),
            ExplainOptions(wal=True),
        ],
    )
    def test_options_without_a_mariadb_spelling_are_refused(self, options):
        with pytest.raises(UnsupportedFeatureError):
            _render(options)


@pytest.mark.mariadb
class TestMariaDBPartitionClauseRendering:
    """MariaDB partition expressions render RANGE COLUMNS pruning clauses.

    The DB-level counterpart is intentionally absent: this backend's
    ``format_create_table_statement`` does not render ``CreateTableStatement.partition``,
    so a partitioned table cannot be set up through expressions alone.
    """

    def test_partition_by_range_columns_renders_boundaries(self):
        dialect = _dialect()
        clause = MariaDBPartitionByRangeColumns(
            dialect,
            [Column(dialect, "created_at")],
            partitions=[
                PartitionDefinitionExpression(
                    dialect, "p0", less_than=[MariaDBPartitionValue(dialect, "2024-01-01")]
                ),
                PartitionDefinitionExpression(
                    dialect, "p1", less_than=[MariaDBPartitionValue(dialect, "2025-01-01")]
                ),
                PartitionDefinitionExpression(
                    dialect, "pmax", less_than=[MariaDBPartitionMaxValue(dialect)]
                ),
            ],
        )
        sql, params = clause.to_sql()
        assert "PARTITION BY RANGE COLUMNS (`created_at`)" in sql
        assert "PARTITION `p0` VALUES LESS THAN ('2024-01-01')" in sql
        assert "PARTITION `p1` VALUES LESS THAN ('2025-01-01')" in sql
        assert "PARTITION `pmax` VALUES LESS THAN (MAXVALUE)" in sql
        assert params == ()


@pytest.mark.mariadb
@pytest.mark.query
class TestMariaDBExplainDeepSync:
    """Interpret MariaDB's tabular EXPLAIN output (synchronous)."""

    @staticmethod
    def _require_explain(model):
        dialect = model.backend().dialect
        if not dialect.supports_explain_plan():
            pytest.skip("backend does not support EXPLAIN plans")
        return dialect

    def test_tabular_plan_shape(self, order_fixtures):
        User, _, _ = order_fixtures
        self._require_explain(User)
        plan = User.query().explain().aggregate()
        assert isinstance(plan, list) and plan, "EXPLAIN must return a non-empty plan"
        assert _cell(plan[0], "select_type") is not None, "expected MariaDB tabular columns"
        assert _cell(plan[0], "type") is not None, "expected the access-type column"
        assert any("users" in str(t).lower() for t in _col(plan, "table"))

    def test_full_scan_on_unindexed_column(self, order_fixtures):
        """users.age has no index, so a range filter plans as a full scan."""
        User, _, _ = order_fixtures
        self._require_explain(User)
        plan = User.query().where(User.c.age > 30).explain().aggregate()
        types = [str(t).upper() for t in _col(plan, "type")]
        assert "ALL" in types, f"expected a full scan (type=ALL), got {types}"

    def test_primary_key_lookup_uses_index(self, order_fixtures):
        """An equality predicate on the primary key resolves through PRIMARY.

        Seed a row first: on an empty table the optimizer short-circuits to
        ``Impossible WHERE`` and reports no access type / key at all.
        """
        User, _, _ = order_fixtures
        self._require_explain(User)
        user = User(username="explain_pk_user", email="explain_pk@example.com", age=30)
        user.save()
        plan = User.query().where(User.c.id == user.id).explain().aggregate()
        types = [str(t).upper() for t in _col(plan, "type")]
        assert any(t in ("CONST", "REF", "EQ_REF") for t in types), types
        keys = [str(k).upper() for k in _col(plan, "key")]
        assert any("PRIMARY" in k for k in keys), keys

    def test_join_plan_references_both_tables(self, order_fixtures):
        """A two-table JOIN produces one plan row per table."""
        User, Order, _ = order_fixtures
        self._require_explain(User)
        plan = User.query().join(Order, on=(User.c.id == Order.c.user_id)).explain().aggregate()
        tables = [str(t).lower() for t in _col(plan, "table")]
        assert any("users" in t for t in tables), tables
        assert any("orders" in t for t in tables), tables

    def test_explain_last_call_wins(self, order_fixtures):
        """A later explain() overrides earlier options (last call wins)."""
        User, _, _ = order_fixtures
        self._require_explain(User)
        plan = User.query().explain(analyze=True).explain().aggregate()
        assert plan
        assert _cell(plan[0], "select_type") is not None, "last plain explain -> tabular plan"

    def test_format_json_when_supported(self, order_fixtures):
        User, _, _ = order_fixtures
        dialect = self._require_explain(User)
        if not dialect.supports_explain_format_json():
            pytest.skip("MariaDB < 10.6 has no FORMAT=JSON")
        plan = User.query().explain(format=ExplainFormat.JSON).aggregate()
        assert isinstance(plan, list) and plan


@pytest.mark.mariadb
@pytest.mark.query
@pytest.mark.asyncio
class TestMariaDBExplainDeepAsync:
    """Interpret MariaDB's tabular EXPLAIN output (asynchronous)."""

    @staticmethod
    def _require_explain(model):
        dialect = model.backend().dialect
        if not dialect.supports_explain_plan():
            pytest.skip("backend does not support EXPLAIN plans")
        return dialect

    async def test_tabular_plan_shape(self, async_order_fixtures):
        AsyncUser, _, _ = async_order_fixtures
        self._require_explain(AsyncUser)
        plan = await AsyncUser.query().explain().aggregate()
        assert isinstance(plan, list) and plan
        assert _cell(plan[0], "select_type") is not None
        assert _cell(plan[0], "type") is not None
        assert any("users" in str(t).lower() for t in _col(plan, "table"))

    async def test_full_scan_on_unindexed_column(self, async_order_fixtures):
        AsyncUser, _, _ = async_order_fixtures
        self._require_explain(AsyncUser)
        plan = await AsyncUser.query().where(AsyncUser.c.age > 30).explain().aggregate()
        types = [str(t).upper() for t in _col(plan, "type")]
        assert "ALL" in types, f"expected a full scan (type=ALL), got {types}"

    async def test_primary_key_lookup_uses_index(self, async_order_fixtures):
        AsyncUser, _, _ = async_order_fixtures
        self._require_explain(AsyncUser)
        user = AsyncUser(
            username="explain_pk_user_async", email="explain_pk_async@example.com", age=30
        )
        await user.save()
        plan = await AsyncUser.query().where(AsyncUser.c.id == user.id).explain().aggregate()
        types = [str(t).upper() for t in _col(plan, "type")]
        assert any(t in ("CONST", "REF", "EQ_REF") for t in types), types
        keys = [str(k).upper() for k in _col(plan, "key")]
        assert any("PRIMARY" in k for k in keys), keys

    async def test_join_plan_references_both_tables(self, async_order_fixtures):
        AsyncUser, AsyncOrder, _ = async_order_fixtures
        self._require_explain(AsyncUser)
        plan = (
            await AsyncUser.query()
            .join(AsyncOrder, on=(AsyncUser.c.id == AsyncOrder.c.user_id))
            .explain()
            .aggregate()
        )
        tables = [str(t).lower() for t in _col(plan, "table")]
        assert any("users" in t for t in tables), tables
        assert any("orders" in t for t in tables), tables
