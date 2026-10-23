# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_introspection_sequences.py
"""Tests for MariaDB sequence introspection.

A sequence is a table on MariaDB, so ``list_sequences`` reads
``information_schema.TABLES`` filtered to ``TABLE_TYPE='SEQUENCE'``. The
numeric details -- start, bounds, increment and cycle -- live in a view this
backend only joins from 11.7 on, so on 10.3 through 11.6 the sequence is
still listed and those fields are ``None`` rather than defaults: a server
that says nothing has said ``None``, not ``START WITH 1``.

``cache_size`` is ``None`` on every server, and the test below says so rather
than asserting a number that no view reports.
"""

from dataclasses import FrozenInstanceError
from typing import Any, Dict, List, Tuple

import pytest

from rhosocial.activerecord.backend.impl.mariadb.introspection.types import (
    SequenceInfo,
)
from rhosocial.activerecord.backend.impl.mariadb.mixins.introspection import (
    SEQUENCE_DETAILS_SINCE,
    SEQUENCES_SINCE,
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


def _server_reports_details(backend) -> bool:
    """Whether this server has ``information_schema.SEQUENCES`` to read."""
    return backend.dialect.version >= SEQUENCE_DETAILS_SINCE


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


class TestListSequences:
    """Tests for list_sequences."""

    def test_server_without_sequences_is_empty_and_questionless(
        self, mariadb_backend_single, monkeypatch
    ):
        """Below 10.3 no sequence can exist, so the answer is a question.

        The list is written to the cache either way, so the version gate
        costs nothing on the second ask.
        """
        backend = mariadb_backend_single
        introspector = backend.introspector
        executor = CountingExecutor(backend)
        introspector._executor = executor
        monkeypatch.setattr(backend, "_version", (10, 2, 44))

        sequences = introspector.list_sequences()

        assert sequences == []
        assert executor.calls == 0
        assert introspector.list_sequences() is sequences

    def test_returns_typed_results(self, backend_with_sequence_and_table):
        sequences = backend_with_sequence_and_table.introspector.list_sequences()

        assert isinstance(sequences, list)
        assert sequences, "the fixture created a sequence, so the list is not empty"
        assert all(isinstance(seq, SequenceInfo) for seq in sequences)

    def test_lists_the_created_sequence(self, backend_with_sequence_and_table):
        sequences = backend_with_sequence_and_table.introspector.list_sequences()
        intro_seq = next(
            (seq for seq in sequences if seq.name == "intro_seq"), None
        )

        assert intro_seq is not None
        assert intro_seq.schema == backend_with_sequence_and_table.config.database

    def test_does_not_list_base_tables(self, backend_with_sequence_and_table):
        """A sequence is a table, but the filter keeps base tables out."""
        sequences = backend_with_sequence_and_table.introspector.list_sequences()
        names = {seq.name for seq in sequences}

        assert "intro_options" not in names

    def test_reports_the_declared_limits(self, backend_with_sequence_and_table):
        """The numbers are the server's, or ``None`` -- never this backend's."""
        backend = backend_with_sequence_and_table
        sequences = backend.introspector.list_sequences()
        intro_seq = next(seq for seq in sequences if seq.name == "intro_seq")

        if _server_reports_details(backend_with_sequence_and_table):
            assert intro_seq.start_value == 10
            assert intro_seq.minimum_value == 5
            assert intro_seq.maximum_value == 100
            assert intro_seq.increment == 2
            assert intro_seq.cycle is True
            assert intro_seq.data_type
        else:
            assert intro_seq.start_value is None
            assert intro_seq.minimum_value is None
            assert intro_seq.maximum_value is None
            assert intro_seq.increment is None
            assert intro_seq.cycle is None
            assert intro_seq.data_type is None

    def test_cache_size_is_not_exposed(self, backend_with_sequence_and_table):
        """No information_schema view carries a sequence's cache size."""
        sequences = backend_with_sequence_and_table.introspector.list_sequences()
        intro_seq = next(seq for seq in sequences if seq.name == "intro_seq")

        assert intro_seq.cache_size is None

    def test_result_is_frozen(self, backend_with_sequence_and_table):
        sequences = backend_with_sequence_and_table.introspector.list_sequences()

        with pytest.raises(FrozenInstanceError):
            sequences[0].name = "renamed"  # type: ignore[misc]

    def test_cache_returns_the_same_list(self, backend_with_sequence_and_table):
        introspector = backend_with_sequence_and_table.introspector
        first = introspector.list_sequences()
        second = introspector.list_sequences()

        assert first is second

    def test_warm_cache_asks_the_server_nothing(
        self, backend_with_sequence_and_table
    ):
        introspector = backend_with_sequence_and_table.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_sequence_and_table)
        introspector._executor = executor

        introspector.list_sequences()
        cold = executor.calls
        introspector.list_sequences()

        assert cold > 0
        assert executor.calls == cold

    def test_invalidating_the_scope_drops_the_list(
        self, backend_with_sequence_and_table
    ):
        introspector = backend_with_sequence_and_table.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_sequence_and_table)
        introspector._executor = executor

        introspector.list_sequences()
        cold = executor.calls
        introspector.invalidate_cache(scope=IntrospectionScope.SEQUENCE)
        introspector.list_sequences()

        assert executor.calls > cold


class TestGetSequenceInfo:
    """Tests for get_sequence_info."""

    def test_returns_typed_result(self, backend_with_sequence):
        info = backend_with_sequence.introspector.get_sequence_info("intro_seq")

        assert isinstance(info, SequenceInfo)
        assert info.name == "intro_seq"
        assert info.schema == backend_with_sequence.config.database

    def test_reports_the_declared_limits(self, backend_with_sequence):
        info = backend_with_sequence.introspector.get_sequence_info("intro_seq")

        if _server_reports_details(backend_with_sequence):
            assert info.start_value == 10
            assert info.minimum_value == 5
            assert info.maximum_value == 100
            assert info.increment == 2
            assert info.cycle is True
        else:
            assert info.start_value is None

    def test_missing_sequence_returns_none(self, backend_with_sequence):
        info = backend_with_sequence.introspector.get_sequence_info(
            "sequence_does_not_exist"
        )

        assert info is None

    def test_cache_returns_the_same_record(self, backend_with_sequence):
        introspector = backend_with_sequence.introspector
        first = introspector.get_sequence_info("intro_seq")
        second = introspector.get_sequence_info("intro_seq")

        assert first is second

    def test_missing_is_not_cached(self, backend_with_sequence):
        """A miss stays a miss: the next CREATE SEQUENCE must be visible."""
        introspector = backend_with_sequence.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_sequence)
        introspector._executor = executor

        assert introspector.get_sequence_info("intro_seq_later") is None
        cold = executor.calls

        # Nothing was stored, so the next miss asks again rather than
        # answering from an absence that a CREATE SEQUENCE has since made
        # a presence.
        assert introspector.get_sequence_info("intro_seq_later") is None
        assert executor.calls > cold

    def test_warm_cache_asks_the_server_nothing(self, backend_with_sequence):
        introspector = backend_with_sequence.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_sequence)
        introspector._executor = executor

        introspector.get_sequence_info("intro_seq")
        cold = executor.calls
        introspector.get_sequence_info("intro_seq")

        assert cold > 0
        assert executor.calls == cold


class TestSupportedScopes:
    """The capability declaration carries the new scope."""

    def test_sequence_scope_is_advertised(self, mariadb_backend_single):
        scopes = mariadb_backend_single.dialect.get_supported_introspection_scopes()

        assert IntrospectionScope.SEQUENCE in scopes

    def test_sequence_introspection_is_supported(self, mariadb_backend_single):
        assert (
            mariadb_backend_single.dialect.supports_sequence_introspection()
            == (mariadb_backend_single.dialect.version >= SEQUENCES_SINCE)
        )


class TestAsyncSequences:
    """Async parity for sequence introspection."""

    @pytest.mark.asyncio
    async def test_returns_typed_results(self, async_backend_with_sequence_and_table):
        backend = async_backend_with_sequence_and_table
        sequences = await backend.introspector.list_sequences()

        assert sequences
        assert all(isinstance(seq, SequenceInfo) for seq in sequences)
        assert "intro_seq" in {seq.name for seq in sequences}

    @pytest.mark.asyncio
    async def test_returns_typed_record(self, async_backend_with_sequence):
        info = await async_backend_with_sequence.introspector.get_sequence_info(
            "intro_seq"
        )

        assert isinstance(info, SequenceInfo)

    @pytest.mark.asyncio
    async def test_missing_sequence_returns_none(self, async_backend_with_sequence):
        info = await async_backend_with_sequence.introspector.get_sequence_info(
            "sequence_does_not_exist"
        )

        assert info is None

    @pytest.mark.asyncio
    async def test_warm_cache_asks_the_server_nothing(
        self, async_backend_with_sequence_and_table
    ):
        introspector = async_backend_with_sequence_and_table.introspector
        introspector.clear_cache()
        executor = AsyncCountingExecutor(async_backend_with_sequence_and_table)
        introspector._executor = executor

        await introspector.list_sequences()
        await introspector.get_sequence_info("intro_seq")
        cold = executor.calls
        await introspector.list_sequences()
        await introspector.get_sequence_info("intro_seq")

        assert cold > 0
        assert executor.calls == cold
