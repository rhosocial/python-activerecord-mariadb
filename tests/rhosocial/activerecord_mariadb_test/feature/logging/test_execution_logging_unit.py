# tests/rhosocial/activerecord_mariadb_test/feature/logging/test_execution_logging_unit.py
"""Database-free tests for the MariaDB execution-logging change set.

These tests never open a MariaDB connection.  They import every module the
logging-audit branch touched, build the sync and async backends without
connecting, drive ``execute_many`` through fake cursors, and exercise the
driver-error mapping and transaction guards directly.

Sync and async cases use the same method names under ``Test*`` and
``TestAsync*`` classes, following the repository's parity convention.
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

mariadb = pytest.importorskip("mariadb")

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


class _FakeConnection:
    """Connection stand-in exposing only ``cursor()``."""

    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


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


_DRIVER_ERROR_CASES = [
    pytest.param(
        lambda: mariadb.OperationalError("Lost connection to server", 2013),
        backend_errors.ConnectionError,
        id="connection-error-code",
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
    """The async guard shares the same logging branch as the sync manager."""

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
