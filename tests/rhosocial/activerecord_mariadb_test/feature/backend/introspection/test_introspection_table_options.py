# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_introspection_table_options.py
"""Tests for MariaDB table storage-options introspection.

``information_schema.TABLES`` carries base tables, views and sequences in one
list, and ``list_table_options`` returns every row with its ``table_type``:
a caller wanting only base tables filters on that, and the filter is not
applied for it. So a sequence made by a fixture shows up here, and the test
below asserts that it does rather than pretending the list is tables only.

``get_table_options`` narrows the same read by name, which is why a view
answers with ``engine is None`` instead of disappearing: the server reports
no engine for a view, and that is the answer.
"""

from dataclasses import FrozenInstanceError
from typing import Any, Dict, List, Tuple

import pytest

from rhosocial.activerecord.backend.impl.mariadb.introspection.types import (
    TableOptionsInfo,
)
from rhosocial.activerecord.backend.introspection.executor import (
    AsyncIntrospectorExecutor,
    SyncIntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

from mariadb_live_server import mariadb_server_available

pytestmark = pytest.mark.skipif(
    not mariadb_server_available(),
    reason="No MariaDB server reachable from the configured scenarios",
)


class CountingExecutor(SyncIntrospectorExecutor):
    """An executor that reports how many questions it was asked."""

    def __init__(self, backend: Any) -> None:
        super().__init__(backend)
        self.calls = 0

    def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        self.calls += 1
        return super().execute(sql, params)


class AsyncCountingExecutor(AsyncIntrospectorExecutor):
    """The async counterpart of :class:`CountingExecutor`."""

    def __init__(self, backend: Any) -> None:
        super().__init__(backend)
        self.calls = 0

    async def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        self.calls += 1
        return await super().execute(sql, params)


class TestListTableOptions:
    """Tests for list_table_options."""

    def test_returns_typed_non_empty_results(self, backend_with_tables):
        options = backend_with_tables.introspector.list_table_options()

        assert options
        assert all(isinstance(option, TableOptionsInfo) for option in options)
        names = {option.name for option in options}
        assert "users" in names

    def test_reports_storage_fields_for_users(self, backend_with_tables):
        options = backend_with_tables.introspector.list_table_options()
        users = next(option for option in options if option.name == "users")

        assert users.schema == backend_with_tables.config.database
        assert users.table_type == "BASE TABLE"
        assert users.engine == "InnoDB"
        assert users.row_format
        assert users.collation
        assert users.comment is not None
        assert users.create_options is not None

    def test_keeps_the_fixture_table_alongside_users(self, backend_with_tables):
        options = backend_with_tables.introspector.list_table_options()
        names = {option.name for option in options}

        assert {"users", "posts", "tags", "post_tags"} <= names

    def test_lists_a_sequence_with_its_own_type(
        self, backend_with_sequence_and_table
    ):
        """A sequence is a table, and its row says so."""
        options = backend_with_sequence_and_table.introspector.list_table_options()
        by_name = {option.name: option for option in options}

        assert "intro_seq" in by_name
        assert by_name["intro_seq"].table_type == "SEQUENCE"

    def test_result_is_frozen(self, backend_with_tables):
        options = backend_with_tables.introspector.list_table_options()

        with pytest.raises(FrozenInstanceError):
            options[0].engine = "MyISAM"  # type: ignore[misc]

    def test_cache_returns_the_same_list(self, backend_with_tables):
        first = backend_with_tables.introspector.list_table_options()
        second = backend_with_tables.introspector.list_table_options()

        assert first is second

    def test_table_options_do_not_answer_the_table_list(
        self, backend_with_tables
    ):
        """Two families share a scope, so they must not share an entry."""
        introspector = backend_with_tables.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_tables)
        introspector._executor = executor

        introspector.list_table_options()
        cold = executor.calls
        introspector.list_tables()

        assert executor.calls > cold

    def test_warm_cache_asks_the_server_nothing(self, backend_with_tables):
        introspector = backend_with_tables.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_tables)
        introspector._executor = executor

        introspector.list_table_options()
        cold = executor.calls
        introspector.list_table_options()

        assert cold > 0
        assert executor.calls == cold

    def test_invalidating_by_table_name_drops_the_record_not_the_list(
        self, backend_with_tables
    ):
        """A name-based invalidation drops what carries the name.

        The record is keyed by the table it is about; the list is keyed by
        the schema, so it names no table and survives. That asymmetry is the
        cache's key policy rather than this backend's, and the assertion keeps
        the new namespace out of it: neither entry answers the other's
        question either way.
        """
        introspector = backend_with_tables.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_tables)
        introspector._executor = executor

        introspector.get_table_options("users")
        introspector.list_table_options()
        cold = executor.calls

        introspector.invalidate_cache(scope=IntrospectionScope.TABLE, name="users")

        introspector.get_table_options("users")
        assert executor.calls > cold
        after_record = executor.calls
        introspector.list_table_options()
        assert executor.calls == after_record

    def test_invalidating_everything_drops_the_list(self, backend_with_tables):
        introspector = backend_with_tables.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_tables)
        introspector._executor = executor

        introspector.list_table_options()
        cold = executor.calls
        introspector.invalidate_cache()
        introspector.list_table_options()

        assert executor.calls > cold


class TestGetTableOptions:
    """Tests for get_table_options."""

    def test_returns_typed_result(self, backend_with_tables):
        options = backend_with_tables.introspector.get_table_options("users")

        assert isinstance(options, TableOptionsInfo)
        assert options.name == "users"
        assert options.schema == backend_with_tables.config.database
        assert options.table_type == "BASE TABLE"
        assert options.engine == "InnoDB"

    def test_returns_a_sequence_by_name(self, backend_with_sequence_and_table):
        options = backend_with_sequence_and_table.introspector.get_table_options(
            "intro_seq"
        )

        assert isinstance(options, TableOptionsInfo)
        assert options.table_type == "SEQUENCE"

    def test_missing_table_returns_none(self, backend_with_tables):
        assert (
            backend_with_tables.introspector.get_table_options(
                "table_options_does_not_exist"
            )
            is None
        )

    def test_cache_returns_the_same_record(self, backend_with_tables):
        introspector = backend_with_tables.introspector
        first = introspector.get_table_options("users")
        second = introspector.get_table_options("users")

        assert first is second

    def test_warm_cache_asks_the_server_nothing(self, backend_with_tables):
        introspector = backend_with_tables.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_tables)
        introspector._executor = executor

        introspector.get_table_options("users")
        cold = executor.calls
        introspector.get_table_options("users")

        assert cold > 0
        assert executor.calls == cold


class TestAsyncTableOptions:
    """Async parity for table storage options."""

    @pytest.mark.asyncio
    async def test_returns_typed_non_empty_results(self, async_backend_with_tables):
        options = await async_backend_with_tables.introspector.list_table_options()

        assert options
        assert all(isinstance(option, TableOptionsInfo) for option in options)
        assert "users" in {option.name for option in options}

    @pytest.mark.asyncio
    async def test_returns_typed_record(self, async_backend_with_tables):
        options = await async_backend_with_tables.introspector.get_table_options(
            "users"
        )

        assert isinstance(options, TableOptionsInfo)
        assert options.engine == "InnoDB"

    @pytest.mark.asyncio
    async def test_missing_table_returns_none(self, async_backend_with_tables):
        options = await async_backend_with_tables.introspector.get_table_options(
            "table_options_does_not_exist"
        )

        assert options is None

    @pytest.mark.asyncio
    async def test_warm_cache_asks_the_server_nothing(self, async_backend_with_tables):
        introspector = async_backend_with_tables.introspector
        introspector.clear_cache()
        executor = AsyncCountingExecutor(async_backend_with_tables)
        introspector._executor = executor

        await introspector.list_table_options()
        await introspector.get_table_options("users")
        cold = executor.calls
        await introspector.list_table_options()
        await introspector.get_table_options("users")

        assert cold > 0
        assert executor.calls == cold
