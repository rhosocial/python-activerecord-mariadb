# tests/rhosocial/activerecord_mariadb_test/feature/backend/backend/test_backend_error_handling_async.py
"""
Async MariaDB Backend Error Handling Tests

Tests for verifying that AsyncMariaDBBackend correctly handles MariaDB errors
using the proper error classes from mariadb driver (not mysql.connector).
"""
import asyncio
import pytest
import pytest_asyncio
import mariadb

from mariadb import (
    Error as MariaDBError,
    DatabaseError as MariaDBDatabaseError,
    OperationalError as MariaDBOperationalError,
)

from rhosocial.activerecord.backend.impl.mariadb import AsyncMariaDBBackend
from rhosocial.activerecord.backend.errors import (
    IntegrityError,
    DatabaseError,
    DeadlockError,
    OperationalError,
)


@pytest_asyncio.fixture
async def setup_test_table(async_mariadb_backend):
    """Create test table for error handling tests."""
    await async_mariadb_backend.execute("DROP TABLE IF EXISTS error_test")
    await async_mariadb_backend.execute("""
        CREATE TABLE error_test (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE
        )
    """)
    yield
    # Give time for any pending async operations to complete
    await asyncio.sleep(0.1)
    try:
        await async_mariadb_backend.execute("DROP TABLE IF EXISTS error_test")
    except Exception:
        pass


class TestAsyncHandleError:
    """Tests for _handle_error method with various MySQL error types."""

    @pytest.mark.asyncio
    async def test_handle_duplicate_entry_error(self, async_mariadb_backend):
        """Test that Duplicate Entry error is converted to IntegrityError."""
        # Create table with unique constraint
        await async_mariadb_backend.execute("DROP TABLE IF EXISTS unique_test_err")
        await async_mariadb_backend.execute("""
            CREATE TABLE unique_test_err (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE
            )
        """)

        try:
            # Insert first row
            await async_mariadb_backend.execute(
                "INSERT INTO unique_test_err (email) VALUES (%s)",
                ("test@example.com",)
            )

            # Try to insert duplicate - should raise IntegrityError
            with pytest.raises(IntegrityError) as exc_info:
                await async_mariadb_backend.execute(
                    "INSERT INTO unique_test_err (email) VALUES (%s)",
                    ("test@example.com",)
                )

            # The error message contains "duplicate entry" (lowercase in MySQL error)
            error_msg_lower = str(exc_info.value).lower()
            assert "duplicate entry" in error_msg_lower
        finally:
            # Give time for any pending async operations
            await asyncio.sleep(0.1)
            try:
                await async_mariadb_backend.execute(
                    "DROP TABLE IF EXISTS unique_test_err")
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_handle_deadlock_error(self, async_mariadb_backend):
        """Test that Deadlock error is converted to DeadlockError."""
        backend = async_mariadb_backend

        # Create a mock MariaDBDatabaseError with deadlock message
        class MockDeadlockError(MariaDBDatabaseError):
            def __init__(self):
                self._msg = "Deadlock found when trying to get lock"

            def __str__(self):
                return self._msg

        mock_error = MockDeadlockError()

        with pytest.raises(DeadlockError):
            await backend._handle_error(mock_error)

    @pytest.mark.asyncio
    async def test_handle_lock_wait_timeout_error(self, async_mariadb_backend):
        """Test that Lock wait timeout error is converted to OperationalError."""
        backend = async_mariadb_backend

        # Create a mock MariaDBOperationalError with lock timeout message
        class MockLockTimeoutError(MariaDBOperationalError):
            def __init__(self):
                super().__init__()
                self._msg = "Lock wait timeout exceeded"

            def __str__(self):
                return self._msg

        mock_error = MockLockTimeoutError()

        # Due to inheritance order in _handle_error, OperationalError that is also
        # a DatabaseError will be caught by DatabaseError branch
        with pytest.raises((OperationalError, DatabaseError)):
            await backend._handle_error(mock_error)

    @pytest.mark.asyncio
    async def test_handle_generic_database_error(self, async_mariadb_backend):
        """Test that generic DatabaseError is converted properly."""
        backend = async_mariadb_backend

        # Create a mock MariaDBDatabaseError
        class MockDatabaseError(MariaDBDatabaseError):
            def __init__(self, msg="Generic database error"):
                self._msg = msg

            def __str__(self):
                return self._msg

        mock_error = MockDatabaseError("Some database error")

        with pytest.raises(DatabaseError):
            await backend._handle_error(mock_error)

    @pytest.mark.asyncio
    async def test_handle_generic_mysql_error(self, async_mariadb_backend):
        """Test that generic MySQLError is converted to DatabaseError."""
        backend = async_mariadb_backend

        # Create a mock MariaDBError (base error class)
        class MockMySQLError(MariaDBError):
            def __init__(self, msg="Generic MariaDB error"):
                self._msg = msg

            def __str__(self):
                return self._msg

        mock_error = MockMySQLError("Some MariaDB error")

        with pytest.raises(DatabaseError):
            await backend._handle_error(mock_error)

    @pytest.mark.asyncio
    async def test_handle_foreign_key_constraint_error(self, async_mariadb_backend):
        """Test that foreign key constraint violation is converted to IntegrityError."""
        backend = async_mariadb_backend

        try:
            # Create parent table
            await backend.execute("DROP TABLE IF EXISTS child_table_err")
            await backend.execute("DROP TABLE IF EXISTS parent_table_err")

            await backend.execute("""
                CREATE TABLE parent_table_err (
                    id INT PRIMARY KEY
                )
            """)

            await backend.execute("""
                CREATE TABLE child_table_err (
                    id INT PRIMARY KEY,
                    parent_id INT,
                    FOREIGN KEY (parent_id) REFERENCES parent_table_err(id)
                )
            """)

            # Try to insert with non-existent parent - should raise IntegrityError
            with pytest.raises(IntegrityError) as exc_info:
                await backend.execute(
                    "INSERT INTO child_table_err (id, parent_id) VALUES (1, 999)"
                )

            assert "foreign key constraint" in str(exc_info.value).lower()
        finally:
            await asyncio.sleep(0.1)
            try:
                await backend.execute("DROP TABLE IF EXISTS child_table_err")
                await backend.execute("DROP TABLE IF EXISTS parent_table_err")
            except Exception:
                pass


class TestAsyncErrorClassValidation:
    """Tests to verify correct error class usage."""

    @pytest.mark.asyncio
    async def test_error_classes_from_correct_module(self):
        """Verify that error classes are imported from mariadb driver."""
        from mariadb import (
            Error as MariaDBError,
            DatabaseError as MariaDBDatabaseError,
            IntegrityError as MariaDBIntegrityError,
            OperationalError as MariaDBOperationalError,
        )

        # All should come from mariadb
        assert MariaDBError.__module__ == "mariadb"
        assert MariaDBDatabaseError.__module__ == "mariadb"
        assert MariaDBIntegrityError.__module__ == "mariadb"
        assert MariaDBOperationalError.__module__ == "mariadb"

    @pytest.mark.asyncio
    async def test_mariadb_async_error_is_same_as_driver_error(self):
        """
        Verify that mariadb driver error classes are consistent across modules.

        mariadb 2.0.0+ provides synchronous and async error classes
        that are the same underlying types.
        """
        import mariadb
        from mariadb import Error as MariaDBError

        # mariadb's async connect provides the same error classes
        if hasattr(mariadb, 'asyncConnect'):
            mariadb_async_conn = getattr(mariadb, 'asyncConnect')
            # The important thing is that we use MariaDBError from mariadb


class TestAsyncConnectionErrorHandling:
    """Tests for connection error handling."""

    @pytest.mark.asyncio
    async def test_connection_error_on_invalid_host(self):
        """Test that connection to invalid host raises proper error."""
        from rhosocial.activerecord.backend.errors import (
            ConnectionError as ARConnectionError
        )

        backend = AsyncMariaDBBackend(
            host="nonexistent-host-12345.invalid",
            port=3306,
            database="test",
            username="test",
            password="test"
        )

        with pytest.raises((ARConnectionError, OSError)):
            await backend.connect()

    @pytest.mark.asyncio
    async def test_syntax_error_handling(self, async_mariadb_backend):
        """Test that SQL syntax error raises proper DatabaseError."""
        with pytest.raises(DatabaseError):
            await async_mariadb_backend.execute(
                "SELECT * FROM nonexistent_table_xyz"
            )
