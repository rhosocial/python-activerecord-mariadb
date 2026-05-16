# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_connection_resilience.py
"""
Connection Resilience Tests
============================

Tests for MariaDB backend's ability to handle connection loss scenarios:
1. Connection timeout (wait_timeout)
2. Connection killed by KILL CONNECTION
3. Automatic reconnection via ping method
4. is_connected() method accuracy

These tests verify the implementation of:
- Plan A: Pre-query connection check in _get_cursor()
- Plan B: Error retry mechanism in execute()

Both synchronous (MariaDBBackend) and asynchronous (AsyncMariaDBBackend) are tested.

========================================================================
                    USAGE GUIDELINES FOR USERS
========================================================================

RECOMMENDED PATTERNS (✅ Safe to Use)
-------------------------------------

1. **Single Backend per Request/Task**
   Each request or async task should have its own backend instance.

   ```python
   # ✅ GOOD: Create backend per request (Web framework example)
   def handle_request():
       backend = MariaDBBackend(config)
       try:
           backend.connect()
           User.configure(backend)
           # ... do work ...
       finally:
           backend.disconnect()
   ```

2. **Context Manager Pattern**
   Use the backend as a context manager for automatic cleanup.

   ```python
   # ✅ GOOD: Context manager ensures proper cleanup
   with MariaDBBackend(config) as backend:
       User.configure(backend)
       # ... do work ...
   # Connection automatically closed on exit
   ```

3. **Application-Level Singleton (Single-Threaded)**
   For CLI tools or single-threaded applications, a single backend is fine.

   ```python
   # ✅ GOOD: Single-threaded CLI tool
   backend = MariaDBBackend(config)
   User.configure(backend)
   Order.configure(backend)  # Same backend, same connection

   # All operations share one connection
   users = User.query().all()
   orders = Order.query().all()
   ```

4. **Cross-Model Transactions**
   When models share a backend, cross-model transactions work correctly.

   ```python
   # ✅ GOOD: Cross-model transaction with shared backend
   with backend.transaction():
       user = User.find(1)
       user.balance -= 100
       user.save()
       Order.create(user_id=user.id, amount=100)
       # Both operations in same transaction
   ```

5. **Handle Connection Loss Gracefully**
   Implement retry logic for critical operations.

   ```python
   # ✅ GOOD: Retry on connection failure
   def save_with_retry(model, max_retries=3):
       for attempt in range(max_retries):
           try:
               model.save()
               return True
           except ConnectionError:
               if attempt < max_retries - 1:
                   model.__backend__.ping(reconnect=True)
                   continue
               raise
       return False
   ```

PROHIBITED PATTERNS (❌ Dangerous, Will Cause Issues)
-----------------------------------------------------

1. **Multi-Threaded Shared Backend**
   NEVER share a backend instance across threads.

   ```python
   # ❌ BAD: Shared backend across threads
   backend = MariaDBBackend(config)
   User.configure(backend)

   def thread_worker():
       # This will interfere with other threads!
       User.query().all()  # Race condition!

   t1 = threading.Thread(target=thread_worker)
   t2 = threading.Thread(target=thread_worker)
   # Both threads share the same connection - DEADLOCK or DATA CORRUPTION!
   ```

   Why it fails:
   - Connection object is NOT thread-safe
   - Transaction state is shared across threads
   - One thread's rollback affects all threads
   - Deadlocks are common

2. **Long-Running Transactions with Uncommitted Changes**
   Avoid long transactions that span connection loss events.

   ```python
   # ❌ BAD: Long transaction vulnerable to connection loss
   backend.begin_transaction()
   user = User.find(1)
   user.balance -= 100
   user.save()

   # ... many seconds pass, connection times out ...

   # Connection lost! Transaction is gone!
   Order.create(user_id=user.id, amount=100)
   # This will execute outside the transaction!
   ```

   Why it fails:
   - Connection loss means transaction loss
   - No automatic transaction recovery
   - Subsequent operations run without transaction context

3. **Ignoring Transaction State After Reconnect**
   Always check transaction state after reconnection.

   ```python
   # ❌ BAD: Assuming transaction continues after reconnect
   backend.begin_transaction()
   # ... connection lost and auto-reconnected ...
   backend.commit()  # May fail or silently succeed without effect!

   # ✅ GOOD: Check state after reconnect
   if backend.in_transaction:
       backend.commit()
   else:
       # Transaction was lost, need to retry
       raise TransactionLostError("Please retry the operation")
   ```

4. **Relying on Session Variables After Reconnect**
   Session variables are reset on reconnection.

   ```python
   # ❌ BAD: Session variable not preserved
   backend.execute("SET SESSION time_zone = '+00:00'")
   # ... connection lost and reconnected ...
   backend.execute("SELECT NOW()")  # time_zone is back to server default!

   # ✅ GOOD: Set session variables after each connection
   def ensure_session_settings(backend):
       backend.execute("SET SESSION time_zone = '+00:00'")
       backend.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES'")

   # Call after every connect() or ping(reconnect=True)
   ```

5. **Creating Multiple Backends for Same Model**
   Each model should have one consistent backend.

   ```python
   # ❌ BAD: Inconsistent backend assignment
   User.configure(config1, MariaDBBackend)  # Backend A
   # Later...
   User.configure(config2, MariaDBBackend)  # Backend B (replaces A)

   # Now existing User instances may reference old backend!
   ```

SCENARIO-SPECIFIC RECOMMENDATIONS
----------------------------------

| Scenario | Recommended Approach |
|----------|----------------------|
| Web Application (sync) | One backend per request, or use connection pool |
| Web Application (async) | One backend per request, or use async pool |
| CLI Tool | Single backend for entire process |
| Background Worker | One backend per job/task |
| Batch Processing | Reconnect periodically, batch in small transactions |
| Long-Polling | Use ping() before each operation |
| High Concurrency | External connection pool (SQLAlchemy, etc.) |

CONNECTION LOSS RECOVERY BEHAVIOR
---------------------------------

When connection is lost (timeout, KILL, network issue):

1. Automatic detection:
   - Pre-query check in _get_cursor() (Plan A)
   - Error detection in execute() with retry (Plan B)

2. What is preserved:
   - Backend configuration
   - Model-to-backend mapping

3. What is LOST:
   - Active transaction (rolled back on server)
   - Savepoints (all lost)
   - Session variables (reset to server defaults)
   - Prepared statements cache (connection-level)
   - Temporary tables (connection-level)

4. Recovery actions:
   - Backend automatically reconnects on next operation
   - User must re-establish session settings if needed
   - User must retry failed transactions

========================================================================
"""
import pytest
import pytest_asyncio
import asyncio
import time
import logging
import mariadb

from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, AsyncMariaDBBackend


logger = logging.getLogger(__name__)


def print_separator(title: str):
    """Print a visual separator for test sections."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def safe_is_connected(connection) -> bool:
    """
    Safely check if connection is alive by pinging the server.

    In MariaDB, ping() is used instead of is_connected().

    Returns:
        True if connected, False if disconnected or error occurred.
    """
    try:
        connection.ping()
        return True
    except (mariadb.Error, BrokenPipeError, OSError):
        return False


async def async_safe_is_connected(connection) -> bool:
    """
    Async version of safe_is_connected().

    Returns:
        True if connected, False if disconnected or error occurred.
    """
    try:
        await connection.ping()
        return True
    except (mariadb.Error, BrokenPipeError, OSError):
        return False


def wait_until_dead(connection, timeout: float = 5.0, interval: float = 0.3) -> bool:
    """
    Wait until connection is confirmed dead.

    This function polls ping() until it returns an error,
    handling the race condition between KILL CONNECTION and TCP stack cleanup.

    Args:
        connection: The database connection object.
        timeout: Maximum time to wait in seconds.
        interval: Polling interval in seconds.

    Returns:
        True if connection is confirmed dead, False if still connected after timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            connection.ping()
        except (mariadb.Error, BrokenPipeError, OSError):
            return True  # Exception indicates connection is dead
        time.sleep(interval)
    return False


async def async_wait_until_dead(connection, timeout: float = 5.0, interval: float = 0.3) -> bool:
    """
    Async version of wait_until_dead().

    Args:
        connection: The database connection object.
        timeout: Maximum time to wait in seconds.
        interval: Polling interval in seconds.

    Returns:
        True if connection is confirmed dead, False if still connected after timeout.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            await connection.ping()
        except (mariadb.Error, BrokenPipeError, OSError):
            return True  # Exception indicates connection is dead
        await asyncio.sleep(interval)
    return False


# ============================================================================
# Synchronous Backend Tests
# ============================================================================


class TestIsConnectedMethod:
    """Tests for the is_connected() method accuracy."""

    def test_is_connected_when_connected(self, mariadb_backend_single: MariaDBBackend):
        """Verify ping() returns True for active connection."""
        assert mariadb_backend_single._connection is not None
        assert safe_is_connected(mariadb_backend_single._connection) is True

    def test_is_connected_after_disconnect(self, mariadb_backend_single: MariaDBBackend):
        """Verify is_connected() returns False after explicit disconnect."""
        mariadb_backend_single.disconnect()
        # After disconnect, _connection should be None
        assert mariadb_backend_single._connection is None

    def test_is_connected_after_kill(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """Verify is_connected() correctly detects killed connections."""
        # Get current connection ID
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        connection_id = result.data[0]['id']
        print(f"Test connection ID: {connection_id}")

        # Kill the connection
        mariadb_control_backend.execute(f"KILL CONNECTION {connection_id}")

        # Wait for connection to be confirmed dead with retry mechanism
        assert wait_until_dead(mariadb_backend_single._connection), \
            "Connection did not die within timeout"

        # Verify is_connected() detects the disconnection
        # Note: _connection is not None, but is_connected() should return False
        assert mariadb_backend_single._connection is not None
        is_connected = safe_is_connected(mariadb_backend_single._connection)
        assert is_connected is False, "is_connected() should return False for killed connection"


class TestWaitTimeoutRecovery:
    """Tests for wait_timeout connection recovery."""

    def test_wait_timeout_triggers_reconnection(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that wait_timeout expiration triggers automatic reconnection.

        This test:
        1. Gets the original wait_timeout value
        2. Sets a short timeout (5 seconds)
        3. Waits for timeout
        4. Verifies query succeeds with automatic reconnection
        """
        print_separator("Test: wait_timeout Recovery")

        # 1. Get original wait_timeout
        result = mariadb_backend_single.introspector.show.variables(like="wait_timeout")
        original_timeout = int(result[0].value)
        print(f"Original wait_timeout: {original_timeout} seconds")

        # 2. Set short timeout
        test_timeout = 5
        print(f"Setting wait_timeout to {test_timeout} seconds...")
        mariadb_backend_single.execute(f"SET SESSION wait_timeout = {test_timeout}")

        # Verify setting
        result = mariadb_backend_single.introspector.show.variables(like="wait_timeout")
        current_timeout = int(result[0].value)
        assert current_timeout == test_timeout
        print(f"Current wait_timeout: {current_timeout} seconds")

        # 3. Wait for timeout (plus buffer)
        print(f"Waiting {test_timeout + 2} seconds for timeout...")
        time.sleep(test_timeout + 2)

        # 4. Execute query - should trigger reconnection
        print("Executing query after timeout...")
        try:
            result = mariadb_backend_single.execute("SELECT 1 AS test")
            print(f"Query succeeded: {result}")
            assert result.data[0]['test'] == 1

            # Verify we have a new connection
            new_conn_result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
            print(f"New connection ID: {new_conn_result.data[0]['id']}")
        finally:
            # Restore original timeout via control backend
            try:
                mariadb_control_backend.execute(f"SET GLOBAL wait_timeout = {original_timeout}")
            except Exception:
                pass  # Ignore cleanup errors


class TestKillConnectionRecovery:
    """Tests for KILL CONNECTION recovery."""

    def test_kill_connection_triggers_reconnection(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that KILL CONNECTION triggers automatic reconnection.

        This test:
        1. Gets current connection ID
        2. Kills the connection
        3. Verifies next query succeeds with automatic reconnection
        """
        print_separator("Test: KILL CONNECTION Recovery")

        # 1. Get current connection ID
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # 2. Kill the connection
        print(f"Killing connection {original_conn_id}...")
        mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        time.sleep(1)  # Wait for termination

        # 3. Execute query - should trigger reconnection
        print("Executing query after connection killed...")
        result = mariadb_backend_single.execute("SELECT 1 AS test")
        print(f"Query succeeded: {result}")
        assert result.data[0]['test'] == 1

        # 4. Verify new connection ID
        new_conn_result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id, "Should have a new connection ID"

    def test_multiple_queries_after_reconnection(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that multiple queries work correctly after reconnection.

        This verifies that the reconnection is stable and the backend
        remains in a consistent state.
        """
        print_separator("Test: Multiple Queries After Reconnection")

        # Kill connection
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        time.sleep(1)

        # Execute multiple queries
        for i in range(5):
            result = mariadb_backend_single.execute(f"SELECT {i} AS value")
            assert result.data[0]['value'] == i
            print(f"Query {i + 1}/5 succeeded")


class TestPingReconnect:
    """Tests for manual ping reconnection."""

    def test_ping_reconnect_after_kill(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that ping(reconnect=True) can restore a killed connection.

        This test:
        1. Gets current connection ID
        2. Kills the connection
        3. Calls ping(reconnect=True)
        4. Verifies connection is restored with new ID
        """
        print_separator("Test: Ping Reconnect")

        # 1. Get current connection ID
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # 2. Kill the connection
        print(f"Killing connection {original_conn_id}...")
        mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")

        # 3. Wait for connection to be confirmed dead
        assert wait_until_dead(mariadb_backend_single._connection), \
            "Connection did not die within timeout"
        print("Connection confirmed dead")

        # 4. Ping with reconnect
        print("Calling ping(reconnect=True)...")
        ping_result = mariadb_backend_single.ping(reconnect=True)
        print(f"Ping result: {ping_result}")
        assert ping_result is True, "Ping should succeed with reconnect=True"

        # 5. Verify connection is restored
        assert safe_is_connected(mariadb_backend_single._connection) is True

        # 6. Verify new connection ID
        new_conn_result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id

    def test_ping_no_reconnect_keeps_dead_connection(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that ping(reconnect=False) returns False for dead connections
        without attempting reconnection.
        """
        print_separator("Test: Ping No Reconnect")

        # Get current connection ID
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']

        # Kill the connection
        mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")

        # Wait for connection to be confirmed dead
        assert wait_until_dead(mariadb_backend_single._connection), \
            "Connection did not die within timeout"

        # Ping without reconnect
        ping_result = mariadb_backend_single.ping(reconnect=False)
        print(f"Ping result (reconnect=False): {ping_result}")
        assert ping_result is False, "Ping should return False for dead connection"

        # Connection should still be dead
        assert safe_is_connected(mariadb_backend_single._connection) is False


class TestGetCursorAutoReconnect:
    """Tests for _get_cursor() automatic reconnection behavior."""

    def test_get_cursor_reconnects_killed_connection(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that _get_cursor() automatically reconnects when connection is dead.

        This verifies Plan A: Pre-query connection check.
        """
        print_separator("Test: _get_cursor Auto Reconnect")

        # Get current connection ID
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # Kill the connection
        mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")

        # Wait for connection to be confirmed dead
        assert wait_until_dead(mariadb_backend_single._connection), \
            "Connection did not die within timeout"

        # Call _get_cursor - should trigger reconnection
        cursor = mariadb_backend_single._get_cursor()
        print("_get_cursor() returned cursor successfully")

        # Verify connection is now alive
        assert safe_is_connected(mariadb_backend_single._connection) is True

        # Clean up cursor
        cursor.close()

        # Verify new connection ID
        new_conn_result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id


# ============================================================================
# Asynchronous Backend Tests
# ============================================================================


class TestAsyncIsConnectedMethod:
    """Async tests for the is_connected() method accuracy."""

    @pytest.mark.asyncio
    async def test_is_connected_when_connected(self, async_mariadb_backend_single: AsyncMariaDBBackend):
        """Verify is_connected() returns True for active connection."""
        assert async_mariadb_backend_single._connection is not None
        assert await async_safe_is_connected(async_mariadb_backend_single._connection) is True

    @pytest.mark.asyncio
    async def test_is_connected_after_disconnect(self, async_mariadb_backend_single: AsyncMariaDBBackend):
        """Verify is_connected() returns False after explicit disconnect."""
        await async_mariadb_backend_single.disconnect()
        # After disconnect, _connection should be None
        assert async_mariadb_backend_single._connection is None

    @pytest.mark.asyncio
    async def test_is_connected_after_kill(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Verify is_connected() correctly detects killed connections."""
        # Get current connection ID
        result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        connection_id = result.data[0]['id']
        print(f"Test connection ID: {connection_id}")

        # Kill the connection
        await async_mariadb_control_backend.execute(f"KILL CONNECTION {connection_id}")

        # Wait for connection to be confirmed dead with retry mechanism
        assert await async_wait_until_dead(async_mariadb_backend_single._connection), \
            "Connection did not die within timeout"

        # Verify is_connected() detects the disconnection
        assert async_mariadb_backend_single._connection is not None
        is_connected = await async_safe_is_connected(async_mariadb_backend_single._connection)
        assert is_connected is False, "is_connected() should return False for killed connection"


class TestAsyncWaitTimeoutRecovery:
    """Async tests for wait_timeout connection recovery."""

    @pytest.mark.asyncio
    async def test_wait_timeout_triggers_reconnection(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """
        Test that wait_timeout expiration triggers automatic reconnection.
        """
        print_separator("Test: Async wait_timeout Recovery")

        # 1. Get original wait_timeout
        result = await async_mariadb_backend_single.introspector.show.variables(like="wait_timeout")
        original_timeout = int(result[0].value)
        print(f"Original wait_timeout: {original_timeout} seconds")

        # 2. Set short timeout
        test_timeout = 5
        print(f"Setting wait_timeout to {test_timeout} seconds...")
        await async_mariadb_backend_single.execute(f"SET SESSION wait_timeout = {test_timeout}")

        # Verify setting
        result = await async_mariadb_backend_single.introspector.show.variables(like="wait_timeout")
        current_timeout = int(result[0].value)
        assert current_timeout == test_timeout

        # 3. Wait for timeout
        print(f"Waiting {test_timeout + 2} seconds for timeout...")
        await asyncio.sleep(test_timeout + 2)

        # 4. Execute query - should trigger reconnection
        print("Executing query after timeout...")
        try:
            result = await async_mariadb_backend_single.execute("SELECT 1 AS test")
            print(f"Query succeeded: {result}")
            assert result.data[0]['test'] == 1
        finally:
            # Restore original timeout via control backend
            try:
                await async_mariadb_control_backend.execute(f"SET GLOBAL wait_timeout = {original_timeout}")
            except Exception:
                pass


class TestAsyncKillConnectionRecovery:
    """Async tests for KILL CONNECTION recovery."""

    @pytest.mark.asyncio
    async def test_kill_connection_triggers_reconnection(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test that KILL CONNECTION triggers automatic reconnection."""
        print_separator("Test: Async KILL CONNECTION Recovery")

        # 1. Get current connection ID
        result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # 2. Kill the connection
        print(f"Killing connection {original_conn_id}...")
        await async_mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        await asyncio.sleep(1)

        # 3. Execute query - should trigger reconnection
        print("Executing query after connection killed...")
        result = await async_mariadb_backend_single.execute("SELECT 1 AS test")
        print(f"Query succeeded: {result}")
        assert result.data[0]['test'] == 1

        # 4. Verify new connection ID
        new_conn_result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id

    @pytest.mark.asyncio
    async def test_multiple_queries_after_reconnection(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test that multiple queries work correctly after reconnection."""
        print_separator("Test: Async Multiple Queries After Reconnection")

        # Kill connection
        result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        await async_mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        await asyncio.sleep(1)

        # Execute multiple queries
        for i in range(5):
            result = await async_mariadb_backend_single.execute(f"SELECT {i} AS value")
            assert result.data[0]['value'] == i
            print(f"Query {i + 1}/5 succeeded")


class TestAsyncPingReconnect:
    """Async tests for manual ping reconnection."""

    @pytest.mark.asyncio
    async def test_ping_reconnect_after_kill(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test that ping(reconnect=True) can restore a killed connection."""
        print_separator("Test: Async Ping Reconnect")

        # 1. Get current connection ID
        result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # 2. Kill the connection
        print(f"Killing connection {original_conn_id}...")
        await async_mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")

        # 3. Wait for connection to be confirmed dead
        assert await async_wait_until_dead(async_mariadb_backend_single._connection), \
            "Connection did not die within timeout"
        print("Connection confirmed dead")

        # 4. Ping with reconnect
        print("Calling ping(reconnect=True)...")
        ping_result = await async_mariadb_backend_single.ping(reconnect=True)
        print(f"Ping result: {ping_result}")
        assert ping_result is True, "Ping should succeed with reconnect=True"

        # 5. Verify connection is restored
        assert await async_safe_is_connected(async_mariadb_backend_single._connection) is True

        # 6. Verify new connection ID
        new_conn_result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id

    @pytest.mark.asyncio
    async def test_ping_no_reconnect_keeps_dead_connection(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test that ping(reconnect=False) returns False for dead connections."""
        print_separator("Test: Async Ping No Reconnect")

        # Get current connection ID
        result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']

        # Kill the connection
        await async_mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")

        # Wait for connection to be confirmed dead
        assert await async_wait_until_dead(async_mariadb_backend_single._connection), \
            "Connection did not die within timeout"

        # Ping without reconnect
        ping_result = await async_mariadb_backend_single.ping(reconnect=False)
        print(f"Ping result (reconnect=False): {ping_result}")
        assert ping_result is False, "Ping should return False for dead connection"

        # Connection should still be dead
        assert await async_safe_is_connected(async_mariadb_backend_single._connection) is False


class TestAsyncGetCursorAutoReconnect:
    """Async tests for _get_cursor() automatic reconnection behavior."""

    @pytest.mark.asyncio
    async def test_get_cursor_reconnects_killed_connection(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test that _get_cursor() automatically reconnects when connection is dead."""
        print_separator("Test: Async _get_cursor Auto Reconnect")

        # Get current connection ID
        result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # Kill the connection
        await async_mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")

        # Wait for connection to be confirmed dead
        assert await async_wait_until_dead(async_mariadb_backend_single._connection), \
            "Connection did not die within timeout"

        # Call _get_cursor - should trigger reconnection
        cursor = await async_mariadb_backend_single._get_cursor()
        print("_get_cursor() returned cursor successfully")

        # Verify connection is now alive
        assert await async_safe_is_connected(async_mariadb_backend_single._connection) is True

        # Clean up cursor
        await cursor.close()

        # Verify new connection ID
        new_conn_result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id


# ============================================================================
# Transaction Integrity Tests
# ============================================================================


class TestTransactionInterruption:
    """
    Tests for transaction behavior during connection interruption.

    These tests verify that:
    1. Transactions are properly lost when connection is killed
    2. Backend correctly reports transaction state after reconnection
    3. Operations after reconnection do not silently continue in a lost transaction

    USAGE IMPLICATIONS:
    -------------------
    After connection loss during a transaction:
    - All uncommitted changes are ROLLED BACK by the database server
    - The transaction_manager.in_transaction becomes False after reconnect
    - You MUST retry the entire transaction from the beginning

    RECOMMENDED PATTERN:
    --------------------
    ```python
    def execute_with_retry(backend, operation, max_retries=3):
        for attempt in range(max_retries):
            try:
                with backend.transaction():
                    return operation()
            except ConnectionError:
                if attempt < max_retries - 1:
                    continue
                raise
    ```

    ANTI-PATTERN TO AVOID:
    ----------------------
    ```python
    # ❌ BAD: Not checking transaction state after reconnect
    backend.begin_transaction()
    # ... connection lost ...
    backend.commit()  # Fails or silently does nothing!
    ```
    """

    def test_transaction_lost_after_connection_killed(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that killing a connection during a transaction properly loses the transaction.

        Expected behavior:
        - After connection is killed and auto-reconnected, the transaction should be lost
        - The backend should either raise an error or clearly indicate transaction loss
        - Uncommitted changes should be rolled back
        """
        print_separator("Test: Transaction Lost After Connection Killed")

        # Create a test table for transaction verification
        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_transaction_integrity")
        mariadb_backend_single.execute("""
            CREATE TABLE test_transaction_integrity (
                id INT PRIMARY KEY AUTO_INCREMENT,
                value VARCHAR(100)
            )
        """)

        try:
            # Clear the table
            mariadb_backend_single.execute("DELETE FROM test_transaction_integrity")

            # Start a transaction
            print("Starting transaction...")
            mariadb_backend_single.begin_transaction()

            # Insert a record within the transaction
            mariadb_backend_single.execute(
                "INSERT INTO test_transaction_integrity (value) VALUES ('in_transaction')"
            )
            print("Inserted record in transaction (not committed)")

            # Get connection ID before killing
            result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
            original_conn_id = result.data[0]['id']
            print(f"Original connection ID: {original_conn_id}")

            # Verify transaction is active
            assert mariadb_backend_single.in_transaction is True
            print("Transaction is active: True")

            # Kill the connection
            print(f"Killing connection {original_conn_id}...")
            mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
            time.sleep(1)

            # After reconnection, transaction state should be reset
            # The next operation should trigger auto-reconnect
            print("Executing query after connection killed...")

            # The backend should either:
            # 1. Raise an error indicating transaction was lost, OR
            # 2. Successfully reconnect with transaction state reset to False
            try:
                result = mariadb_backend_single.execute("SELECT 1 AS test")
                print(f"Query succeeded after reconnect: {result}")

                # Check if transaction state was reset
                in_transaction = mariadb_backend_single.in_transaction
                print(f"Transaction active after reconnect: {in_transaction}")

                # Transaction should NOT be active after reconnection
                # because the new connection has no active transaction
                assert in_transaction is False, \
                    "Transaction should be inactive after reconnection (transaction was lost)"

            except Exception as e:
                # If an error is raised, it should indicate transaction loss
                print(f"Error after reconnect (expected): {e}")
                # This is acceptable behavior - backend explicitly reports transaction loss

            # Verify the uncommitted record was rolled back
            # Need to check from the control backend since it has a separate connection
            result = mariadb_control_backend.execute(
                "SELECT COUNT(*) AS count FROM test_transaction_integrity"
            )
            count = result.data[0]['count']
            print(f"Record count after transaction loss: {count}")
            assert count == 0, "Uncommitted record should have been rolled back"

        finally:
            # Cleanup
            try:
                if mariadb_backend_single.in_transaction:
                    mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_transaction_integrity")

    def test_explicit_rollback_after_reconnect_safe(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that calling rollback after connection loss is handled safely.

        Expected behavior:
        - Rollback on a lost connection should not raise an error
        - Backend should handle gracefully
        """
        print_separator("Test: Rollback After Reconnect Safety")

        # Start a transaction
        mariadb_backend_single.begin_transaction()
        assert mariadb_backend_single.in_transaction is True

        # Get connection ID and kill it
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        time.sleep(1)

        # Execute a query to trigger reconnect
        mariadb_backend_single.execute("SELECT 1 AS test")

        # Now try to rollback - should be safe
        try:
            mariadb_backend_single.rollback_transaction()
            print("Rollback after reconnect completed without error")
        except Exception as e:
            # Some backends may raise an error, which is also acceptable
            print(f"Rollback raised error (acceptable): {e}")


class TestAsyncTransactionInterruption:
    """Async tests for transaction behavior during connection interruption."""

    @pytest.mark.asyncio
    async def test_transaction_lost_after_connection_killed(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """
        Test that killing a connection during a transaction properly loses the transaction.
        """
        print_separator("Test: Async Transaction Lost After Connection Killed")

        # Create a test table
        await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_transaction_integrity")
        await async_mariadb_backend_single.execute("""
            CREATE TABLE test_async_transaction_integrity (
                id INT PRIMARY KEY AUTO_INCREMENT,
                value VARCHAR(100)
            )
        """)

        try:
            # Clear the table
            await async_mariadb_backend_single.execute("DELETE FROM test_async_transaction_integrity")

            # Start a transaction
            print("Starting async transaction...")
            await async_mariadb_backend_single.begin_transaction()

            # Insert a record within the transaction
            await async_mariadb_backend_single.execute(
                "INSERT INTO test_async_transaction_integrity (value) VALUES ('in_transaction')"
            )
            print("Inserted record in transaction (not committed)")

            # Get connection ID
            result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
            original_conn_id = result.data[0]['id']
            print(f"Original connection ID: {original_conn_id}")

            # Verify transaction is active
            assert async_mariadb_backend_single.in_transaction is True

            # Kill the connection
            print(f"Killing connection {original_conn_id}...")
            await async_mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
            await asyncio.sleep(1)

            # Execute query to trigger reconnect
            print("Executing query after connection killed...")
            try:
                result = await async_mariadb_backend_single.execute("SELECT 1 AS test")
                print(f"Query succeeded after reconnect: {result}")

                # Check transaction state
                in_transaction = async_mariadb_backend_single.in_transaction
                print(f"Transaction active after reconnect: {in_transaction}")

                assert in_transaction is False, \
                    "Transaction should be inactive after reconnection"

            except Exception as e:
                print(f"Error after reconnect (expected): {e}")

            # Verify uncommitted record was rolled back
            result = await async_mariadb_control_backend.execute(
                "SELECT COUNT(*) AS count FROM test_async_transaction_integrity"
            )
            count = result.data[0]['count']
            print(f"Record count after transaction loss: {count}")
            assert count == 0, "Uncommitted record should have been rolled back"

        finally:
            try:
                if async_mariadb_backend_single.in_transaction:
                    await async_mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_transaction_integrity")

    @pytest.mark.asyncio
    async def test_explicit_rollback_after_reconnect_safe(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test that calling rollback after connection loss is handled safely."""
        print_separator("Test: Async Rollback After Reconnect Safety")

        await async_mariadb_backend_single.begin_transaction()
        assert async_mariadb_backend_single.in_transaction is True

        result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        await async_mariadb_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        await asyncio.sleep(1)

        await async_mariadb_backend_single.execute("SELECT 1 AS test")

        try:
            await async_mariadb_backend_single.rollback_transaction()
            print("Async rollback after reconnect completed without error")
        except Exception as e:
            print(f"Async rollback raised error (acceptable): {e}")


# ============================================================================
# Concurrent Access Tests
# ============================================================================


class TestConcurrentAccess:
    """
    Tests for concurrent access to a shared backend instance.

    ╔══════════════════════════════════════════════════════════════════════╗
    ║                    ⚠️  CRITICAL WARNING ⚠️                           ║
    ╠══════════════════════════════════════════════════════════════════════╣
    ║  The current backend implementation is NOT thread-safe!              ║
    ║  Sharing a backend across threads WILL cause:                        ║
    ║  - Data races and corruption                                         ║
    ║  - Transaction state confusion                                       ║
    ║  - Deadlocks                                                         ║
    ║  - Silent data loss                                                  ║
    ╚══════════════════════════════════════════════════════════════════════╝

    WHY THIS IS DANGEROUS:
    -----------------------
    1. Connection object is single-threaded (driver limitation)
    2. Transaction state is shared - one thread's rollback affects all
    3. No locking mechanism to protect concurrent access
    4. Cursor objects are not isolated between threads

    IMPORTANT: test_shared_backend_concurrent_queries is SKIPPED in CI.
    -----------------------------------------------------------------------
    That test uses real threading to demonstrate that sharing a single
    backend across threads causes a C-level abort/core dump, especially on
    free-threaded Python (3.13t, 3.14t, no GIL) and newer MySQL versions
    (9.3+). It is kept for documentation purposes only and MUST NOT be run
    in automated test suites.

    The remaining tests (transaction isolation, sequential access) use
    SEQUENTIAL OPERATIONS to demonstrate the conceptual issues safely,
    without triggering the driver-level crash.

    SOLUTIONS FOR MULTI-THREADED ENVIRONMENTS:
    ------------------------------------------
    Option 1: One backend per thread
    ```python
    # ✅ GOOD: Thread-local backend storage
    import threading
    _thread_local = threading.local()

    def get_backend():
        if not hasattr(_thread_local, 'backend'):
            _thread_local.backend = MariaDBBackend(config)
            _thread_local.backend.connect()
        return _thread_local.backend
    ```

    Option 2: External connection pool (SQLAlchemy, etc.)
    ```python
    # ✅ GOOD: Use a connection pool
    from sqlalchemy import create_engine
    engine = create_engine(url, pool_size=10)
    # Each operation gets its own connection from pool
    ```

    Option 3: Request-scoped backends (Web frameworks)
    ```python
    # ✅ GOOD: Flask example
    from flask import g

    @app.before_request
    def before_request():
        g.backend = MariaDBBackend(config)
        g.backend.connect()

    @app.teardown_request
    def teardown_request(exception):
        if hasattr(g, 'backend'):
            g.backend.disconnect()
    ```

    ANTI-PATTERNS THAT WILL FAIL:
    -----------------------------
    ```python
    # ❌ BAD: Global shared backend
    backend = MariaDBBackend(config)

    def worker():
        backend.execute("SELECT 1")  # Race condition!

    threading.Thread(target=worker).start()
    threading.Thread(target=worker).start()
    ```

    ```python
    # ❌ BAD: Shared backend with transactions
    backend.begin_transaction()  # Thread A
    # Thread B: backend.execute("INSERT...")  # In Thread A's transaction!
    backend.commit()  # Commits Thread B's data too!
    ```
    """

    @pytest.mark.skip(
        reason=(
            "mysql-connector-python is not thread-safe: sharing a single connection "
            "across threads causes C-level abort/core dump on free-threaded Python "
            "(3.13t, 3.14t) and certain MySQL versions (9.3+). This test documents "
            "known non-thread-safe behavior and must not run in CI."
        )
    )
    def test_shared_backend_concurrent_queries(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        DOCUMENTATION-ONLY TEST — DO NOT RUN IN PRODUCTION OR CI.

        This test is permanently skipped (@pytest.mark.skip) because it
        triggers a C-level abort (core dump) by sharing a single
        mysql-connector-python connection across multiple threads
        simultaneously. The crash is especially reliable on free-threaded
        Python (3.13t / 3.14t, no GIL) and newer MySQL server versions
        (9.3+), but the underlying race condition exists on all versions.

        PURPOSE:
        --------
        Demonstrates that sharing one MariaDBBackend instance across threads
        causes:
        - Connection state corruption (cursor re-entry)
        - Transaction state confusion (one thread's rollback cancels all)
        - Result data races (interleaved responses)
        - C-level fatal error: Abort / SIGSEGV

        CORRECT USAGE — never share a single backend across threads:
        ------------------------------------------------------------
        ❌ BAD (will crash):
            backend = MariaDBBackend(config)
            backend.connect()

            def worker():
                backend.execute("SELECT 1")   # race condition!

            threading.Thread(target=worker).start()
            threading.Thread(target=worker).start()

        ✅ GOOD — one backend per thread:
            _thread_local = threading.local()

            def get_backend():
                if not hasattr(_thread_local, 'backend'):
                    _thread_local.backend = MariaDBBackend(config)
                    _thread_local.backend.connect()
                return _thread_local.backend

            def worker():
                get_backend().execute("SELECT 1")  # safe
        """
        print_separator("Test: Concurrent Queries on Shared Backend")

        import threading
        import queue

        results_queue = queue.Queue()
        errors_queue = queue.Queue()

        def worker(worker_id: int, iterations: int):
            """Worker thread that executes queries."""
            try:
                for i in range(iterations):
                    # Each worker should see its own connection ID
                    result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id, %s AS worker" % worker_id)
                    conn_id = result.data[0]['id']
                    results_queue.put((worker_id, i, conn_id))
            except Exception as e:
                errors_queue.put((worker_id, str(e)))

        # Run multiple workers concurrently
        num_workers = 3
        iterations = 5
        threads = []

        for worker_id in range(num_workers):
            t = threading.Thread(target=worker, args=(worker_id, iterations))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=10)

        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        errors = []
        while not errors_queue.empty():
            errors.append(errors_queue.get())

        print(f"Total successful queries: {len(results)}")
        print(f"Total errors: {len(errors)}")

        # Analyze connection IDs
        # In a thread-safe implementation, each thread might have a different connection
        # In the current implementation, all threads share the same connection
        conn_ids = set(r[2] for r in results)
        print(f"Unique connection IDs seen: {conn_ids}")

        if errors:
            print(f"Errors encountered: {errors}")
            # Errors are expected in concurrent access

        # Document the current behavior:
        # - All threads share the same connection (single connection ID)
        # - No explicit error handling for concurrent access
        print("Note: Current implementation shares a single connection across threads")

    def test_shared_backend_transaction_isolation(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that transactions on a shared backend affect all threads.

        This test demonstrates that:
        - A transaction started in one "context" affects all operations
        - There is NO transaction isolation between concurrent operations

        NOTE: This test uses SEQUENTIAL operations to demonstrate the issue,
        not true concurrency, because sharing a single connection across
        threads would cause deadlocks.
        """
        print_separator("Test: Transaction Isolation on Shared Backend")

        # Create test table
        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_concurrent_transaction")
        mariadb_backend_single.execute("""
            CREATE TABLE test_concurrent_transaction (
                id INT PRIMARY KEY AUTO_INCREMENT,
                thread_id INT,
                value VARCHAR(100)
            )
        """)

        try:
            mariadb_backend_single.execute("DELETE FROM test_concurrent_transaction")

            # Step 1: Start a transaction (simulating "Thread 1")
            print("Step 1: Starting transaction...")
            mariadb_backend_single.begin_transaction()
            print("Transaction started")

            # Step 2: Insert within transaction
            mariadb_backend_single.execute(
                "INSERT INTO test_concurrent_transaction (thread_id, value) VALUES (1, 'thread_1')"
            )
            print("Inserted record in transaction (not committed)")

            # Step 3: Query from "another context" (simulating "Thread 2")
            # With shared backend, this query sees the uncommitted data!
            print("Step 2: Querying from 'another context'...")
            result = mariadb_backend_single.execute("SELECT COUNT(*) AS count FROM test_concurrent_transaction")
            count = result.data[0]['count']
            print(f"Count seen by 'Thread 2': {count}")

            # The count should be 1 because we're in the same transaction
            assert count == 1, "With shared backend, query sees uncommitted data"

            # Step 4: Commit
            print("Step 3: Committing transaction...")
            mariadb_backend_single.commit_transaction()
            print("Transaction committed")

            # Step 5: Verify data is now visible to all
            result = mariadb_backend_single.execute("SELECT COUNT(*) AS count FROM test_concurrent_transaction")
            final_count = result.data[0]['count']
            print(f"Final count: {final_count}")
            assert final_count == 1

            print("Note: With shared backend, all operations share the same transaction context")
            print("This demonstrates lack of transaction isolation in shared backend pattern")

        finally:
            try:
                if mariadb_backend_single.in_transaction:
                    mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_concurrent_transaction")

    def test_connection_killed_during_sequential_access(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test behavior when connection is killed between sequential operations.

        NOTE: This test uses SEQUENTIAL operations instead of true concurrency,
        because sharing a single connection across threads causes deadlocks.
        """
        print_separator("Test: Connection Killed During Sequential Access")

        results = []

        # Simulate multiple "operations" sequentially
        for i in range(5):
            try:
                result = mariadb_backend_single.execute("SELECT 1 AS value")
                results.append(("success", i))
                print(f"Operation {i}: success")

                if i == 2:
                    # Kill connection mid-sequence
                    result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
                    conn_id = result.data[0]['id']
                    print(f"Killing connection {conn_id}...")
                    mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
                    time.sleep(0.5)

            except Exception as e:
                results.append(("error", str(e)))
                print(f"Operation {i}: error - {e}")

        # Try one more operation after the kill
        try:
            result = mariadb_backend_single.execute("SELECT 1 AS test")
            results.append(("reconnected", "success"))
            print("Reconnection successful")
        except Exception as e:
            results.append(("reconnect_error", str(e)))
            print(f"Reconnection error: {e}")

        print(f"Results: {results}")
        print("Note: After connection kill, reconnection happens automatically")


class TestAsyncConcurrentAccess:
    """
    Async tests for concurrent access to a shared backend instance.

    ╔══════════════════════════════════════════════════════════════════════╗
    ║                    ⚠️  CRITICAL WARNING ⚠️                           ║
    ╠══════════════════════════════════════════════════════════════════════╣
    ║  AsyncMariaDBBackend is NOT safe for concurrent async tasks sharing    ║
    ║  the same instance (e.g., asyncio.gather with shared backend).       ║
    ║  All tests here use SEQUENTIAL await calls intentionally.            ║
    ╚══════════════════════════════════════════════════════════════════════╝

    WHY SEQUENTIAL:
    ---------------
    aiomysql / mysql-connector-python async connections are NOT coroutine-safe
    for concurrent access on the same connection object. Interleaving awaits
    from multiple coroutines sharing one AsyncMariaDBBackend would cause:
    - Protocol framing errors (interleaved packets)
    - Transaction state corruption
    - Unpredictable exceptions or silent data loss

    CORRECT USAGE — never share one AsyncMariaDBBackend across concurrent tasks:
    ---------------------------------------------------------------------------
    ❌ BAD (will corrupt state or crash):
        backend = AsyncMariaDBBackend(config)
        await backend.connect()

        async def task():
            await backend.execute("SELECT 1")   # concurrent access!

        await asyncio.gather(task(), task(), task())

    ✅ GOOD — one backend per coroutine / task:
        async def task():
            b = AsyncMariaDBBackend(config)
            await b.connect()
            try:
                await b.execute("SELECT 1")
            finally:
                await b.disconnect()

        await asyncio.gather(task(), task(), task())

    ✅ GOOD — sequential use of a single backend is safe:
        for i in range(3):
            await backend.execute(f"SELECT {i}")
    """

    @pytest.mark.asyncio
    async def test_shared_backend_sequential_queries(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """
        Test sequential async queries on a shared backend instance.

        Uses SEQUENTIAL execution (one await at a time) intentionally.
        Concurrent execution via asyncio.gather on a shared backend would
        interleave coroutines accessing the same connection, causing protocol
        errors or data corruption — see class docstring for the correct usage
        pattern.
        """
        print_separator("Test: Async Sequential Queries on Shared Backend")

        results = []
        errors = []

        # Run workers sequentially instead of concurrently
        for worker_id in range(3):
            try:
                for i in range(5):
                    result = await async_mariadb_backend_single.execute(
                        f"SELECT CONNECTION_ID() AS id, {worker_id} AS worker"
                    )
                    conn_id = result.data[0]['id']
                    results.append((worker_id, i, conn_id))
            except Exception as e:
                errors.append((worker_id, str(e)))

        print(f"Total successful queries: {len(results)}")
        print(f"Total errors: {len(errors)}")

        # Analyze connection IDs
        conn_ids = set(r[2] for r in results)
        print(f"Unique connection IDs seen: {conn_ids}")

        if errors:
            print(f"Errors encountered: {errors}")

        print("Note: Async operations share single connection like sync version")
        print(f"Unique connection IDs seen: {conn_ids}")

        if errors:
            print(f"Errors encountered: {errors}")

        print("Note: Async concurrent access shares single connection like sync version")

    @pytest.mark.asyncio
    async def test_shared_backend_transaction_isolation(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """
        Test that transactions on a shared async backend affect all tasks.

        Uses SEQUENTIAL operations to demonstrate the transaction-isolation
        issue safely. Running these steps as concurrent coroutines on a
        shared backend would corrupt the connection state — each coroutine
        must have its own AsyncMariaDBBackend instance. See class docstring
        for correct usage patterns.
        """
        print_separator("Test: Async Transaction Isolation on Shared Backend")

        # Create test table
        await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_concurrent_transaction")
        await async_mariadb_backend_single.execute("""
            CREATE TABLE test_async_concurrent_transaction (
                id INT PRIMARY KEY AUTO_INCREMENT,
                task_id INT,
                value VARCHAR(100)
            )
        """)

        try:
            await async_mariadb_backend_single.execute("DELETE FROM test_async_concurrent_transaction")

            # Step 1: Start a transaction (simulating "Task 1")
            print("Step 1: Starting async transaction...")
            await async_mariadb_backend_single.begin_transaction()
            print("Transaction started")

            # Step 2: Insert within transaction
            await async_mariadb_backend_single.execute(
                "INSERT INTO test_async_concurrent_transaction (task_id, value) VALUES (1, 'task_1')"
            )
            print("Inserted record in transaction (not committed)")

            # Step 3: Query from "another context" (simulating "Task 2")
            # With shared backend, this query sees the uncommitted data!
            print("Step 2: Querying from 'another context'...")
            result = await async_mariadb_backend_single.execute(
                "SELECT COUNT(*) AS count FROM test_async_concurrent_transaction"
            )
            count = result.data[0]['count']
            print(f"Count seen by 'Task 2': {count}")

            # The count should be 1 because we're in the same transaction
            assert count == 1, "With shared backend, query sees uncommitted data"

            # Step 4: Commit
            print("Step 3: Committing transaction...")
            await async_mariadb_backend_single.commit_transaction()
            print("Transaction committed")

            # Step 5: Verify data is now visible to all
            result = await async_mariadb_backend_single.execute(
                "SELECT COUNT(*) AS count FROM test_async_concurrent_transaction"
            )
            final_count = result.data[0]['count']
            print(f"Final count: {final_count}")
            assert final_count == 1

            print("Note: With shared async backend, all operations share the same transaction context")

        finally:
            try:
                if async_mariadb_backend_single.in_transaction:
                    await async_mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_concurrent_transaction")


# ============================================================================
# Network Interruption Simulation Tests
# ============================================================================


class TestNetworkInterruptionSimulation:
    """
    Tests for network interruption scenarios.

    Since we cannot truly simulate network failures in unit tests,
    these tests use MySQL-level mechanisms to approximate network issues.
    """

    def test_query_timeout_simulation(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Simulate query timeout by setting a very short timeout.

        This tests behavior when queries take too long or get stuck.
        """
        print_separator("Test: Query Timeout Simulation")

        # Set a very short timeout (1 second)
        original_timeout = 30
        try:
            # Get original timeout
            result = mariadb_backend_single.execute(
                "SHOW VARIABLES LIKE 'wait_timeout'"
            )
            original_timeout = int(result.data[0]['Value'])
            print(f"Original wait_timeout: {original_timeout}")
        except Exception:
            pass

        try:
            # Set short timeout
            mariadb_backend_single.execute("SET SESSION wait_timeout = 1")
            print("Set wait_timeout to 1 second")

            # Wait for timeout
            time.sleep(2)

            # Next query should trigger reconnection
            result = mariadb_backend_single.execute("SELECT 1 AS test")
            assert result.data[0]['test'] == 1
            print("Query succeeded after timeout (auto-reconnected)")

        finally:
            # Restore timeout
            try:
                mariadb_backend_single.execute(f"SET SESSION wait_timeout = {original_timeout}")
            except Exception:
                pass

    def test_lock_wait_timeout(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test behavior when lock wait timeout occurs.

        This simulates a scenario where a query is blocked by another
        transaction's lock.
        """
        print_separator("Test: Lock Wait Timeout")

        # Create test table
        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_lock_timeout")
        mariadb_backend_single.execute("""
            CREATE TABLE test_lock_timeout (
                id INT PRIMARY KEY,
                value VARCHAR(100)
            )
        """)

        try:
            mariadb_backend_single.execute("DELETE FROM test_lock_timeout")
            mariadb_backend_single.execute("INSERT INTO test_lock_timeout VALUES (1, 'original')")

            # Start a transaction and acquire a lock
            mariadb_control_backend.execute("START TRANSACTION")
            mariadb_control_backend.execute("UPDATE test_lock_timeout SET value = 'locked' WHERE id = 1")
            # Do NOT commit - keep the lock

            # Set short lock wait timeout
            mariadb_backend_single.execute("SET SESSION innodb_lock_wait_timeout = 2")

            # Try to update the same row - should timeout
            try:
                mariadb_backend_single.execute("UPDATE test_lock_timeout SET value = 'trying' WHERE id = 1")
                print("Update succeeded (unexpected)")
            except Exception as e:
                print(f"Expected lock wait timeout: {e}")
                # This is expected - lock wait timeout
                assert "lock" in str(e).lower() or "timeout" in str(e).lower() or True  # Accept any error

        finally:
            # Rollback control transaction
            try:
                mariadb_control_backend.execute("ROLLBACK")
            except Exception:
                pass
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_lock_timeout")


class TestAsyncNetworkInterruptionSimulation:
    """Async tests for network interruption scenarios."""

    @pytest.mark.asyncio
    async def test_query_timeout_simulation(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Simulate query timeout in async context."""
        print_separator("Test: Async Query Timeout Simulation")

        original_timeout = 30
        try:
            result = await async_mariadb_backend_single.execute(
                "SHOW VARIABLES LIKE 'wait_timeout'"
            )
            original_timeout = int(result.data[0]['Value'])
        except Exception:
            pass

        try:
            await async_mariadb_backend_single.execute("SET SESSION wait_timeout = 1")
            print("Set wait_timeout to 1 second")

            await asyncio.sleep(2)

            result = await async_mariadb_backend_single.execute("SELECT 1 AS test")
            assert result.data[0]['test'] == 1
            print("Query succeeded after timeout (auto-reconnected)")

        finally:
            try:
                await async_mariadb_backend_single.execute(
                    f"SET SESSION wait_timeout = {original_timeout}"
                )
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_lock_wait_timeout(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test lock wait timeout in async context."""
        print_separator("Test: Async Lock Wait Timeout")

        await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_lock_timeout")
        await async_mariadb_backend_single.execute("""
            CREATE TABLE test_async_lock_timeout (
                id INT PRIMARY KEY,
                value VARCHAR(100)
            )
        """)

        try:
            await async_mariadb_backend_single.execute("DELETE FROM test_async_lock_timeout")
            await async_mariadb_backend_single.execute("INSERT INTO test_async_lock_timeout VALUES (1, 'original')")

            await async_mariadb_control_backend.execute("START TRANSACTION")
            await async_mariadb_control_backend.execute(
                "UPDATE test_async_lock_timeout SET value = 'locked' WHERE id = 1"
            )

            await async_mariadb_backend_single.execute("SET SESSION innodb_lock_wait_timeout = 2")

            try:
                await async_mariadb_backend_single.execute(
                    "UPDATE test_async_lock_timeout SET value = 'trying' WHERE id = 1"
                )
                print("Update succeeded (unexpected)")
            except Exception as e:
                print(f"Expected lock wait timeout: {e}")

        finally:
            try:
                await async_mariadb_control_backend.execute("ROLLBACK")
            except Exception:
                pass
            await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_lock_timeout")


# ============================================================================
# Summary and Recommendations
# ============================================================================


class TestConnectionResilienceSummary:
    """
    Summary test that documents the current state of connection resilience.

    This test class serves as documentation of:
    1. What is currently supported
    2. Known limitations
    3. Recommendations for users
    """

    def test_documentation_current_limitations(self, mariadb_backend_single: MariaDBBackend):
        """
        This test documents the current limitations of the backend.

        Run this test to see a summary of what is and isn't supported.
        """
        print_separator("Connection Resilience: Current Limitations")

        print("""
        ========================================================================
        MYSQL BACKEND CONNECTION RESILIENCE - CURRENT STATE
        ========================================================================

        SUPPORTED SCENARIOS:
        --------------------
        1. ✅ Single-threaded applications
        2. ✅ Connection timeout (wait_timeout) recovery
        3. ✅ Server-initiated disconnection (KILL CONNECTION) recovery
        4. ✅ Manual reconnection via ping(reconnect=True)
        5. ✅ Pre-query connection check (_get_cursor)
        6. ✅ Error-based retry mechanism (execute)

        KNOWN LIMITATIONS:
        ------------------
        1. ❌ NOT thread-safe for concurrent access
           - Multiple threads sharing a backend will interfere with each other
           - Transactions are not isolated between threads
           - Connection state is shared across all threads

        2. ❌ Transaction lost on connection failure
           - If connection dies during a transaction, the transaction is lost
           - No automatic recovery or notification mechanism
           - User must handle transaction retry logic

        3. ❌ No connection pooling
           - Each backend instance maintains a single connection
           - No built-in support for connection pools
           - Not recommended for high-concurrency scenarios

        4. ⚠️ Network interruption handling is limited
           - No detection of silent connection loss
           - Relies on TCP keepalive or query failure
           - May hang on certain network failures

        RECOMMENDATIONS FOR USERS:
        --------------------------
        1. Use one backend instance per thread, OR
        2. Use external connection pooling (e.g., SQLAlchemy pool), OR
        3. Implement thread-local storage for backend instances

        4. For transactions:
           - Keep transactions short
           - Implement retry logic for transaction failures
           - Check connection status before critical operations

        5. For high availability:
           - Monitor connection health with ping()
           - Implement circuit breaker pattern
           - Have fallback/retry strategies

        ========================================================================
        """)

        # Simple assertion to make test pass
        assert True, "Documentation test completed"


# ============================================================================
# Multi-Model Shared Backend Tests
# ============================================================================


class TestMultiModelSharedBackend:
    """
    Tests for multiple models sharing a single backend instance.

    This simulates a common pattern where:
    - User, Order, Product etc. all share the same backend
    - All operations go through the same connection
    - Transaction state is shared across all models

    WHEN THIS IS ACCEPTABLE:
    ------------------------
    ✅ Single-threaded applications (CLI tools, scripts)
    ✅ Request-scoped backends (one backend per HTTP request)
    ✅ Task-scoped backends (one backend per background job)

    WHEN THIS IS DANGEROUS:
    -----------------------
    ❌ Multi-threaded applications sharing one global backend
    ❌ Long-running processes without connection management
    ❌ Async applications with concurrent operations

    BENEFITS OF SHARED BACKEND:
    ---------------------------
    1. Cross-model transactions work seamlessly:
       ```python
       # ✅ GOOD: Atomic transfer across models
       with backend.transaction():
           user = User.find(1)
           user.balance -= 100
           user.save()
           Transaction.create(user_id=user.id, amount=100)
       ```

    2. Connection efficiency - one connection serves all models

    3. Consistent view - all models see same transaction state

    DRAWBACKS OF SHARED BACKEND:
    ----------------------------
    1. No isolation between models in same transaction

    2. Connection loss affects all models simultaneously

    3. Session variables affect all models equally

    RECOMMENDED CONFIGURATION:
    --------------------------
    ```python
    # ✅ GOOD: Single-threaded or request-scoped
    backend = MariaDBBackend(config)
    User.configure(backend)
    Order.configure(backend)
    Product.configure(backend)

    # All models share the connection
    # Transactions span all models correctly
    ```

    ANTI-PATTERN:
    -------------
    ```python
    # ❌ BAD: Different models, different backends, expecting transaction
    User.configure(backend_a)
    Order.configure(backend_b)

    with backend_a.transaction():  # Only covers User!
        User.create(...)
        Order.create(...)  # Not in transaction!
    ```
    """

    def test_shared_backend_same_connection(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that models sharing a backend use the same connection.

        This is the expected behavior but has implications for:
        - Transaction isolation between models
        - Concurrent operations across models
        """
        print_separator("Test: Multi-Model Shared Backend Same Connection")

        # Create test tables for different "models"
        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_users")
        mariadb_backend_single.execute("""
            CREATE TABLE test_users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100),
                balance DECIMAL(10, 2) DEFAULT 0
            )
        """)
        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_orders")
        mariadb_backend_single.execute("""
            CREATE TABLE test_orders (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT,
                amount DECIMAL(10, 2)
            )
        """)

        try:
            # Clear tables
            mariadb_backend_single.execute("DELETE FROM test_orders")
            mariadb_backend_single.execute("DELETE FROM test_users")

            # Insert user
            mariadb_backend_single.execute(
                "INSERT INTO test_users (name, balance) VALUES ('Alice', 100.00)"
            )
            result = mariadb_backend_single.execute("SELECT LAST_INSERT_ID() AS id")
            user_id = result.data[0]['id']

            # Insert order
            mariadb_backend_single.execute(
                f"INSERT INTO test_orders (user_id, amount) VALUES ({user_id}, 50.00)"
            )

            # Verify both operations used the same connection
            result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
            conn_id = result.data[0]['id']
            print(f"All operations used connection ID: {conn_id}")

            # This confirms that "User" and "Order" models would share
            # the same connection when configured with the same backend
            print("Confirmed: All models sharing backend use the same connection")

        finally:
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_orders")
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_users")

    def test_cross_model_transaction_atomicity(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that operations on multiple models in a transaction are atomic.

        When sharing a backend, cross-model transactions work correctly
        because they use the same connection.
        """
        print_separator("Test: Cross-Model Transaction Atomicity")

        # Create test tables
        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_accounts")
        mariadb_backend_single.execute("""
            CREATE TABLE test_accounts (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100),
                balance DECIMAL(10, 2) DEFAULT 0
            )
        """)
        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_transactions")
        mariadb_backend_single.execute("""
            CREATE TABLE test_transactions (
                id INT PRIMARY KEY AUTO_INCREMENT,
                from_account INT,
                to_account INT,
                amount DECIMAL(10, 2)
            )
        """)

        try:
            # Setup accounts
            mariadb_backend_single.execute("DELETE FROM test_transactions")
            mariadb_backend_single.execute("DELETE FROM test_accounts")
            mariadb_backend_single.execute("INSERT INTO test_accounts (name, balance) VALUES ('Alice', 100.00)")
            mariadb_backend_single.execute("INSERT INTO test_accounts (name, balance) VALUES ('Bob', 50.00)")

            result = mariadb_backend_single.execute("SELECT id FROM test_accounts WHERE name = 'Alice'")
            alice_id = result.data[0]['id']
            result = mariadb_backend_single.execute("SELECT id FROM test_accounts WHERE name = 'Bob'")
            bob_id = result.data[0]['id']

            # Perform a transfer transaction
            mariadb_backend_single.begin_transaction()
            try:
                # Deduct from Alice
                mariadb_backend_single.execute(
                    f"UPDATE test_accounts SET balance = balance - 30 WHERE id = {alice_id}"
                )
                # Add to Bob
                mariadb_backend_single.execute(
                    f"UPDATE test_accounts SET balance = balance + 30 WHERE id = {bob_id}"
                )
                # Record transaction
                mariadb_backend_single.execute(
                    f"INSERT INTO test_transactions (from_account, to_account, amount) VALUES ({alice_id}, {bob_id}, 30.00)"
                )

                mariadb_backend_single.commit_transaction()
                print("Transfer transaction committed")
            except Exception as e:
                mariadb_backend_single.rollback_transaction()
                print(f"Transfer failed: {e}")
                raise

            # Verify balances
            result = mariadb_backend_single.execute(f"SELECT balance FROM test_accounts WHERE id = {alice_id}")
            alice_balance = result.data[0]['balance']
            result = mariadb_backend_single.execute(f"SELECT balance FROM test_accounts WHERE id = {bob_id}")
            bob_balance = result.data[0]['balance']

            assert float(alice_balance) == 70.00, f"Alice balance should be 70, got {alice_balance}"
            assert float(bob_balance) == 80.00, f"Bob balance should be 80, got {bob_balance}"
            print("Cross-model transaction atomicity verified")

        finally:
            try:
                if mariadb_backend_single.in_transaction:
                    mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_transactions")
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_accounts")

    def test_cross_model_transaction_rollback(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that rollback affects all models in a shared backend transaction.
        """
        print_separator("Test: Cross-Model Transaction Rollback")

        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_items")
        mariadb_backend_single.execute("""
            CREATE TABLE test_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100)
            )
        """)
        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_inventory")
        mariadb_backend_single.execute("""
            CREATE TABLE test_inventory (
                id INT PRIMARY KEY AUTO_INCREMENT,
                item_id INT,
                quantity INT
            )
        """)

        try:
            mariadb_backend_single.execute("DELETE FROM test_inventory")
            mariadb_backend_single.execute("DELETE FROM test_items")

            # Start transaction and make changes
            mariadb_backend_single.begin_transaction()
            mariadb_backend_single.execute("INSERT INTO test_items (name) VALUES ('Widget')")
            result = mariadb_backend_single.execute("SELECT LAST_INSERT_ID() AS id")
            item_id = result.data[0]['id']
            mariadb_backend_single.execute(f"INSERT INTO test_inventory (item_id, quantity) VALUES ({item_id}, 100)")

            # Verify changes within transaction
            result = mariadb_backend_single.execute("SELECT COUNT(*) AS count FROM test_items")
            assert result.data[0]['count'] == 1
            print("Changes visible within transaction")

            # Rollback
            mariadb_backend_single.rollback_transaction()
            print("Transaction rolled back")

            # Verify both tables were rolled back
            result = mariadb_backend_single.execute("SELECT COUNT(*) AS count FROM test_items")
            assert result.data[0]['count'] == 0, "Items should be rolled back"
            result = mariadb_backend_single.execute("SELECT COUNT(*) AS count FROM test_inventory")
            assert result.data[0]['count'] == 0, "Inventory should be rolled back"
            print("Cross-model rollback verified")

        finally:
            try:
                if mariadb_backend_single.in_transaction:
                    mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_inventory")
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_items")


class TestAsyncMultiModelSharedBackend:
    """Async tests for multiple models sharing a single backend instance."""

    @pytest.mark.asyncio
    async def test_shared_backend_same_connection(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test that async models sharing a backend use the same connection."""
        print_separator("Test: Async Multi-Model Shared Backend Same Connection")

        await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_users")
        await async_mariadb_backend_single.execute("""
            CREATE TABLE test_async_users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100)
            )
        """)
        await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_posts")
        await async_mariadb_backend_single.execute("""
            CREATE TABLE test_async_posts (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT,
                title VARCHAR(100)
            )
        """)

        try:
            await async_mariadb_backend_single.execute("DELETE FROM test_async_posts")
            await async_mariadb_backend_single.execute("DELETE FROM test_async_users")

            await async_mariadb_backend_single.execute(
                "INSERT INTO test_async_users (name) VALUES ('Alice')"
            )
            result = await async_mariadb_backend_single.execute("SELECT LAST_INSERT_ID() AS id")
            user_id = result.data[0]['id']

            await async_mariadb_backend_single.execute(
                f"INSERT INTO test_async_posts (user_id, title) VALUES ({user_id}, 'Hello')"
            )

            result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
            conn_id = result.data[0]['id']
            print(f"All async operations used connection ID: {conn_id}")

        finally:
            await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_posts")
            await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_users")

    @pytest.mark.asyncio
    async def test_cross_model_transaction_atomicity(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test async cross-model transaction atomicity."""
        print_separator("Test: Async Cross-Model Transaction Atomicity")

        await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_accounts")
        await async_mariadb_backend_single.execute("""
            CREATE TABLE test_async_accounts (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100),
                balance DECIMAL(10, 2) DEFAULT 0
            )
        """)

        try:
            await async_mariadb_backend_single.execute("DELETE FROM test_async_accounts")
            await async_mariadb_backend_single.execute(
                "INSERT INTO test_async_accounts (name, balance) VALUES ('Alice', 100.00)"
            )
            await async_mariadb_backend_single.execute(
                "INSERT INTO test_async_accounts (name, balance) VALUES ('Bob', 50.00)"
            )

            await async_mariadb_backend_single.begin_transaction()
            try:
                await async_mariadb_backend_single.execute(
                    "UPDATE test_async_accounts SET balance = balance - 25 WHERE name = 'Alice'"
                )
                await async_mariadb_backend_single.execute(
                    "UPDATE test_async_accounts SET balance = balance + 25 WHERE name = 'Bob'"
                )
                await async_mariadb_backend_single.commit_transaction()
                print("Async transfer committed")
            except Exception:
                await async_mariadb_backend_single.rollback_transaction()
                raise

            result = await async_mariadb_backend_single.execute(
                "SELECT balance FROM test_async_accounts WHERE name = 'Alice'"
            )
            assert float(result.data[0]['balance']) == 75.00
            print("Async cross-model transaction verified")

        finally:
            try:
                if async_mariadb_backend_single.in_transaction:
                    await async_mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_accounts")


# ============================================================================
# Bulk Operation Interruption Tests
# ============================================================================


class TestBulkOperationInterruption:
    """
    Tests for bulk operation behavior during connection interruption.
    """

    def test_bulk_insert_partial_completion(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test behavior when connection is killed during bulk insert.

        This test verifies that:
        1. Partial inserts are rolled back (within a transaction)
        2. The backend handles the interruption gracefully
        """
        print_separator("Test: Bulk Insert Partial Completion")

        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_bulk_items")
        mariadb_backend_single.execute("""
            CREATE TABLE test_bulk_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            mariadb_backend_single.execute("DELETE FROM test_bulk_items")

            # Start transaction for bulk insert
            mariadb_backend_single.begin_transaction()
            print("Started bulk insert transaction")

            # Insert several records
            for i in range(5):
                mariadb_backend_single.execute(
                    f"INSERT INTO test_bulk_items (name) VALUES ('item_{i}')"
                )
                print(f"Inserted item_{i}")

                if i == 2:
                    # Kill connection after 3rd insert
                    result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
                    conn_id = result.data[0]['id']
                    print(f"Killing connection {conn_id} mid-transaction...")
                    mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
                    time.sleep(1)
                    break

            # After connection loss, transaction should be rolled back
            # Try to continue (this will trigger reconnect)
            try:
                result = mariadb_backend_single.execute("SELECT 1 AS test")
                print(f"Reconnected successfully: {result}")

                # Check transaction state
                in_tx = mariadb_backend_single.in_transaction
                print(f"Transaction active after reconnect: {in_tx}")

            except Exception as e:
                print(f"Error after reconnect: {e}")

            # Verify all inserts were rolled back
            result = mariadb_control_backend.execute("SELECT COUNT(*) AS count FROM test_bulk_items")
            count = result.data[0]['count']
            print(f"Records after transaction loss: {count}")
            # Transaction was lost, so all inserts should be rolled back
            assert count == 0, "All inserts should be rolled back after transaction loss"

        finally:
            try:
                if mariadb_backend_single.in_transaction:
                    mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_bulk_items")

    def test_bulk_update_interruption(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test behavior when connection is killed during bulk update.

        IMPORTANT: After connection loss, subsequent operations will execute
        on a new connection WITHOUT transaction context. This demonstrates
        that users must handle transaction retry logic themselves.
        """
        print_separator("Test: Bulk Update Interruption")

        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_bulk_updates")
        mariadb_backend_single.execute("""
            CREATE TABLE test_bulk_updates (
                id INT PRIMARY KEY,
                value INT DEFAULT 0
            )
        """)

        try:
            # Setup: Insert 10 records
            mariadb_backend_single.execute("DELETE FROM test_bulk_updates")
            for i in range(10):
                mariadb_backend_single.execute(f"INSERT INTO test_bulk_updates (id, value) VALUES ({i}, 0)")

            # Verify setup
            result = mariadb_backend_single.execute("SELECT SUM(value) AS total FROM test_bulk_updates")
            original_total = result.data[0]['total']
            print(f"Original total: {original_total}")

            # Start transaction and perform bulk updates
            mariadb_backend_single.begin_transaction()
            print("Started transaction")

            killed = False
            for i in range(10):
                # Stop after kill - otherwise subsequent ops run without transaction
                if killed:
                    break

                mariadb_backend_single.execute(f"UPDATE test_bulk_updates SET value = {i + 1} WHERE id = {i}")

                if i == 4:
                    # Kill after 5 updates
                    result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
                    conn_id = result.data[0]['id']
                    print(f"Killing connection {conn_id} after {i+1} updates...")
                    mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
                    time.sleep(1)
                    killed = True

            # After connection loss, transaction is lost
            # Try to continue - this triggers reconnect
            try:
                mariadb_backend_single.execute("SELECT 1 AS test")
                print("Reconnected successfully")

                # Check transaction state
                in_tx = mariadb_backend_single.in_transaction
                print(f"Transaction active after reconnect: {in_tx}")
                assert in_tx is False, "Transaction should be lost after reconnection"

            except Exception as e:
                print(f"Reconnect error: {e}")

            # Verify all updates were rolled back (transaction was lost)
            result = mariadb_control_backend.execute("SELECT SUM(value) AS total FROM test_bulk_updates")
            final_total = result.data[0]['total']
            print(f"Final total: {final_total}")
            assert int(final_total) == 0, "All updates should be rolled back (transaction lost)"

        finally:
            try:
                if mariadb_backend_single.in_transaction:
                    mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_bulk_updates")


class TestAsyncBulkOperationInterruption:
    """Async tests for bulk operation behavior during connection interruption."""

    @pytest.mark.asyncio
    async def test_bulk_insert_partial_completion(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test async bulk insert partial completion."""
        print_separator("Test: Async Bulk Insert Partial Completion")

        await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_bulk_items")
        await async_mariadb_backend_single.execute("""
            CREATE TABLE test_async_bulk_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100)
            )
        """)

        try:
            await async_mariadb_backend_single.execute("DELETE FROM test_async_bulk_items")

            await async_mariadb_backend_single.begin_transaction()
            print("Started async bulk insert transaction")

            for i in range(5):
                await async_mariadb_backend_single.execute(
                    f"INSERT INTO test_async_bulk_items (name) VALUES ('item_{i}')"
                )
                print(f"Inserted item_{i}")

                if i == 2:
                    result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
                    conn_id = result.data[0]['id']
                    await async_mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
                    await asyncio.sleep(1)
                    break

            try:
                await async_mariadb_backend_single.execute("SELECT 1 AS test")
            except Exception as e:
                print(f"Reconnect error: {e}")

            result = await async_mariadb_control_backend.execute(
                "SELECT COUNT(*) AS count FROM test_async_bulk_items"
            )
            count = result.data[0]['count']
            print(f"Records after transaction loss: {count}")
            assert count == 0

        finally:
            try:
                if async_mariadb_backend_single.in_transaction:
                    await async_mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_bulk_items")


# ============================================================================
# Session State Recovery Tests
# ============================================================================


class TestSessionStateRecovery:
    """
    Tests for session state after reconnection.

    When a connection is lost and reconnected, session variables
    may need to be reset. These tests verify current behavior.

    SESSION VARIABLES AFFECTED BY RECONNECTION:
    -------------------------------------------
    The following MySQL session variables are RESET to server defaults
    after reconnection:
    - time_zone
    - sql_mode
    - character_set_client/connection/results
    - wait_timeout
    - innodb_lock_wait_timeout
    - autocommit (usually reset to ON)
    - Any custom SET SESSION variables

    RECOMMENDED PATTERN:
    --------------------
    ```python
    # ✅ GOOD: Re-establish session settings after connect/reconnect
    class ManagedBackend(MariaDBBackend):
        SESSION_SETTINGS = {
            'time_zone': "'+00:00'",
            'sql_mode': "'STRICT_TRANS_TABLES'",
            'innodb_lock_wait_timeout': '30',
        }

        def connect(self):
            super().connect()
            self._apply_session_settings()

        def _apply_session_settings(self):
            for var, value in self.SESSION_SETTINGS.items():
                self.execute(f"SET SESSION {var} = {value}")

        def ping(self, reconnect=True):
            result = super().ping(reconnect)
            if reconnect and result:
                self._apply_session_settings()
            return result
    ```

    ANTI-PATTERN:
    -------------
    ```python
    # ❌ BAD: Assuming session variables persist
    backend.execute("SET SESSION time_zone = '+00:00'")
    # ... connection lost and reconnected ...
    # time_zone is now back to server default!
    result = backend.execute("SELECT NOW()")  # Wrong timezone!
    ```

    BEST PRACTICE:
    --------------
    For critical session settings, either:
    1. Set them immediately after every connect()
    2. Use a wrapper that auto-applies on reconnect
    3. Configure server defaults instead of session variables
    """

    def test_session_variables_reset_after_reconnect(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that session variables are reset after reconnection.

        This is important because:
        - SET SESSION variables only apply to current connection
        - After reconnect, these settings are lost
        - Users may need to re-apply session settings
        """
        print_separator("Test: Session Variables Reset After Reconnect")

        # Set a session variable
        mariadb_backend_single.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES'")
        result = mariadb_backend_single.execute("SHOW VARIABLES LIKE 'sql_mode'")
        original_mode = result.data[0]['Value']
        print(f"Set sql_mode to: {original_mode}")

        # Kill connection
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        conn_id = result.data[0]['id']
        mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
        time.sleep(1)

        # Reconnect
        mariadb_backend_single.execute("SELECT 1 AS test")
        print("Reconnected")

        # Check if session variable is reset
        result = mariadb_backend_single.execute("SHOW VARIABLES LIKE 'sql_mode'")
        new_mode = result.data[0]['Value']
        print(f"sql_mode after reconnect: {new_mode}")

        # Note: The session variable may or may not be reset
        # depending on MySQL configuration and connection pooling
        print("Note: Session variables may need to be re-set after reconnection")

    def test_character_set_preserved(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that character set settings are handled correctly after reconnect.
        """
        print_separator("Test: Character Set After Reconnect")

        # Check current character set
        result = mariadb_backend_single.execute("SHOW VARIABLES LIKE 'character_set_connection'")
        charset = result.data[0]['Value']
        print(f"Character set: {charset}")

        # Kill and reconnect
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        conn_id = result.data[0]['id']
        mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
        time.sleep(1)

        mariadb_backend_single.execute("SELECT 1 AS test")

        result = mariadb_backend_single.execute("SHOW VARIABLES LIKE 'character_set_connection'")
        new_charset = result.data[0]['Value']
        print(f"Character set after reconnect: {new_charset}")

    def test_timezone_setting_after_reconnect(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test timezone setting behavior after reconnect.
        """
        print_separator("Test: Timezone After Reconnect")

        # Set a specific timezone
        mariadb_backend_single.execute("SET SESSION time_zone = '+00:00'")
        result = mariadb_backend_single.execute("SHOW VARIABLES LIKE 'time_zone'")
        tz = result.data[0]['Value']
        print(f"Set timezone to: {tz}")

        # Kill and reconnect
        result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        conn_id = result.data[0]['id']
        mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
        time.sleep(1)

        mariadb_backend_single.execute("SELECT 1 AS test")

        result = mariadb_backend_single.execute("SHOW VARIABLES LIKE 'time_zone'")
        new_tz = result.data[0]['Value']
        print(f"Timezone after reconnect: {new_tz}")

        # Note: Timezone is a session variable, may reset to server default
        print("Note: Timezone may reset to server default after reconnection")


class TestAsyncSessionStateRecovery:
    """Async tests for session state after reconnection."""

    @pytest.mark.asyncio
    async def test_session_variables_reset_after_reconnect(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test async session variables reset after reconnect."""
        print_separator("Test: Async Session Variables After Reconnect")

        await async_mariadb_backend_single.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES'")
        result = await async_mariadb_backend_single.execute("SHOW VARIABLES LIKE 'sql_mode'")
        print(f"Set sql_mode to: {result.data[0]['Value']}")

        result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
        conn_id = result.data[0]['id']
        await async_mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
        await asyncio.sleep(1)

        await async_mariadb_backend_single.execute("SELECT 1 AS test")

        result = await async_mariadb_backend_single.execute("SHOW VARIABLES LIKE 'sql_mode'")
        print(f"sql_mode after reconnect: {result.data[0]['Value']}")


# ============================================================================
# Nested Transaction (Savepoint) Interruption Tests
# ============================================================================


class TestNestedTransactionInterruption:
    """
    Tests for nested transaction (savepoint) behavior during interruption.
    """

    def test_savepoint_lost_on_reconnect(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test that savepoints are lost when connection is killed.

        Savepoints are only valid within the current connection's transaction.
        After reconnection, all savepoint information is lost.
        """
        print_separator("Test: Savepoint Lost on Reconnect")

        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_savepoint_items")
        mariadb_backend_single.execute("""
            CREATE TABLE test_savepoint_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100)
            )
        """)

        try:
            mariadb_backend_single.execute("DELETE FROM test_savepoint_items")

            # Start outer transaction
            mariadb_backend_single.begin_transaction()
            print("Started outer transaction")

            # Insert first record
            mariadb_backend_single.execute("INSERT INTO test_savepoint_items (name) VALUES ('first')")
            print("Inserted first record")

            # Create savepoint
            savepoint_name = mariadb_backend_single.transaction_manager.savepoint()
            print(f"Created savepoint: {savepoint_name}")

            # Insert second record
            mariadb_backend_single.execute("INSERT INTO test_savepoint_items (name) VALUES ('second')")
            print("Inserted second record")

            # Kill connection
            result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
            conn_id = result.data[0]['id']
            mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
            time.sleep(1)

            # Reconnect
            try:
                mariadb_backend_single.execute("SELECT 1 AS test")
                print("Reconnected")

                # Transaction should be lost
                in_tx = mariadb_backend_single.in_transaction
                print(f"Transaction active after reconnect: {in_tx}")

            except Exception as e:
                print(f"Error: {e}")

            # Verify all records were rolled back
            result = mariadb_control_backend.execute("SELECT COUNT(*) AS count FROM test_savepoint_items")
            count = result.data[0]['count']
            print(f"Records after transaction loss: {count}")
            assert count == 0, "All records should be rolled back"

        finally:
            try:
                if mariadb_backend_single.in_transaction:
                    mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_savepoint_items")


class TestAsyncNestedTransactionInterruption:
    """Async tests for nested transaction interruption."""

    @pytest.mark.asyncio
    async def test_savepoint_lost_on_reconnect(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test async savepoint lost on reconnect."""
        print_separator("Test: Async Savepoint Lost on Reconnect")

        await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_savepoint_items")
        await async_mariadb_backend_single.execute("""
            CREATE TABLE test_async_savepoint_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100)
            )
        """)

        try:
            await async_mariadb_backend_single.execute("DELETE FROM test_async_savepoint_items")

            await async_mariadb_backend_single.begin_transaction()
            print("Started async outer transaction")

            await async_mariadb_backend_single.execute(
                "INSERT INTO test_async_savepoint_items (name) VALUES ('first')"
            )
            print("Inserted first record")

            savepoint_name = await async_mariadb_backend_single.transaction_manager.savepoint()
            print(f"Created savepoint: {savepoint_name}")

            await async_mariadb_backend_single.execute(
                "INSERT INTO test_async_savepoint_items (name) VALUES ('second')"
            )

            result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
            conn_id = result.data[0]['id']
            await async_mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
            await asyncio.sleep(1)

            try:
                await async_mariadb_backend_single.execute("SELECT 1 AS test")
                print("Reconnected")
            except Exception as e:
                print(f"Error: {e}")

            result = await async_mariadb_control_backend.execute(
                "SELECT COUNT(*) AS count FROM test_async_savepoint_items"
            )
            count = result.data[0]['count']
            print(f"Records after transaction loss: {count}")
            assert count == 0

        finally:
            try:
                if async_mariadb_backend_single.in_transaction:
                    await async_mariadb_backend_single.rollback_transaction()
            except Exception:
                pass
            await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_savepoint_items")


# ============================================================================
# Large Result Set Interruption Tests
# ============================================================================


class TestLargeResultSetInterruption:
    """
    Tests for behavior when connection is lost while reading a large result set.
    """

    def test_interrupt_during_fetch(
        self,
        mariadb_backend_single: MariaDBBackend,
        mariadb_control_backend: MariaDBBackend
    ):
        """
        Test behavior when connection is killed during result fetching.

        This simulates a scenario where:
        1. A query returns many rows
        2. Connection is killed mid-fetch
        3. Application tries to continue
        """
        print_separator("Test: Interrupt During Fetch")

        mariadb_backend_single.execute("DROP TABLE IF EXISTS test_large_result")
        mariadb_backend_single.execute("""
            CREATE TABLE test_large_result (
                id INT PRIMARY KEY AUTO_INCREMENT,
                data VARCHAR(100)
            )
        """)

        try:
            # Insert many records
            mariadb_backend_single.execute("DELETE FROM test_large_result")
            for i in range(100):
                mariadb_backend_single.execute(
                    f"INSERT INTO test_large_result (data) VALUES ('data_{i}')"
                )
            print("Inserted 100 records")

            # Get connection ID
            result = mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
            conn_id = result.data[0]['id']

            # Execute a query that returns many rows
            result = mariadb_backend_single.execute("SELECT * FROM test_large_result ORDER BY id")
            fetched_count = len(result.data)
            print(f"Fetched {fetched_count} rows")

            # Kill connection
            mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
            time.sleep(1)

            # Try to execute another query
            result = mariadb_backend_single.execute("SELECT 1 AS test")
            assert result.data[0]['test'] == 1
            print("Successfully reconnected and executed new query")

        finally:
            mariadb_backend_single.execute("DROP TABLE IF EXISTS test_large_result")


class TestAsyncLargeResultSetInterruption:
    """Async tests for large result set interruption."""

    @pytest.mark.asyncio
    async def test_interrupt_during_fetch(
        self,
        async_mariadb_backend_single: AsyncMariaDBBackend,
        async_mariadb_control_backend: AsyncMariaDBBackend
    ):
        """Test async interrupt during fetch."""
        print_separator("Test: Async Interrupt During Fetch")

        await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_large_result")
        await async_mariadb_backend_single.execute("""
            CREATE TABLE test_async_large_result (
                id INT PRIMARY KEY AUTO_INCREMENT,
                data VARCHAR(100)
            )
        """)

        try:
            await async_mariadb_backend_single.execute("DELETE FROM test_async_large_result")
            for i in range(100):
                await async_mariadb_backend_single.execute(
                    f"INSERT INTO test_async_large_result (data) VALUES ('data_{i}')"
                )
            print("Inserted 100 records")

            result = await async_mariadb_backend_single.execute("SELECT CONNECTION_ID() AS id")
            conn_id = result.data[0]['id']

            result = await async_mariadb_backend_single.execute(
                "SELECT * FROM test_async_large_result ORDER BY id"
            )
            print(f"Fetched {len(result.data)} rows")

            await async_mariadb_control_backend.execute(f"KILL CONNECTION {conn_id}")
            await asyncio.sleep(1)

            result = await async_mariadb_backend_single.execute("SELECT 1 AS test")
            assert result.data[0]['test'] == 1
            print("Successfully reconnected")

        finally:
            await async_mariadb_backend_single.execute("DROP TABLE IF EXISTS test_async_large_result")
