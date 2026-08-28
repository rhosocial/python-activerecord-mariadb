# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_autocommit_backend.py
"""Offline tests for the MariaDB backend auto-commit handlers."""
import pytest

from rhosocial.activerecord.backend.impl.mariadb import (
    AsyncMariaDBBackend,
    MariaDBBackend,
)
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


def make_config(**overrides) -> MariaDBConnectionConfig:
    params = dict(
        host="localhost",
        port=3306,
        database="test",
        username="root",
        password="",
    )
    params.update(overrides)
    return MariaDBConnectionConfig(**params)


class FakeConnection:
    def __init__(self):
        self.commit_count = 0

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        pass


class FakeAsyncConnection:
    def __init__(self):
        self.commit_count = 0

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        pass


class TestSyncAutoCommit:
    def test_handle_auto_commit_commits_when_disabled(self):
        backend = MariaDBBackend(connection_config=make_config())
        backend._connection = FakeConnection()
        backend._handle_auto_commit()
        assert backend._connection.commit_count == 1

    def test_handle_auto_commit_skips_when_enabled(self):
        backend = MariaDBBackend(connection_config=make_config(autocommit=True))
        backend._connection = FakeConnection()
        backend._handle_auto_commit()
        assert backend._connection.commit_count == 0

    def test_handle_auto_commit_noop_without_connection(self):
        backend = MariaDBBackend(connection_config=make_config())
        backend._handle_auto_commit()

    def test_handle_auto_commit_if_needed_commits_when_disabled(self):
        backend = MariaDBBackend(connection_config=make_config())
        backend._connection = FakeConnection()
        backend._handle_auto_commit_if_needed()
        assert backend._connection.commit_count == 1

    def test_handle_auto_commit_if_needed_skips_when_enabled(self):
        backend = MariaDBBackend(connection_config=make_config(autocommit=True))
        backend._connection = FakeConnection()
        backend._handle_auto_commit_if_needed()
        assert backend._connection.commit_count == 0

    def test_handle_auto_commit_swallows_commit_error(self):
        backend = MariaDBBackend(connection_config=make_config())

        class _Failing:
            def commit(self):
                raise RuntimeError("connection lost")

        backend._connection = _Failing()
        backend._handle_auto_commit()


class TestAsyncAutoCommit:
    @pytest.mark.asyncio
    async def test_handle_auto_commit_commits_when_disabled(self):
        backend = AsyncMariaDBBackend(connection_config=make_config())
        backend._connection = FakeAsyncConnection()
        await backend._handle_auto_commit()
        assert backend._connection.commit_count == 1

    @pytest.mark.asyncio
    async def test_handle_auto_commit_skips_when_enabled(self):
        backend = AsyncMariaDBBackend(connection_config=make_config(autocommit=True))
        backend._connection = FakeAsyncConnection()
        await backend._handle_auto_commit()
        assert backend._connection.commit_count == 0

    @pytest.mark.asyncio
    async def test_handle_auto_commit_if_needed_commits_when_disabled(self):
        backend = AsyncMariaDBBackend(connection_config=make_config())
        backend._connection = FakeAsyncConnection()
        await backend._handle_auto_commit_if_needed()
        assert backend._connection.commit_count == 1

    @pytest.mark.asyncio
    async def test_handle_auto_commit_if_needed_skips_when_enabled(self):
        backend = AsyncMariaDBBackend(connection_config=make_config(autocommit=True))
        backend._connection = FakeAsyncConnection()
        await backend._handle_auto_commit_if_needed()
        assert backend._connection.commit_count == 0

    @pytest.mark.asyncio
    async def test_handle_auto_commit_swallows_commit_error(self):
        backend = AsyncMariaDBBackend(connection_config=make_config())

        class _Failing:
            async def commit(self):
                raise RuntimeError("connection lost")

        backend._connection = _Failing()
        await backend._handle_auto_commit()
