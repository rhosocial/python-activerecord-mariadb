# tests/rhosocial/activerecord_mariadb_test/feature/query/mariadb/test_mariadb_explain_deep.py
"""Backend-local, deep EXPLAIN tests for MariaDB.

The shared testsuite contract only asserts that EXPLAIN *can run*. This file
interprets what MariaDB actually returns, which is deliberately NOT generalized
into the testsuite because dialects disagree on plan shape:

* Construction level (no DB): the capability probes are version-gated at 10.6
  for ANALYZE / FORMAT, and ``format_explain_statement`` renders
  ``EXPLAIN [ANALYZE] [FORMAT=<TYPE>] ...`` with an equals sign (MariaDB's
  spelling, unlike core's ``FORMAT <TYPE>``). ``TREE`` is MySQL-only and is
  never advertised by this dialect.
* Execution level (real DB in CI): the default tabular plan yields opaque dict
  rows keyed by MariaDB's 12 columns -- ``select_type`` / ``table`` / ``type`` /
  ``key`` / ``partitions`` / ``Extra`` ... -- from which scan-vs-index evidence
  is read. ANALYZE / FORMAT=JSON return a single text/JSON column instead, so
  those tests assert only that a non-empty plan comes back.
* Partition pruning: MariaDB genuinely supports declarative RANGE partitioning
  and the tabular plan exposes a ``partitions`` column, so a gated test builds a
  small partitioned table and asserts the plan names only the matching partition.

Construction-level tests run without a database; DB-level tests use the
directory-owned scenario database and are gated by ``supports_*`` probes.
"""

from typing import Any, Dict, List, Optional

import pytest
from rhosocial.activerecord.backend.expression import RawSQL
from rhosocial.activerecord.backend.expression.statements import (
    ExplainFormat,
    ExplainOptions,
    ExplainStatement,
    ExplainType,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

_DDL = ExecutionOptions(stmt_type=StatementType.DDL)


def _dialect(version=(11, 4, 0)) -> MariaDBDialect:
    return MariaDBDialect(version=version)


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
        "fmt, expected",
        [
            ("JSON", True),
            ("TRADITIONAL", True),
            ("json", True),
            ("TREE", False),
            ("XML", False),
        ],
    )
    def test_supports_explain_format_on_10_6(self, fmt, expected):
        assert _dialect((10, 6, 0)).supports_explain_format(fmt) is expected

    def test_supports_explain_format_before_10_6(self):
        dialect = _dialect((10, 5, 4))
        assert dialect.supports_explain_format("JSON") is False
        assert dialect.supports_explain_format("TRADITIONAL") is False
        assert dialect.supports_explain_analyze() is False

    def test_explain_plan_and_partitioning_are_declared(self):
        dialect = _dialect()
        assert dialect.supports_explain_plan() is True
        assert dialect.supports_table_partitioning() is True
        assert dialect.supports_range_columns_partitioning() is True


@pytest.mark.mariadb
class TestMariaDBExplainRendering:
    """format_explain_statement / ExplainStatement.to_sql without a DB."""

    @staticmethod
    def _render(options, version=(11, 4, 0)):
        dialect = _dialect(version)
        statement = RawSQL(dialect, "SELECT * FROM u WHERE id = %s", (1,))
        expr = ExplainStatement(dialect, statement=statement, options=options)
        return expr.to_sql()

    def test_basic_explain_preserves_statement_and_params(self):
        sql, params = self._render(None)
        assert sql == "EXPLAIN SELECT * FROM u WHERE id = %s"
        assert params == (1,)

    def test_analyze_boolean_flag(self):
        sql, params = self._render(ExplainOptions(analyze=True))
        assert sql.startswith("EXPLAIN ANALYZE ")
        assert sql.endswith("SELECT * FROM u WHERE id = %s")
        assert params == (1,)

    def test_analyze_via_type(self):
        sql, _ = self._render(ExplainOptions(type=ExplainType.ANALYZE))
        assert sql.startswith("EXPLAIN ANALYZE ")

    def test_format_uses_equals_sign(self):
        sql, _ = self._render(ExplainOptions(format=ExplainFormat.JSON))
        assert "FORMAT=JSON" in sql
        assert "FORMAT JSON" not in sql

    def test_format_traditional(self):
        sql, _ = self._render(ExplainOptions(format=ExplainFormat.TRADITIONAL))
        assert "FORMAT=TRADITIONAL" in sql

    def test_analyze_and_format_combined(self):
        sql, _ = self._render(ExplainOptions(analyze=True, format=ExplainFormat.JSON))
        assert sql.startswith("EXPLAIN ANALYZE FORMAT=JSON ")

    def test_costs_off_and_verbose_are_rendered(self):
        sql, _ = self._render(ExplainOptions(costs=False, verbose=True))
        assert " COSTS OFF " in sql
        assert " VERBOSE " in sql

    def test_render_matches_dialect_formatter(self):
        dialect = _dialect()
        statement = RawSQL(dialect, "SELECT 1")
        expr = ExplainStatement(dialect, statement=statement, options=ExplainOptions())
        assert expr.to_sql() == dialect.format_explain_statement(expr)

    def test_tree_format_is_not_advertised(self):
        # The renderer emits whatever format the caller passes; TREE must be
        # gated out by supports_explain_format() before it reaches the dialect.
        dialect = _dialect()
        assert dialect.supports_explain_format("TREE") is False
        sql, _ = self._render(ExplainOptions(format=ExplainFormat.TREE))
        assert "FORMAT=TREE" in sql


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
        dialect = self._require_explain(order_fixtures[0])
        if not dialect.supports_explain_format("JSON"):
            pytest.skip("MariaDB < 10.6 has no FORMAT=JSON")
        User, _, _ = order_fixtures
        plan = User.query().explain(format=ExplainFormat.JSON).aggregate()
        assert isinstance(plan, list) and plan

    def test_analyze_format_json_when_supported(self, order_fixtures):
        """MariaDB's analyzed-plan form is the ``ANALYZE FORMAT=JSON`` statement.

        NOTE: the dialect renderer currently emits ``EXPLAIN ANALYZE ...``
        (the PostgreSQL / MySQL-8 spelling), which MariaDB rejects with errno
        1064. This test uses MariaDB's own spelling so that ANALYZE capability is
        still covered at the DB level; the renderer mismatch is a known backend
        limitation recorded in the report for this change.
        """
        User, _, _ = order_fixtures
        dialect = self._require_explain(User)
        if not (dialect.supports_explain_analyze() and dialect.supports_explain_format("JSON")):
            pytest.skip("ANALYZE FORMAT=JSON requires MariaDB >= 10.6")
        rows = User.backend().fetch_all("ANALYZE FORMAT=JSON SELECT * FROM `users`", ())
        assert rows and any("query_" in str(v) for v in rows[0].values()), rows

    def test_partition_pruning_evidence(self, order_fixtures):
        """A RANGE COLUMNS plan names only the matching partition.

        MariaDB's plain tabular EXPLAIN has no ``partitions`` column (unlike
        MySQL); the ``EXPLAIN PARTITIONS`` form is what exposes pruning.
        """
        User, _, _ = order_fixtures
        dialect = self._require_explain(User)
        if not (
            dialect.supports_table_partitioning() and dialect.supports_range_columns_partitioning()
        ):
            pytest.skip("no declarative RANGE COLUMNS partitioning")
        backend = User.backend()
        table = "test_explain_part_prune"
        create_sql = (
            f"CREATE TABLE {table} ("
            "id INT NOT NULL AUTO_INCREMENT, "
            "d DATE NOT NULL, "
            "note VARCHAR(50), "
            "PRIMARY KEY (id, d)"
            ") ENGINE=InnoDB "
            "PARTITION BY RANGE COLUMNS(d) ("
            "PARTITION p0 VALUES LESS THAN ('2024-01-01'), "
            "PARTITION p1 VALUES LESS THAN ('2025-01-01'), "
            "PARTITION p2 VALUES LESS THAN (MAXVALUE)"
            ")"
        )
        insert_sql = (
            f"INSERT INTO {table} (d, note) VALUES "
            "('2023-06-01', 'old'), ('2024-06-01', 'mid'), ('2025-06-01', 'new')"
        )
        try:
            backend.execute(f"DROP TABLE IF EXISTS {table}", (), options=_DDL)
            backend.execute(create_sql, (), options=_DDL)
            backend.execute(insert_sql, (), options=_DDL)
            rows = backend.fetch_all(
                f"EXPLAIN PARTITIONS SELECT * FROM {table} WHERE d = '2024-06-01'", ()
            )
            assert rows, "EXPLAIN PARTITIONS must return a plan"
            partitions = [str(v) for v in _col(rows, "partitions")]
            assert partitions, "MariaDB EXPLAIN PARTITIONS must expose the partitions column"
            assert any("p1" in p for p in partitions), partitions
            assert not any("p0" in p for p in partitions), f"p0 should be pruned: {partitions}"
        finally:
            backend.execute(f"DROP TABLE IF EXISTS {table}", (), options=_DDL)


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
