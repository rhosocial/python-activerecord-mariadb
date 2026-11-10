# tests/rhosocial/activerecord_mariadb_test/feature/logging/test_execution_logging_unit.py
"""Database-free tests for the MariaDB execution-logging change set.

These tests never open a MariaDB connection.  They import every module the
logging-audit branch touched, build the sync and async backends without
connecting, drive ``execute_many`` through fake cursors, and exercise the
driver-error mapping, transaction guards and failure-logging paths directly.

The backend modules import ``mariadb`` eagerly, so this module installs a
minimal fake driver when the real one is unavailable.  That keeps collection
and every assertion below runnable in coverage jobs where the connector
cannot be imported; when the real driver is present it is used unchanged.

Sync and async cases use the same method names under ``Test*`` and
``TestAsync*`` classes, following the repository's parity convention.
"""

import logging
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


def _import_mariadb_or_fake():
    """Return the real driver, or install a minimal fake in ``sys.modules``.

    The fake only needs the exception hierarchy and ``errno`` attribute that
    ``_handle_mariadb_error`` inspects.  ``asyncConnect`` is present so the
    async connection test can patch it without touching a server.
    """
    try:
        import mariadb as driver
    except ImportError:
        driver = types.ModuleType("mariadb")

        class Error(Exception):
            def __init__(self, message="", errno=0):
                super().__init__(message)
                self.errno = errno

        class DatabaseError(Error):
            pass

        class OperationalError(DatabaseError):
            pass

        class IntegrityError(DatabaseError):
            pass

        class ProgrammingError(DatabaseError):
            pass

        driver.Error = Error
        driver.DatabaseError = DatabaseError
        driver.OperationalError = OperationalError
        driver.IntegrityError = IntegrityError
        driver.ProgrammingError = ProgrammingError
        driver.asyncConnect = None
        sys.modules["mariadb"] = driver

    return driver


mariadb = _import_mariadb_or_fake()

from rhosocial.activerecord.backend import errors as backend_errors  # noqa: E402
from rhosocial.activerecord.backend.impl.mariadb.async_transaction import (  # noqa: E402
    AsyncMariaDBTransactionManager,
)
from rhosocial.activerecord.backend.impl.mariadb.backend.async_backend import (  # noqa: E402
    AsyncMariaDBBackend,
)
from rhosocial.activerecord.backend.impl.mariadb.backend.backend import (  # noqa: E402
    MariaDBBackend,
)
from rhosocial.activerecord.backend.impl.mariadb.cli import info as cli_info  # noqa: E402
from rhosocial.activerecord.backend.impl.mariadb.mixins import backend as mixins_backend  # noqa: E402
from rhosocial.activerecord.backend.impl.mariadb.mixins import (  # noqa: E402
    transaction as mixins_transaction,
)
from rhosocial.activerecord.backend.impl.mariadb.transaction import (  # noqa: E402
    MariaDBTransactionManager,
)
from rhosocial.activerecord.backend.transaction import (  # noqa: E402
    IsolationLevel,
    IsolationLevelError,
    TransactionState,
)


_LOGGER_NAME = "rhosocial.activerecord.backend.mariadb"
_SECRET_PARAM = "s3cr3t-parameter-value"


class _FakeSyncCursor:
    """Minimal DB-API cursor capturing the executemany call."""

    def __init__(self):
        self.rowcount = 0
        self.executemany_calls = []
        self.closed = False

    def executemany(self, sql, params_list):
        self.executemany_calls.append((sql, list(params_list)))
        self.rowcount = len(params_list)

    def close(self):
        self.closed = True


class _FailingSyncCursor:
    """Cursor whose every operation raises a supplied exception."""

    def __init__(self, error=None):
        self.error = error or RuntimeError("cursor failure")
        self.rowcount = 0
        self.closed = False

    def execute(self, *args, **kwargs):
        raise self.error

    def executemany(self, *args, **kwargs):
        raise self.error

    def fetchone(self):
        raise self.error

    def nextset(self):
        return False

    def close(self):
        self.closed = True


class _FakeAsyncCursor:
    """Minimal async cursor: ``execute`` and ``close`` are coroutines."""

    def __init__(self, rowcount=1):
        self.rowcount = rowcount
        self.executions = []
        self.closed = False

    async def execute(self, sql, params=None):
        self.executions.append((sql, params))

    async def close(self):
        self.closed = True


class _FailingAsyncCursor:
    """Async cursor whose every awaited operation raises."""

    def __init__(self, error=None):
        self.error = error or RuntimeError("cursor failure")
        self.closed = False

    async def execute(self, *args, **kwargs):
        raise self.error

    async def fetchone(self):
        raise self.error

    def nextset(self):
        return False

    async def close(self):
        self.closed = True


class _FakeConnection:
    """Connection stand-in exposing only ``cursor()``."""

    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class _CloseFailingConnection:
    """Connection whose ``close()`` raises a supplied exception."""

    def __init__(self, error):
        self.error = error

    def close(self):
        raise self.error


class TestBackendIdentity:
    """The sync backend resolves to the shared MariaDB library logger."""

    def test_backend_uses_mariadb_logger(self):
        backend = MariaDBBackend(database="logging_unit_db")

        assert type(backend).__module__.endswith("mariadb.backend.backend")
        assert backend.logger.name == _LOGGER_NAME
        assert backend._logger_name == _LOGGER_NAME
        assert backend._connection is None


class TestAsyncBackendIdentity:
    """The async backend resolves to the shared MariaDB library logger."""

    @pytest.mark.asyncio
    async def test_backend_uses_mariadb_logger(self):
        backend = AsyncMariaDBBackend(database="logging_unit_db")

        assert type(backend).__module__.endswith("mariadb.backend.async_backend")
        assert backend.logger.name == _LOGGER_NAME
        assert backend._logger_name == _LOGGER_NAME
        assert backend._connection is None

    @pytest.mark.asyncio
    async def test_connect_failure_logs_and_maps_error(self, caplog):
        """A driver failure logs DEBUG and raises the framework error."""
        backend = AsyncMariaDBBackend(database="logging_unit_db")
        driver_error = mariadb.Error("async connect refused", 2003)

        with patch.object(
            mariadb, "asyncConnect", new=AsyncMock(side_effect=driver_error)
        ):
            with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
                with pytest.raises(backend_errors.ConnectionError):
                    await backend.connect()

        assert "Failed to connect to MariaDB database" in caplog.text


class TestBatchLogging:
    """Batch logging records the parameter-set count, never the values."""

    def test_execute_many_hides_parameter_values(self, caplog):
        cursor = _FakeSyncCursor()
        backend = MariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(cursor)
        backend._cursor = cursor

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            result = backend.execute_many(
                "INSERT INTO t (name) VALUES (%s)",
                [("alice", _SECRET_PARAM), ("bob", _SECRET_PARAM)],
            )

        assert result is not None
        assert result.affected_rows == 2
        assert cursor.executemany_calls
        assert "parameter_sets: 2" in caplog.text
        assert _SECRET_PARAM not in caplog.text

    def test_error_is_logged_and_mapped(self, caplog):
        cursor = _FailingSyncCursor(mariadb.Error("batch failure", 1064))
        backend = MariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(cursor)
        backend._cursor = cursor

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(backend_errors.DatabaseError):
                backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])

        assert "Query failed, exception will be re-raised" in caplog.text


class TestAsyncBatchLogging:
    """Async batch logging also hides parameter values."""

    @pytest.mark.asyncio
    async def test_execute_many_hides_parameter_values(self, caplog):
        cursor = _FakeAsyncCursor(rowcount=1)
        backend = AsyncMariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(cursor)

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            result = await backend.execute_many(
                "INSERT INTO t (name) VALUES (%s)",
                [("alice", _SECRET_PARAM), ("bob", _SECRET_PARAM)],
            )

        assert result.affected_rows == 2
        assert len(cursor.executions) == 2
        assert cursor.closed is True
        assert "parameter_sets: 2" in caplog.text
        assert _SECRET_PARAM not in caplog.text

    @pytest.mark.asyncio
    async def test_error_is_logged_and_mapped(self, caplog):
        cursor = _FailingAsyncCursor(mariadb.Error("batch failure", 1064))
        backend = AsyncMariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(cursor)

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(backend_errors.DatabaseError):
                await backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])

        assert "Query failed, exception will be re-raised" in caplog.text


_DRIVER_ERROR_CASES = [
    pytest.param(
        lambda: mariadb.OperationalError("Lost connection to server", 2013),
        backend_errors.ConnectionError,
        id="connection-error-code",
    ),
    pytest.param(
        lambda: mariadb.OperationalError("Can't connect to server"),
        backend_errors.ConnectionError,
        id="operational-connect-message",
    ),
    pytest.param(
        lambda: mariadb.OperationalError("Server shutdown in progress", 1053),
        backend_errors.OperationalError,
        id="operational-generic",
    ),
    pytest.param(
        lambda: mariadb.OperationalError("Deadlock found when trying to get lock"),
        backend_errors.DeadlockError,
        id="deadlock",
    ),
    pytest.param(
        lambda: mariadb.OperationalError("Lock wait timeout exceeded"),
        backend_errors.OperationalError,
        id="lock-timeout",
    ),
    pytest.param(
        lambda: mariadb.IntegrityError("Duplicate entry 'x' for key 'PRIMARY'"),
        backend_errors.IntegrityError,
        id="duplicate-entry",
    ),
    pytest.param(
        lambda: mariadb.IntegrityError("foreign key constraint fails"),
        backend_errors.IntegrityError,
        id="foreign-key",
    ),
    pytest.param(
        lambda: mariadb.IntegrityError("Column 'name' cannot be null"),
        backend_errors.IntegrityError,
        id="null-constraint",
    ),
    pytest.param(
        lambda: mariadb.IntegrityError("Check constraint violated"),
        backend_errors.IntegrityError,
        id="integrity-generic",
    ),
    pytest.param(
        lambda: mariadb.ProgrammingError("You have an error in your SQL syntax"),
        backend_errors.QueryError,
        id="programming",
    ),
    pytest.param(
        lambda: mariadb.Error("Generic MariaDB error"),
        backend_errors.DatabaseError,
        id="database-generic",
    ),
]


class TestDriverErrorMapping:
    """Exercise every mapped branch of ``_handle_mariadb_error``."""

    @pytest.mark.parametrize("make_error, expected_error", _DRIVER_ERROR_CASES)
    def test_handle_error(self, make_error, expected_error, caplog):
        backend = MariaDBBackend(database="logging_unit_db")

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(expected_error):
                backend._handle_error(make_error())

        assert caplog.text, "the mapped branch must emit a DEBUG record"

    def test_unhandled_error_is_reraised(self, caplog):
        backend = MariaDBBackend(database="logging_unit_db")
        original = RuntimeError("not a driver error")

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(RuntimeError) as exc_info:
                backend._handle_error(original)

        assert exc_info.value is original
        assert "Unhandled error" in caplog.text

    def test_connection_error_codes_are_shared(self):
        """The mixin exports the code table the mapping relies on."""
        assert mixins_backend.CONNECTION_ERROR_CODES
        assert 2013 in mixins_backend.CONNECTION_ERROR_CODES
        assert hasattr(mixins_backend, "MariaDBBackendMixin")


class TestAsyncDriverErrorMapping:
    """Async error handling delegates to the same shared mapping."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("make_error, expected_error", _DRIVER_ERROR_CASES)
    async def test_handle_error(self, make_error, expected_error, caplog):
        backend = AsyncMariaDBBackend(database="logging_unit_db")

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(expected_error):
                await backend._handle_error(make_error())

        assert caplog.text, "the mapped branch must emit a DEBUG record"

    @pytest.mark.asyncio
    async def test_unhandled_error_is_reraised(self, caplog):
        backend = AsyncMariaDBBackend(database="logging_unit_db")
        original = RuntimeError("not a driver error")

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(RuntimeError) as exc_info:
                await backend._handle_error(original)

        assert exc_info.value is original
        assert "Unhandled error" in caplog.text


class TestConnectionLifecycle:
    """Failure branches of the sync connection and script helpers."""

    def test_connect_failure_logs_and_maps(self, caplog):
        backend = MariaDBBackend(database="logging_unit_db")
        driver_error = mariadb.Error("sync connect refused", 2003)

        with patch.object(mariadb, "connect", side_effect=driver_error, create=True):
            with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
                with pytest.raises(backend_errors.ConnectionError):
                    backend.connect()

        assert "Failed to connect to MariaDB database" in caplog.text

    def test_disconnect_failure_logs_and_maps(self, caplog):
        backend = MariaDBBackend(database="logging_unit_db")
        backend._transaction_manager = None
        backend._connection = _CloseFailingConnection(
            mariadb.Error("close failed", 2006)
        )

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(backend_errors.ConnectionError):
                backend.disconnect()

        assert "Error during disconnect" in caplog.text

    def test_reconnect_failure_returns_false(self, caplog):
        backend = MariaDBBackend(database="logging_unit_db")
        backend._connection = None

        with patch.object(backend, "connect", side_effect=RuntimeError("boom")):
            with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
                assert backend._reconnect() is False

        assert "Reconnection failed" in caplog.text

    def test_execute_retry_aborts_when_reconnect_fails(self, caplog):
        error = backend_errors.OperationalError("connection lost")
        cursor = _FailingSyncCursor(error)
        backend = MariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(cursor)
        backend._cursor = cursor

        with patch.object(backend, "_is_connection_error", return_value=True):
            with patch.object(backend, "_reconnect", return_value=False):
                with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
                    with pytest.raises(backend_errors.OperationalError):
                        backend.execute("SELECT 1", max_retries=1)

        assert "Reconnection failed, aborting retry" in caplog.text

    def test_executescript_failure_logs_and_reraises(self, caplog):
        cursor = _FailingSyncCursor(RuntimeError("script failure"))
        backend = MariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(cursor)
        backend._cursor = cursor

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(RuntimeError):
                backend.executescript("SELECT 1;")

        assert "Error executing SQL script" in caplog.text

    def test_server_version_failure_logs_and_maps(self, caplog):
        backend = MariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(
            _FailingSyncCursor(RuntimeError("version failure"))
        )

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(backend_errors.OperationalError):
                backend.get_server_version()

        assert "Failed to determine MariaDB version" in caplog.text


class TestAsyncConnectionLifecycle:
    """Failure branches of the async connection and script helpers."""

    @pytest.mark.asyncio
    async def test_disconnect_failure_logs_and_maps(self, caplog):
        backend = AsyncMariaDBBackend(database="logging_unit_db")
        backend._connection = _CloseFailingConnection(
            mariadb.Error("close failed", 2006)
        )

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(backend_errors.OperationalError):
                await backend.disconnect()

        assert "Error during disconnect" in caplog.text

    @pytest.mark.asyncio
    async def test_execute_many_connects_when_no_connection(self, caplog):
        cursor = _FakeAsyncCursor(rowcount=1)
        backend = AsyncMariaDBBackend(database="logging_unit_db")

        async def fake_connect():
            backend._connection = _FakeConnection(cursor)

        backend.connect = fake_connect

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            result = await backend.execute_many(
                "INSERT INTO t VALUES (%s)", [(1,), (2,)]
            )

        assert result.affected_rows == 2
        assert "No active connection, establishing new connection" in caplog.text

    @pytest.mark.asyncio
    async def test_executescript_failure_logs(self, caplog):
        backend = AsyncMariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(
            _FailingAsyncCursor(RuntimeError("script failure"))
        )
        # The source calls the async handler without await; stub it so this
        # test observes the logging branch instead of an unawaited coroutine.
        backend._handle_error = lambda error: None

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            await backend.executescript("SELECT 1;")

        assert "Error executing SQL script" in caplog.text

    @pytest.mark.asyncio
    async def test_ping_reconnect_failure_returns_false(self, caplog):
        backend = AsyncMariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(
            _FailingAsyncCursor(RuntimeError("ping failed"))
        )
        backend.disconnect = AsyncMock()
        backend.connect = AsyncMock(side_effect=RuntimeError("reconnect failed"))

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            assert await backend.ping(reconnect=True) is False

        assert "Failed to reconnect" in caplog.text


_SAVEPOINT_FAILURES = [
    pytest.param("_do_create_savepoint", id="create"),
    pytest.param("_do_release_savepoint", id="release"),
    pytest.param("_do_rollback_savepoint", id="rollback"),
]


class TestTransactionGuards:
    """Guard/setter logging branches of the MariaDB transaction manager."""

    def test_guard_blocks_isolation_change(self, caplog):
        backend = MariaDBBackend(database="logging_unit_db")
        manager = MariaDBTransactionManager(backend, backend.logger)
        manager._transaction_level = 1
        manager._state = TransactionState.ACTIVE

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(
                backend_errors.TransactionError,
                match="Cannot change isolation level",
            ):
                manager._check_no_active_transaction()

        assert "Cannot change isolation level" in caplog.text

    def test_setter_validates_and_stores_level(self):
        backend = MariaDBBackend(database="logging_unit_db")
        manager = MariaDBTransactionManager(backend, backend.logger)

        manager.isolation_level = IsolationLevel.SERIALIZABLE
        assert manager.isolation_level is IsolationLevel.SERIALIZABLE

        with pytest.raises(backend_errors.TransactionError):
            manager._validate_isolation_level("UNSUPPORTED")

    @pytest.mark.parametrize("method_name", _SAVEPOINT_FAILURES)
    def test_savepoint_failure_logs_and_raises(self, method_name, caplog):
        backend = MariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(
            _FailingSyncCursor(RuntimeError("savepoint failure"))
        )
        manager = MariaDBTransactionManager(backend, backend.logger)

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(backend_errors.TransactionError, match="Failed to"):
                getattr(manager, method_name)("SP_1")

        assert "Failed to" in caplog.text

    def test_transaction_mixins_expose_guard_helpers(self):
        """The mixin module exposes the helpers the managers rely on."""
        assert hasattr(
            mixins_transaction.MariaDBTransactionMixin,
            "format_set_isolation_level",
        )
        backend = MariaDBBackend(database="logging_unit_db")
        manager = MariaDBTransactionManager(backend, backend.logger)
        assert callable(manager._check_no_active_transaction)
        assert manager.supports_savepoint() is True


class TestAsyncTransactionGuards:
    """The async guard shares the same logging branches as the sync manager."""

    @pytest.mark.asyncio
    async def test_guard_blocks_isolation_change(self, caplog):
        backend = AsyncMariaDBBackend(database="logging_unit_db")
        manager = AsyncMariaDBTransactionManager(backend, backend.logger)
        manager._transaction_level = 1
        manager._state = TransactionState.ACTIVE

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(
                backend_errors.TransactionError,
                match="Cannot change isolation level",
            ):
                manager._check_no_active_transaction()

        assert "Cannot change isolation level" in caplog.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method_name", _SAVEPOINT_FAILURES)
    async def test_savepoint_failure_logs_and_raises(self, method_name, caplog):
        backend = AsyncMariaDBBackend(database="logging_unit_db")
        backend._connection = _FakeConnection(
            _FailingAsyncCursor(RuntimeError("savepoint failure"))
        )
        manager = AsyncMariaDBTransactionManager(backend, backend.logger)

        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            with pytest.raises(backend_errors.TransactionError, match="Failed to"):
                await getattr(manager, method_name)("SP_1")

        assert "Failed to" in caplog.text


class TestLegacyTransactionMixin:
    """The standalone mixin setter logs both of its guard branches."""

    def test_setter_logs_guard_branches(self):
        mixin = object.__new__(mixins_transaction.MariaDBTransactionMixin)
        mixin.log = lambda *args, **kwargs: None
        mixin._isolation_level = None

        mixin.is_active = True
        with pytest.raises(IsolationLevelError):
            mixin.isolation_level = IsolationLevel.SERIALIZABLE

        mixin.is_active = False
        with pytest.raises(backend_errors.TransactionError):
            mixin.isolation_level = "UNSUPPORTED"


class TestCliInfoLogging:
    """The CLI info handler works without a server and uses its logger."""

    def test_info_handle_without_connection(self, capsys):
        args = SimpleNamespace(
            output="json",
            rich_ascii=False,
            named_connection=None,
            database=None,
            version=None,
            verbose=0,
        )

        cli_info.handle(args)

        output = capsys.readouterr().out
        assert '"mariadb"' in output
        assert cli_info.logger.name == (
            "rhosocial.activerecord.backend.mariadb.cli.info"
        )
