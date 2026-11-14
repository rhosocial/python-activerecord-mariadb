# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/introspection/test_introspection_partitions.py
"""Partitions listing: statement shape and live execution.

MariaDB's ``information_schema.PARTITIONS`` publishes 25 columns: it has the
subpartition name, method, expression and ordinal, but **no**
``SUBPARTITION_DESCRIPTION``. A statement that projects that column is rejected
by the server at parse time (``Unknown column ... in 'field list'``) no matter
which projection is read, so the family could not answer for any table. The
shape checks below pin the projection against the view's real column set, and
the live cases drive the family against a server.
"""

import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.introspection import (
    MariaDBPartitionQuery,
)
from rhosocial.activerecord.backend.impl.mariadb.introspection.types import (
    MariaDBPartitionInfo,
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


def _sql(schema="app", table_name="partition_demo"):
    return MariaDBPartitionQuery(
        MariaDBDialect(), schema=schema, table_name=table_name
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

    def test_null_partition_sentinel_is_excluded(self):
        sql, _ = _sql()
        assert "`PARTITION_NAME` IS NOT NULL" in sql

    def test_parameters_are_schema_and_table(self):
        _, params = _sql(schema="app", table_name="partition_demo")
        assert params == ("app", "partition_demo")


class TestPartitionsLive:
    """The statement has to parse and answer on a real server."""

    def test_list_partitions_answers_for_a_partitioned_table(self, backend_with_tables):
        backend = backend_with_tables
        backend.execute("DROP TABLE IF EXISTS partition_demo")
        backend.execute(_PARTITIONED_DDL)
        try:
            partitions = backend.introspector.list_partitions(
                "partition_demo", schema=None
            )
            assert isinstance(partitions, list)
            assert partitions
            for partition in partitions:
                assert isinstance(partition, MariaDBPartitionInfo)
                assert partition.partition_name
                assert partition.subpartition_description is None
        finally:
            backend.introspector.clear_cache()
            backend.execute("DROP TABLE IF EXISTS partition_demo")

    def test_list_partitions_is_empty_for_a_non_partitioned_table(
        self, backend_with_tables
    ):
        partitions = backend_with_tables.introspector.list_partitions(
            "users", schema=None
        )
        assert partitions == []


class TestAsyncPartitionsLive:
    """Asynchronous counterpart of the live cases (same method names)."""

    @pytest.mark.asyncio
    async def test_list_partitions_answers_for_a_partitioned_table(
        self, async_backend_with_tables
    ):
        backend = async_backend_with_tables
        await backend.execute("DROP TABLE IF EXISTS partition_demo")
        await backend.execute(_PARTITIONED_DDL)
        try:
            partitions = await backend.introspector.list_partitions(
                "partition_demo", schema=None
            )
            assert isinstance(partitions, list)
            assert partitions
            for partition in partitions:
                assert isinstance(partition, MariaDBPartitionInfo)
                assert partition.partition_name
                assert partition.subpartition_description is None
        finally:
            backend.introspector.clear_cache()
            await backend.execute("DROP TABLE IF EXISTS partition_demo")

    @pytest.mark.asyncio
    async def test_list_partitions_is_empty_for_a_non_partitioned_table(
        self, async_backend_with_tables
    ):
        partitions = await async_backend_with_tables.introspector.list_partitions(
            "users", schema=None
        )
        assert partitions == []
