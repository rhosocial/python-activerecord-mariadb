# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_execute_error_contract.py
"""Database-free tests for the MariaDB execute error contract.

Each phase of ``execute`` / ``execute_many`` has a fixed error type:

- transient framework connection errors are retried after a reconnect;
- non-transient and exhausted errors are raised unchanged (no second
  translation by ``_handle_error``);
- an auto-commit failure is a ``TransactionError`` carrying the driver error;
- batch deadlocks keep their ``DeadlockError`` semantics and a successful
  batch commits before the result is returned;
- a failing ``cursor.close()`` never replaces the error in flight.

The tests patch ``ExecutionMixin.execute`` or drive fake cursors, so no
MariaDB server is needed. Sync and async cases share method names under the
``Test*`` / ``TestAsync*`` classes, following the repository's parity rule.
"""

import logging
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

mariadb = pytest.importorskip("mariadb")

from rhosocial.activerecord.backend.base.execution import (  # noqa: E402
    AsyncExecutionMixin,
    ExecutionMixin,
)
from rhosocial.activerecord.backend.errors import (  # noqa: E402
    DeadlockError,
    OperationalError,
    TransactionError,
    attach_diagnostics,
)
from rhosocial.activerecord.backend.impl.mariadb.backend import (  # noqa: E402
    AsyncMariaDBBackend,
    MariaDBBackend,
)
from rhosocial.activerecord.backend.result import QueryResult  # noqa: E402

_LOGGER_NAME = "rhosocial.activerecord.backend.mariadb"


def _make_backend(**overrides) -> MariaDBBackend:
    """Build a sync backend without opening a connection."""
    return MariaDBBackend(database="execute_contract_db", **overrides)


def _make_async_backend(**overrides) -> AsyncMariaDBBackend:
    """Build an async backend without opening a connection."""
    return AsyncMariaDBBackend(database="execute_contract_db", **overrides)


def _transient_error() -> OperationalError:
    """A lost connection, as the shared mapper reports it."""
    return attach_diagnostics(
        OperationalError("Lost connection to server during query"),
        operation="execute",
        driver_code=2013,
        backend="mariadb",
        transient=True,
    )


def _non_transient_error(transient=False) -> OperationalError:
    """A shutdown/permission failure, which a retry cannot fix."""
    return attach_diagnostics(
        OperationalError("Server shutdown in progress"),
        operation="execute",
        driver_code=1053,
        backend="mariadb",
        transient=transient,
    )


def _deadlock_driver_error() -> "mariadb.Error":
    return mariadb.Error(
        "Deadlock found when trying to get lock; try restarting transaction",
        1213,
    )


class _CommitFailingConnection:
    """Connection whose ``commit()`` raises a supplied driver error."""

    def __init__(self, failure: Exception):
        self.failure = failure
        self.commit_count = 0

    def cursor(self):
        return None

    def commit(self):
        self.commit_count += 1
        raise self.failure


class _AsyncCommitFailingConnection(_CommitFailingConnection):
    async def commit(self):
        self.commit_count += 1
        raise self.failure


class _BatchConnection:
    """Connection that counts commits and exposes no real cursor."""

    def __init__(self):
        self.commit_count = 0

    def cursor(self):
        return None

    def commit(self):
        self.commit_count += 1


class _AsyncBatchConnection(_BatchConnection):
    async def commit(self):
        self.commit_count += 1


class _DeadlockCursor:
    """Sync cursor whose ``executemany`` raises the supplied error."""

    def __init__(self, error: Exception):
        self.error = error
        self.rowcount = 0
        self.executemany_calls = 0
        self.closed = False

    def executemany(self, sql, params_list):
        self.executemany_calls += 1
        raise self.error

    def close(self):
        self.closed = True


class _AsyncDeadlockCursor:
    """Async cursor that raises on the first ``execute`` and on ``close``."""

    def __init__(self, error: Exception, close_error: Optional[Exception] = None):
        self.error = error
        self.close_error = close_error
        self.rowcount = 0
        self.execute_calls = 0
        self.closed = False

    async def execute(self, sql, params=None):
        self.execute_calls += 1
        raise self.error

    async def close(self):
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class _AsyncBatchCursor:
    """Async cursor that succeeds and records rowcount."""

    def __init__(self, rowcount=1):
        self.rowcount = rowcount
        self.execute_calls = 0
        self.closed = False

    async def execute(self, sql, params=None):
        self.execute_calls += 1

    async def close(self):
        self.closed = True


class TestExecuteRetry:
    """Retry policy of the synchronous execute wrapper."""

    def test_transient_error_reconnects_and_retries(self, monkeypatch):
        backend = _make_backend()
        backend._reconnect = MagicMock(return_value=True)
        attempts = []

        def fake_execute(self, sql, params=None, *, options=None):
            attempts.append(sql)
            if len(attempts) == 1:
                raise _transient_error()
            return QueryResult(affected_rows=1, duration=0.0)

        monkeypatch.setattr(ExecutionMixin, "execute", fake_execute)

        result = backend.execute("SELECT 1", max_retries=1)

        assert result.affected_rows == 1
        assert len(attempts) == 2
        assert backend._reconnect.call_count == 1

    @pytest.mark.parametrize("transient", [False, None])
    def test_non_transient_error_is_not_retried(self, monkeypatch, transient):
        backend = _make_backend()
        backend._reconnect = MagicMock(return_value=True)
        error = _non_transient_error(transient=transient)
        attempts = []

        def fake_execute(self, sql, params=None, *, options=None):
            attempts.append(sql)
            raise error

        monkeypatch.setattr(ExecutionMixin, "execute", fake_execute)

        with pytest.raises(OperationalError) as exc_info:
            backend.execute("SELECT 1", max_retries=2)

        assert exc_info.value is error
        assert len(attempts) == 1
        backend._reconnect.assert_not_called()

    def test_exhausted_retry_raises_original_error(self, monkeypatch):
        backend = _make_backend()
        backend._reconnect = MagicMock(return_value=True)
        backend._handle_error = MagicMock()
        error = _transient_error()

        def fake_execute(self, sql, params=None, *, options=None):
            raise error

        monkeypatch.setattr(ExecutionMixin, "execute", fake_execute)

        with pytest.raises(OperationalError) as exc_info:
            backend.execute("SELECT 1", max_retries=1)

        # The framework error is raised as-is: no second mapping, no rewrapping.
        assert exc_info.value is error
        assert backend._reconnect.call_count == 1
        backend._handle_error.assert_not_called()


class TestAsyncExecuteRetry:
    """The async execute wrapper follows the same retry policy."""

    @pytest.mark.asyncio
    async def test_transient_error_reconnects_and_retries(self, monkeypatch):
        backend = _make_async_backend()
        backend._reconnect = AsyncMock(return_value=True)
        attempts = []

        async def fake_execute(self, sql, params=None, *, options=None):
            attempts.append(sql)
            if len(attempts) == 1:
                raise _transient_error()
            return QueryResult(affected_rows=1, duration=0.0)

        monkeypatch.setattr(AsyncExecutionMixin, "execute", fake_execute)

        result = await backend.execute("SELECT 1", max_retries=1)

        assert result.affected_rows == 1
        assert len(attempts) == 2
        backend._reconnect.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("transient", [False, None])
    async def test_non_transient_error_is_not_retried(self, monkeypatch, transient):
        backend = _make_async_backend()
        backend._reconnect = AsyncMock(return_value=True)
        error = _non_transient_error(transient=transient)
        attempts = []

        async def fake_execute(self, sql, params=None, *, options=None):
            attempts.append(sql)
            raise error

        monkeypatch.setattr(AsyncExecutionMixin, "execute", fake_execute)

        with pytest.raises(OperationalError) as exc_info:
            await backend.execute("SELECT 1", max_retries=2)

        assert exc_info.value is error
        assert len(attempts) == 1
        backend._reconnect.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_exhausted_retry_raises_original_error(self, monkeypatch):
        backend = _make_async_backend()
        backend._reconnect = AsyncMock(return_value=True)
        backend._handle_error = AsyncMock()
        error = _transient_error()

        async def fake_execute(self, sql, params=None, *, options=None):
            raise error

        monkeypatch.setattr(AsyncExecutionMixin, "execute", fake_execute)

        with pytest.raises(OperationalError) as exc_info:
            await backend.execute("SELECT 1", max_retries=1)

        assert exc_info.value is error
        backend._reconnect.assert_awaited_once()
        backend._handle_error.assert_not_awaited()


class TestAutoCommit:
    """Commit failures must not be swallowed."""

    def test_commit_failure_raises_transaction_error(self):
        backend = _make_backend()
        failure = mariadb.Error("Lost connection during commit", 2013)
        backend._connection = _CommitFailingConnection(failure)

        with pytest.raises(TransactionError) as exc_info:
            backend._handle_auto_commit()

        assert exc_info.value.__cause__ is failure
        assert backend._connection.commit_count == 1

    def test_autocommit_enabled_does_not_commit(self):
        backend = _make_backend(autocommit=True)
        backend._connection = _CommitFailingConnection(RuntimeError("unused"))

        backend._handle_auto_commit()

        assert backend._connection.commit_count == 0


class TestAsyncAutoCommit:
    """Async counterpart of the commit contract."""

    @pytest.mark.asyncio
    async def test_commit_failure_raises_transaction_error(self):
        backend = _make_async_backend()
        failure = mariadb.Error("Lost connection during commit", 2013)
        backend._connection = _AsyncCommitFailingConnection(failure)

        with pytest.raises(TransactionError) as exc_info:
            await backend._handle_auto_commit()

        assert exc_info.value.__cause__ is failure
        assert backend._connection.commit_count == 1

    @pytest.mark.asyncio
    async def test_autocommit_enabled_does_not_commit(self):
        backend = _make_async_backend(autocommit=True)
        backend._connection = _AsyncCommitFailingConnection(RuntimeError("unused"))

        await backend._handle_auto_commit()

        assert backend._connection.commit_count == 0


class TestExecuteMany:
    """Batch execution uses the shared mapper and commits before returning."""

    def test_deadlock_maps_to_deadlock_error(self):
        backend = _make_backend()
        connection = _BatchConnection()
        backend._connection = connection
        backend._cursor = _DeadlockCursor(_deadlock_driver_error())
        backend._transaction_manager = SimpleNamespace(is_active=False)

        with pytest.raises(DeadlockError) as exc_info:
            backend.execute_many("UPDATE t SET v = %s WHERE id = %s", [(1, 1)])

        mapped = exc_info.value
        assert mapped.driver_code == 1213
        assert mapped.transient is True
        assert mapped.operation == "execute"
        assert mapped.backend == "mariadb"
        # A deadlocked batch must never be reported as committed.
        assert connection.commit_count == 0

    def test_commit_runs_before_successful_result(self):
        backend = _make_backend()
        connection = _BatchConnection()
        backend._connection = connection
        cursor = _DeadlockCursor(_deadlock_driver_error())
        cursor.executemany = lambda sql, params_list: setattr(cursor, "rowcount", 2)
        backend._cursor = cursor
        backend._transaction_manager = SimpleNamespace(is_active=False)

        result = backend.execute_many("INSERT INTO t VALUES (%s)", [(1,), (2,)])

        assert result.affected_rows == 2
        assert connection.commit_count == 1

    def test_commit_failure_propagates_as_transaction_error(self):
        backend = _make_backend()
        failure = mariadb.Error("Lost connection during commit", 2013)
        backend._connection = _CommitFailingConnection(failure)
        cursor = _DeadlockCursor(_deadlock_driver_error())
        cursor.executemany = lambda sql, params_list: setattr(cursor, "rowcount", 1)
        backend._cursor = cursor
        backend._transaction_manager = SimpleNamespace(is_active=False)

        with pytest.raises(TransactionError) as exc_info:
            backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])

        assert exc_info.value.__cause__ is failure


class TestAsyncExecuteMany:
    """Async batch execution follows the same contract."""

    @pytest.mark.asyncio
    async def test_deadlock_maps_to_deadlock_error(self):
        backend = _make_async_backend()
        connection = _AsyncBatchConnection()
        cursor = _AsyncDeadlockCursor(_deadlock_driver_error())
        backend._connection = connection
        backend._get_cursor = AsyncMock(return_value=cursor)

        with pytest.raises(DeadlockError) as exc_info:
            await backend.execute_many("UPDATE t SET v = %s", [(1,)])

        mapped = exc_info.value
        assert mapped.driver_code == 1213
        assert mapped.transient is True
        assert connection.commit_count == 0
        assert cursor.closed is True

    @pytest.mark.asyncio
    async def test_close_failure_does_not_mask_original_error(self, caplog):
        backend = _make_async_backend()
        backend._connection = _AsyncBatchConnection()
        cursor = _AsyncDeadlockCursor(
            _deadlock_driver_error(),
            close_error=RuntimeError("close failed"),
        )
        backend._get_cursor = AsyncMock(return_value=cursor)

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(DeadlockError):
                await backend.execute_many("UPDATE t SET v = %s", [(1,)])

        assert "Ignoring cursor close error" in caplog.text

    @pytest.mark.asyncio
    async def test_commit_runs_before_successful_result(self):
        backend = _make_async_backend()
        connection = _AsyncBatchConnection()
        cursor = _AsyncBatchCursor(rowcount=1)
        backend._connection = connection
        backend._get_cursor = AsyncMock(return_value=cursor)

        result = await backend.execute_many("INSERT INTO t VALUES (%s)", [(1,), (2,)])

        assert result.affected_rows == 2
        assert connection.commit_count == 1

    @pytest.mark.asyncio
    async def test_commit_failure_propagates_as_transaction_error(self):
        backend = _make_async_backend()
        failure = mariadb.Error("Lost connection during commit", 2013)
        backend._connection = _AsyncCommitFailingConnection(failure)
        cursor = _AsyncBatchCursor(rowcount=1)
        backend._get_cursor = AsyncMock(return_value=cursor)

        with pytest.raises(TransactionError) as exc_info:
            await backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])

        assert exc_info.value.__cause__ is failure


class TestExecuteReturnContract:
    """``execute`` always returns a result or raises; it never returns None."""

    def test_signature_declares_query_result(self):
        import inspect

        from typing import get_type_hints

        hints = get_type_hints(MariaDBBackend.execute)
        assert hints["return"] is QueryResult

        async_hints = get_type_hints(AsyncMariaDBBackend.execute)
        assert async_hints["return"] is QueryResult

        # Guards against a future edit reintroducing Optional[QueryResult].
        assert inspect.signature(MariaDBBackend.execute).return_annotation is QueryResult
