# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/errors/test_driver_error_mapping.py
"""MariaDB driver exceptions map to the framework's semantic error taxonomy.

These tests never open a connection: they build a backend without connecting
and hand synthetic driver exceptions to ``_handle_error`` directly. The sync
and async backends share the mapper, so the async cases only assert that
delegation still raises the same categories.
"""

import pytest

driver = pytest.importorskip("mariadb")

from rhosocial.activerecord.backend.errors import (  # noqa: E402
    ConnectionError,
    DataError,
    DatabaseError,
    DeadlockError,
    IntegrityError,
    LockError,
    OperationalError,
    QueryError,
)
from rhosocial.activerecord.backend.impl.mariadb.backend.async_backend import (  # noqa: E402
    AsyncMariaDBBackend,
)
from rhosocial.activerecord.backend.impl.mariadb.backend.backend import (  # noqa: E402
    MariaDBBackend,
)


@pytest.fixture
def backend():
    """A backend that is never connected."""
    return MariaDBBackend(database="error_mapping_db")


@pytest.fixture
def async_backend():
    """An async backend that is never connected."""
    return AsyncMariaDBBackend(database="error_mapping_db")


def _translated(backend, error):
    with pytest.raises(DatabaseError) as info:
        backend._handle_error(error)
    return info.value


class TestDriverErrorMapping:
    """Sync mapping: duplicate, FK, deadlock, lock, lost, programming, read-only."""

    def test_duplicate_key_maps_to_integrity(self, backend):
        error = driver.IntegrityError("Duplicate entry 'a' for key 'uniq'", 1062)
        translated = _translated(backend, error)
        assert isinstance(translated, IntegrityError)
        assert isinstance(translated, DataError)
        assert translated.operation == "execute"
        assert translated.driver_code == 1062
        assert translated.backend == "mariadb"
        assert translated.retryable is False

    def test_duplicate_entry_message_without_code_maps_to_integrity(self, backend):
        error = driver.IntegrityError("Duplicate entry 'a' for key 'uniq'")
        translated = _translated(backend, error)
        assert isinstance(translated, IntegrityError)
        assert translated.driver_code is None

    def test_foreign_key_maps_to_integrity(self, backend):
        error = driver.IntegrityError(
            "Cannot add or update a child row: a foreign key constraint fails", 1452
        )
        translated = _translated(backend, error)
        assert isinstance(translated, IntegrityError)
        assert translated.driver_code == 1452
        assert "Foreign key constraint" in str(translated)

    def test_foreign_key_delete_restrict_maps_to_integrity(self, backend):
        error = driver.IntegrityError(
            "Cannot delete or update a parent row: a foreign key constraint fails", 1451
        )
        translated = _translated(backend, error)
        assert isinstance(translated, IntegrityError)
        assert translated.driver_code == 1451

    def test_not_null_maps_to_integrity(self, backend):
        error = driver.IntegrityError("Column 'name' cannot be null", 1048)
        translated = _translated(backend, error)
        assert isinstance(translated, IntegrityError)
        assert translated.driver_code == 1048

    def test_check_constraint_maps_to_integrity(self, backend):
        error = driver.IntegrityError(
            "Check constraint 'chk_positive' is violated", 4025
        )
        translated = _translated(backend, error)
        assert isinstance(translated, IntegrityError)
        assert translated.driver_code == 4025

    def test_deadlock_maps_to_deadlock_error(self, backend):
        error = driver.OperationalError(
            "Deadlock found when trying to get lock; try restarting transaction", 1213
        )
        translated = _translated(backend, error)
        assert isinstance(translated, DeadlockError)
        assert isinstance(translated, LockError)
        assert translated.retryable is True
        assert translated.transient is True

    def test_lock_wait_timeout_maps_to_lock_error(self, backend):
        error = driver.OperationalError(
            "Lock wait timeout exceeded; try restarting transaction", 1205
        )
        translated = _translated(backend, error)
        assert isinstance(translated, LockError)
        assert not isinstance(translated, DeadlockError)
        assert translated.retryable is True
        assert translated.transient is True

    @pytest.mark.parametrize("code", [2006, 2013, 2055])
    def test_lost_connection_is_transient(self, backend, code):
        error = driver.OperationalError("Lost connection to server during query", code)
        translated = _translated(backend, error)
        assert isinstance(translated, OperationalError)
        assert translated.driver_code == code
        assert translated.transient is True
        assert translated.retryable is True

    def test_connect_failure_is_not_transient(self, backend):
        error = driver.OperationalError("Can't connect to server", 2003)
        translated = _translated(backend, error)
        assert isinstance(translated, ConnectionError)
        assert translated.driver_code == 2003
        assert translated.transient is False
        assert translated.retryable is False

    def test_read_only_server_is_not_retryable(self, backend):
        error = driver.OperationalError(
            "The MariaDB server is running with the --read-only option so it "
            "cannot execute this statement",
            1290,
        )
        translated = _translated(backend, error)
        assert isinstance(translated, OperationalError)
        assert translated.driver_code == 1290
        assert translated.sqlstate == "HY000"
        assert translated.transient is False
        assert translated.retryable is False

    def test_syntax_error_maps_to_query_error(self, backend):
        error = driver.ProgrammingError(
            "You have an error in your SQL syntax; check the manual", 1064
        )
        translated = _translated(backend, error)
        assert isinstance(translated, QueryError)
        assert translated.driver_code == 1064

    def test_unknown_table_maps_to_query_error(self, backend):
        error = driver.ProgrammingError("Table 'db.missing' doesn't exist", 1146)
        translated = _translated(backend, error)
        assert isinstance(translated, QueryError)
        assert translated.driver_code == 1146

    def test_unknown_database_error_falls_back(self, backend):
        error = driver.DatabaseError("Unknown database 'nope'", 1049)
        translated = _translated(backend, error)
        assert isinstance(translated, DatabaseError)
        assert not isinstance(
            translated, (IntegrityError, QueryError, LockError, OperationalError)
        )
        assert translated.driver_code == 1049
        assert translated.backend == "mariadb"

    def test_generic_driver_error_falls_back(self, backend):
        error = driver.Error("Generic MariaDB error")
        translated = _translated(backend, error)
        assert isinstance(translated, DatabaseError)
        assert translated.driver_code is None

    def test_message_only_deadlock_still_maps(self, backend):
        error = driver.OperationalError("Deadlock found when trying to get lock")
        translated = _translated(backend, error)
        assert isinstance(translated, DeadlockError)

    def test_message_only_lock_timeout_still_maps(self, backend):
        error = driver.OperationalError("Lock wait timeout exceeded")
        translated = _translated(backend, error)
        assert isinstance(translated, LockError)

    def test_non_driver_error_is_reraised_unchanged(self, backend):
        original = RuntimeError("not a driver error")
        with pytest.raises(RuntimeError) as info:
            backend._handle_error(original)
        assert info.value is original


class TestAsyncDriverErrorMapping:
    """Async mapping goes through the same shared mapper."""

    @pytest.mark.asyncio
    async def test_duplicate_key_maps_to_integrity(self, async_backend):
        error = driver.IntegrityError("Duplicate entry 'a' for key 'uniq'", 1062)
        with pytest.raises(IntegrityError) as info:
            await async_backend._handle_error(error)
        assert info.value.driver_code == 1062
        assert info.value.backend == "mariadb"

    @pytest.mark.asyncio
    async def test_deadlock_maps_to_deadlock_error(self, async_backend):
        error = driver.OperationalError("Deadlock found when trying to get lock", 1213)
        with pytest.raises(DeadlockError) as info:
            await async_backend._handle_error(error)
        assert info.value.retryable is True
        assert info.value.transient is True

    @pytest.mark.asyncio
    async def test_lost_connection_is_transient(self, async_backend):
        error = driver.OperationalError("Lost connection to server", 2013)
        with pytest.raises(OperationalError) as info:
            await async_backend._handle_error(error)
        assert info.value.transient is True

    @pytest.mark.asyncio
    async def test_syntax_error_maps_to_query_error(self, async_backend):
        error = driver.ProgrammingError("You have an error in your SQL syntax", 1064)
        with pytest.raises(QueryError) as info:
            await async_backend._handle_error(error)
        assert info.value.driver_code == 1064
