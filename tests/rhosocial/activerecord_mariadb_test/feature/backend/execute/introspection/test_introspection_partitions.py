# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/introspection/test_introspection_partitions.py
"""Partition state: statement shape and live execution.

MariaDB's ``information_schema.PARTITIONS`` publishes 25 columns: it has the
subpartition name, method, expression and ordinal, but **no**
``SUBPARTITION_DESCRIPTION``. A statement that projects that column is rejected
by the server at parse time (``Unknown column ... in 'field list'``) no matter
which projection is read, so the family could not answer for any table. The
shape checks below pin the projection against the view's real column set, and
the live cases drive the neutral ``get_partition_state`` against a server.
"""

import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.introspection import (
    MariaDBPartitionQuery,
)
from rhosocial.activerecord.backend.introspection.types import (
    PartitionScheme,
    PartitionState,
)

_PARTITIONED_DDL = """
CREATE TABLE partition_demo (
    id INT NOT NULL,
    created_at DATETIME NOT NULL
) PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION p_future VALUES LESS THAN MAXVALUE
)
"""


def _sql(schema="app", table_name="partition_demo", include_stats=True):
    return MariaDBPartitionQuery(
        MariaDBDialect(),
        schema=schema,
        table_name=table_name,
        include_stats=include_stats,
    ).to_sql()


class TestPartitionStatementShape:
    """The projection must stay inside the view's published columns."""

    def test_subpartition_description_is_not_projected(self):
        sql, _ = _sql()
        assert "SUBPARTITION_DESCRIPTION" not in sql
        # The columns the view really publishes stay in place.
        assert "SUBPARTITION_NAME" in sql
        assert "SUBPARTITION_METHOD" in sql
        assert "SUBPARTITION_EXPRESSION" in sql
        assert "SUBPARTITION_ORDINAL_POSITION" in sql

    def test_partition_description_stays_projected(self):
        sql, _ = _sql()
        assert "`PARTITION_DESCRIPTION`" in sql

    def test_tablespace_stays_projected(self):
        sql, _ = _sql()
        assert "`TABLESPACE_NAME`" in sql

    def test_null_partition_sentinel_is_excluded(self):
        sql, _ = _sql()
        assert "`PARTITION_NAME` IS NOT NULL" in sql

    def test_parameters_are_schema_and_table(self):
        _, params = _sql(schema="app", table_name="partition_demo")
        assert params == ("app", "partition_demo")

    def test_without_stats_the_counters_are_not_projected(self):
        sql, _ = _sql(include_stats=False)
        assert "`TABLE_ROWS`" not in sql
        assert "`DATA_LENGTH`" not in sql
        assert "`INDEX_LENGTH`" not in sql


class TestPartitionsLive:
    """The statement has to parse and answer on a real server."""

    def test_get_partition_state_answers_for_a_partitioned_table(
        self, backend_with_tables
    ):
        backend = backend_with_tables
        backend.execute("DROP TABLE IF EXISTS partition_demo")
        backend.execute(_PARTITIONED_DDL)
        try:
            state = backend.introspector.get_partition_state(
                "partition_demo", schema=None
            )
            assert isinstance(state, PartitionState)
            assert state.scheme is PartitionScheme.RANGE
            assert [bound.name for bound in state.bounds] == [
                "p2025",
                "p2026",
                "p_future",
            ]
            assert state.bounds[0].upper == "2026"
            assert state.bounds[-1].upper == "MAXVALUE"
            assert state.bounds[-1].is_maxvalue is True
            assert state.has_default is True
            assert "created_at" in state.key_expression
            # The default does not ask for counters, so no statistic runs.
            assert state.bounds[0].row_count is None
            assert state.bounds[0].size_bytes is None
        finally:
            backend.introspector.clear_cache()
            backend.execute("DROP TABLE IF EXISTS partition_demo")

    def test_get_partition_state_can_ask_for_stats(self, backend_with_tables):
        backend = backend_with_tables
        backend.execute("DROP TABLE IF EXISTS partition_demo")
        backend.execute(_PARTITIONED_DDL)
        try:
            state = backend.introspector.get_partition_state(
                "partition_demo", schema=None, include_stats=True
            )
            assert state.bounds[0].row_count is not None
        finally:
            backend.introspector.clear_cache()
            backend.execute("DROP TABLE IF EXISTS partition_demo")

    def test_unpartitioned_table_answers_scheme_none(self, backend_with_tables):
        state = backend_with_tables.introspector.get_partition_state(
            "users", schema=None
        )
        assert isinstance(state, PartitionState)
        assert state.scheme is None
        assert state.bounds == ()


class TestAsyncPartitionsLive:
    """Asynchronous counterpart of the live cases (same method names)."""

    @pytest.mark.asyncio
    async def test_get_partition_state_answers_for_a_partitioned_table(
        self, async_backend_with_tables
    ):
        backend = async_backend_with_tables
        await backend.execute("DROP TABLE IF EXISTS partition_demo")
        await backend.execute(_PARTITIONED_DDL)
        try:
            state = await backend.introspector.get_partition_state(
                "partition_demo", schema=None
            )
            assert isinstance(state, PartitionState)
            assert state.scheme is PartitionScheme.RANGE
            assert [bound.name for bound in state.bounds] == [
                "p2025",
                "p2026",
                "p_future",
            ]
            assert state.bounds[-1].is_maxvalue is True
            assert state.bounds[0].row_count is None
        finally:
            backend.introspector.clear_cache()
            await backend.execute("DROP TABLE IF EXISTS partition_demo")

    @pytest.mark.asyncio
    async def test_unpartitioned_table_answers_scheme_none(
        self, async_backend_with_tables
    ):
        state = await async_backend_with_tables.introspector.get_partition_state(
            "users", schema=None
        )
        assert isinstance(state, PartitionState)
        assert state.scheme is None
        assert state.bounds == ()
