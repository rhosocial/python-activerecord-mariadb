# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_concurrency_protocol.py
"""
Test for ConcurrencyAware protocol implementation in MariaDB backend.

This test verifies that MariaDBBackend correctly implements the ConcurrencyAware
protocol by fetching max_connections during connect and returning the appropriate
concurrency hint.
"""
import pytest

from rhosocial.activerecord.backend.protocols import ConcurrencyAware, ConcurrencyHint


class TestMySQLConcurrencyAware:
    """Test ConcurrencyAware protocol implementation for MariaDB backend."""

    def test_mariadb_backend_implements_protocol(self, mariadb_backend_single):
        """Test that MariaDBBackend implements ConcurrencyAware protocol."""
        assert isinstance(mariadb_backend_single, ConcurrencyAware)

    def test_mysql_get_concurrency_hint(self, mariadb_backend_single):
        """Test MariaDBBackend returns correct concurrency hint."""
        hint = mariadb_backend_single.get_concurrency_hint()

        assert hint is not None
        assert isinstance(hint, ConcurrencyHint)
        assert hint.max_concurrency is not None
        assert hint.max_concurrency > 0
        assert "max_connections" in hint.reason
        assert "pool_size" in hint.reason

    def test_mysql_concurrency_hint_value(self, mariadb_backend_single):
        """Test concurrency hint value is bounded by pool_size."""
        pool_size = mariadb_backend_single.config.pool_size or 5
        hint = mariadb_backend_single.get_concurrency_hint()

        assert hint.max_concurrency <= pool_size
        assert hint.max_concurrency > 0

    def test_mysql_concurrency_hint_not_none_after_connect(self, mariadb_backend_single):
        """Test that concurrency hint is populated after connect."""
        assert mariadb_backend_single._connection is not None
        assert mariadb_backend_single.get_concurrency_hint() is not None


class TestAsyncMySQLConcurrencyAware:
    """Test ConcurrencyAware protocol implementation for async MariaDB backend."""

    @pytest.mark.asyncio
    async def test_async_mariadb_backend_implements_protocol(self, async_mariadb_backend_single):
        """Test that AsyncMariaDBBackend implements ConcurrencyAware protocol."""
        assert isinstance(async_mariadb_backend_single, ConcurrencyAware)

    @pytest.mark.asyncio
    async def test_async_mysql_get_concurrency_hint(self, async_mariadb_backend_single):
        """Test AsyncMariaDBBackend returns correct concurrency hint."""
        hint = async_mariadb_backend_single.get_concurrency_hint()

        assert hint is not None
        assert isinstance(hint, ConcurrencyHint)
        assert hint.max_concurrency is not None
        assert hint.max_concurrency > 0
        assert "max_connections" in hint.reason
        assert "pool_size" in hint.reason

    @pytest.mark.asyncio
    async def test_async_mysql_concurrency_hint_value(self, async_mariadb_backend_single):
        """Test async concurrency hint value is bounded by pool_size."""
        pool_size = async_mariadb_backend_single.config.pool_size or 5
        hint = async_mariadb_backend_single.get_concurrency_hint()

        assert hint.max_concurrency <= pool_size
        assert hint.max_concurrency > 0

    @pytest.mark.asyncio
    async def test_async_mysql_concurrency_hint_not_none_after_connect(
        self, async_mariadb_backend_single
    ):
        """Test that async concurrency hint is populated after connect."""
        assert async_mariadb_backend_single._connection is not None
        assert async_mariadb_backend_single.get_concurrency_hint() is not None