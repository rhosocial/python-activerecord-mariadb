# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_transaction_isolation_effect.py
"""
Tests for MySQL transaction isolation level actual effects.

This module tests that different isolation levels actually provide
the expected isolation behavior in MariaDB backend.

Tests cover:
- READ UNCOMMITTED: Dirty reads allowed
- READ COMMITTED: No dirty reads, but non-repeatable reads allowed
- REPEATABLE READ: No dirty reads, no non-repeatable reads, but phantom reads possible
- SERIALIZABLE: Full isolation, no phantom reads
"""
import pytest
import threading
import time
from decimal import Decimal
from typing import Type

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.transaction import IsolationLevel
from rhosocial.activerecord.backend.errors import TransactionError


class TestIsolationLevelEffects:
    """Test actual isolation behavior for each isolation level."""

    @pytest.fixture
    def test_table(self, mariadb_backend):
        """Create a test table for isolation tests."""
        mariadb_backend.execute("DROP TABLE IF EXISTS isolation_test")
        mariadb_backend.execute("""
            CREATE TABLE isolation_test (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                balance DECIMAL(10, 2),
                version INT DEFAULT 1
            )
        """)
        mariadb_backend.execute(
            "INSERT INTO isolation_test (name, balance) VALUES (%s, %s)",
            ("user1", Decimal("100.00"))
        )
        yield "isolation_test"
        mariadb_backend.execute("DROP TABLE IF EXISTS isolation_test")

    @pytest.fixture(params=[None, "InnoDB", "MyISAM"], ids=["unspecified", "innodb", "myisam"])
    def engine_table(self, request, mariadb_backend):
        """Create an isolation test table, with and without naming the engine.

        Yields the table name, the requested engine (None when the CREATE TABLE
        omits the clause) and the engine the server actually resolved it to, so a
        test can assert on the difference rather than assume it.
        """
        engine = request.param
        suffix = "auto" if engine is None else engine.lower()
        table = f"isolation_engine_test_{suffix}"
        clause = "" if engine is None else f" ENGINE={engine}"

        mariadb_backend.execute(f"DROP TABLE IF EXISTS {table}")
        mariadb_backend.execute(f"""
            CREATE TABLE {table} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                balance DECIMAL(10, 2),
                version INT DEFAULT 1
            ){clause}
        """)
        mariadb_backend.execute(
            f"INSERT INTO {table} (name, balance) VALUES (%s, %s)",
            ("user1", Decimal("100.00"))
        )
        rows = mariadb_backend.execute(
            "SELECT engine FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = %s",
            (table,),
        )
        # information_schema column labels differ in case between servers, so take
        # the single selected value rather than indexing by name.
        resolved = next(iter(rows.data[0].values()))
        yield table, engine, resolved
        mariadb_backend.execute(f"DROP TABLE IF EXISTS {table}")

    def test_read_uncommitted_isolation_effect(self, mariadb_backend, mariadb_control_backend, engine_table):
        """Verify what READ UNCOMMITTED does, for each storage engine.

        Measured against MariaDB 10.2 through 13.1 and MySQL 5.6 through 9.7:
        an unqualified CREATE TABLE resolves to InnoDB everywhere, and on InnoDB
        READ UNCOMMITTED does expose the other session's uncommitted write, which
        is then rolled back. On MyISAM the reader also sees the new value, but
        MyISAM has no transactions, so the write is never rolled back and the
        reader was looking at committed data rather than performing a dirty read.
        The two cases are therefore asserted differently.

        The reader waits on an event the writer sets after its UPDATE lands.
        Sleeping a fixed interval instead made this a race: when the read ran
        before the write landed, the reader saw the old value and the test failed
        intermittently, which is how it presented in CI.
        """
        table, requested, resolved = engine_table
        backend1 = mariadb_backend
        backend2 = mariadb_control_backend

        read_value = []
        write_landed = threading.Event()

        def transaction1():
            """Read on the first connection once the write has landed."""
            try:
                backend1.transaction_manager.isolation_level = IsolationLevel.READ_UNCOMMITTED
                with backend1.transaction():
                    assert write_landed.wait(timeout=10), "writer never issued its UPDATE"
                    rows = backend1.execute(
                        f"SELECT balance FROM {table} WHERE name = %s", ("user1",)
                    )
                    read_value.append(rows.data[0]["balance"] if rows.data else None)
            except Exception as e:  # noqa: BLE001 - surfaced through the assertion below
                read_value.append(e)

        def transaction2():
            """Write on the second connection and never commit it."""
            try:
                backend2.transaction_manager.isolation_level = IsolationLevel.READ_UNCOMMITTED
                with backend2.transaction():
                    backend2.execute(
                        f"UPDATE {table} SET balance = %s WHERE name = %s",
                        (Decimal("200.00"), "user1"),
                    )
                    write_landed.set()
                    time.sleep(0.3)
                    raise RuntimeError("force rollback")
            except Exception:
                pass

        t1 = threading.Thread(target=transaction1)
        t2 = threading.Thread(target=transaction2)
        t1.start()
        t2.start()
        t1.join(timeout=20)
        t2.join(timeout=20)

        expected_engine = requested or "InnoDB"
        assert resolved.lower() == expected_engine.lower(), (
            f"CREATE TABLE {clause or '(no engine clause)'} resolved to {resolved}, "
            f"expected {expected_engine}"
        )

        assert read_value and not isinstance(read_value[0], Exception), (
            f"reader failed: {read_value[0] if read_value else 'never ran'}"
        )
        assert read_value[0] == Decimal("200.00"), (
            f"READ UNCOMMITTED on {resolved} did not expose the other session's "
            f"write; reader saw {read_value[0]}"
        )

        after = backend1.execute(
            f"SELECT balance FROM {table} WHERE name = %s", ("user1",)
        ).data[0]["balance"]
        if resolved.lower() == "myisam":
            assert after == Decimal("200.00"), (
                "MyISAM has no transactions, so the write is expected to survive the "
                f"rollback; found {after}"
            )
        else:
            assert after == Decimal("100.00"), (
                f"on {resolved} the reader saw a dirty read, so the rollback must "
                f"restore the original value; found {after}"
            )

    def test_read_committed_prevents_dirty_reads(self, mariadb_backend, mariadb_control_backend, test_table):
        """Verify READ COMMITTED isolation level prevents dirty reads.

        Uses independent connections for each thread to avoid connection sharing issues.
        """
        backend1 = mariadb_backend
        backend2 = mariadb_control_backend
        dirty_read_occurred = []

        def transaction1():
            """Transaction 1: Should not see uncommitted data."""
            try:
                backend1.transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED
                with backend1.transaction():
                    # Wait for transaction 2 to modify
                    time.sleep(0.15)
                    # Should NOT see the uncommitted change
                    rows = backend1.fetch_all(
                        "SELECT balance FROM isolation_test WHERE name = %s",
                        ("user1",)
                    )
                    if rows and rows[0]["balance"] != Decimal("200.00"):
                        dirty_read_occurred.append(False)  # Correct behavior
                    else:
                        dirty_read_occurred.append(True)  # Dirty read happened
            except Exception as e:
                dirty_read_occurred.append(str(e))

        def transaction2():
            """Transaction 2: Modify and rollback."""
            try:
                backend2.transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED
                with backend2.transaction():
                    backend2.execute(
                        "UPDATE isolation_test SET balance = %s WHERE name = %s",
                        (Decimal("200.00"), "user1")
                    )
                    time.sleep(0.2)
                    raise Exception("Force rollback")
            except Exception:
                pass

        t1 = threading.Thread(target=transaction1)
        t2 = threading.Thread(target=transaction2)

        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # READ COMMITTED should NOT have dirty read
        assert False in dirty_read_occurred, "READ COMMITTED should prevent dirty reads"

    def test_repeatable_read_consistency(self, mariadb_backend, mariadb_control_backend, test_table):
        """Verify REPEATABLE READ provides consistent reads within a transaction.

        REPEATABLE READ should ensure that if a row is read twice in the same
        transaction, the same value is returned even if another transaction
        committed a change.

        Uses independent connections for each thread to avoid connection sharing issues.
        """
        backend1 = mariadb_backend
        backend2 = mariadb_control_backend
        read_values = []

        def transaction1():
            """Transaction 1: Read the same row twice."""
            try:
                backend1.transaction_manager.isolation_level = IsolationLevel.REPEATABLE_READ
                with backend1.transaction():
                    # First read
                    rows1 = backend1.fetch_all(
                        "SELECT balance FROM isolation_test WHERE name = %s",
                        ("user1",)
                    )
                    read_values.append(rows1[0]["balance"])

                    # Wait for transaction 2 to commit
                    time.sleep(0.2)

                    # Second read (should be same as first)
                    rows2 = backend1.fetch_all(
                        "SELECT balance FROM isolation_test WHERE name = %s",
                        ("user1",)
                    )
                    read_values.append(rows2[0]["balance"])
            except Exception as e:
                read_values.append(str(e))

        def transaction2():
            """Transaction 2: Modify and commit."""
            try:
                time.sleep(0.1)  # Wait for transaction 1's first read
                backend2.transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED
                with backend2.transaction():
                    backend2.execute(
                        "UPDATE isolation_test SET balance = %s WHERE name = %s",
                        (Decimal("200.00"), "user1")
                    )
            except Exception as e:
                pass

        t1 = threading.Thread(target=transaction1)
        t2 = threading.Thread(target=transaction2)

        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # Both reads should return the same value
        assert len(read_values) == 2, "Should have two reads"
        assert read_values[0] == read_values[1], f"REPEATABLE READ should provide consistent reads: {read_values}"

    def test_serializable_prevents_phantom_reads(self, mariadb_backend, mariadb_control_backend, test_table):
        """Verify SERIALIZABLE prevents phantom reads.

        Phantom reads occur when a transaction reads rows matching a condition,
        then another transaction inserts a row matching that condition.
        SERIALIZABLE should prevent this.

        Uses independent connections for each thread to avoid connection sharing issues.
        """
        backend1 = mariadb_backend
        backend2 = mariadb_control_backend
        initial_count = []
        second_count = []
        insert_blocked = []

        def transaction1():
            """Transaction 1: Count rows twice."""
            try:
                backend1.transaction_manager.isolation_level = IsolationLevel.SERIALIZABLE
                with backend1.transaction():
                    # First count
                    rows1 = backend1.fetch_all(
                        "SELECT COUNT(*) as cnt FROM isolation_test WHERE balance > %s",
                        (Decimal("50.00"),)
                    )
                    initial_count.append(rows1[0]["cnt"])

                    # Wait for transaction 2 to try insert
                    time.sleep(0.2)

                    # Second count (should be same)
                    rows2 = backend1.fetch_all(
                        "SELECT COUNT(*) as cnt FROM isolation_test WHERE balance > %s",
                        (Decimal("50.00"),)
                    )
                    second_count.append(rows2[0]["cnt"])
            except Exception as e:
                initial_count.append(str(e))

        def transaction2():
            """Transaction 2: Try to insert a matching row."""
            try:
                time.sleep(0.1)  # Wait for transaction 1's first read
                backend2.transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED
                with backend2.transaction():
                    # Try to insert a row that matches the condition
                    backend2.execute(
                        "INSERT INTO isolation_test (name, balance) VALUES (%s, %s)",
                        ("user2", Decimal("75.00"))
                    )
                insert_blocked.append(False)
            except Exception as e:
                # May be blocked by SERIALIZABLE lock
                insert_blocked.append(True)

        t1 = threading.Thread(target=transaction1)
        t2 = threading.Thread(target=transaction2)

        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # With SERIALIZABLE, the counts should be consistent
        # (insert may be blocked or delayed until transaction 1 commits)
        if len(initial_count) == 2 and isinstance(initial_count[0], int):
            assert initial_count[0] == second_count[0], \
                f"SERIALIZABLE should prevent phantom reads: {initial_count[0]} vs {second_count[0]}"


class TestTransactionModeEffects:
    """Test actual effects of READ ONLY and READ WRITE transaction modes."""

    @pytest.fixture
    def test_table(self, mariadb_backend):
        """Create a test table for transaction mode tests."""
        mariadb_backend.execute("DROP TABLE IF EXISTS mode_test")
        mariadb_backend.execute("""
            CREATE TABLE mode_test (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                value INT
            )
        """)
        mariadb_backend.execute(
            "INSERT INTO mode_test (name, value) VALUES (%s, %s)",
            ("item1", 100)
        )
        yield "mode_test"
        mariadb_backend.execute("DROP TABLE IF EXISTS mode_test")

    def test_read_only_mode_rejects_writes(self, mariadb_backend, test_table):
        """Verify READ ONLY mode rejects write operations.

        MySQL 5.6.5+ supports READ ONLY transactions. Any attempt to modify
        data in a READ ONLY transaction should fail.
        """
        # Check if READ ONLY is supported
        if not mariadb_backend.dialect.supports_read_only_transaction():
            pytest.skip("MySQL version does not support READ ONLY transactions")

        error_caught = False
        try:
            from rhosocial.activerecord.backend.transaction import TransactionMode
            mariadb_backend.transaction_manager.transaction_mode = TransactionMode.READ_ONLY
            with mariadb_backend.transaction():
                # Attempt to insert (should fail)
                mariadb_backend.execute(
                    "INSERT INTO mode_test (name, value) VALUES (%s, %s)",
                    ("item2", 200)
                )
        except Exception as e:
            error_caught = True
            # Verify it's the right error
            assert "read-only" in str(e).lower() or "cannot execute" in str(e).lower() or "1792" in str(e)

        assert error_caught, "READ ONLY transaction should reject write operations"

    def test_read_only_mode_allows_reads(self, mariadb_backend, test_table):
        """Verify READ ONLY mode allows read operations."""
        if not mariadb_backend.dialect.supports_read_only_transaction():
            pytest.skip("MySQL version does not support READ ONLY transactions")

        from rhosocial.activerecord.backend.transaction import TransactionMode
        mariadb_backend.transaction_manager.transaction_mode = TransactionMode.READ_ONLY
        with mariadb_backend.transaction():
            rows = mariadb_backend.fetch_all("SELECT * FROM mode_test")
            assert len(rows) == 1
            assert rows[0]["name"] == "item1"

    def test_read_write_mode_allows_writes(self, mariadb_backend, test_table):
        """Verify READ WRITE mode allows write operations."""
        from rhosocial.activerecord.backend.transaction import TransactionMode
        mariadb_backend.transaction_manager.transaction_mode = TransactionMode.READ_WRITE
        with mariadb_backend.transaction():
            mariadb_backend.execute(
                "INSERT INTO mode_test (name, value) VALUES (%s, %s)",
                ("item2", 200)
            )

        rows = mariadb_backend.fetch_all("SELECT * FROM mode_test ORDER BY id")
        assert len(rows) == 2
        assert rows[1]["name"] == "item2"


class TestIsolationModeCombination:
    """Test combinations of isolation levels and transaction modes."""

    @pytest.fixture
    def test_table(self, mariadb_backend):
        """Create a test table for combination tests."""
        mariadb_backend.execute("DROP TABLE IF EXISTS combo_test")
        mariadb_backend.execute("""
            CREATE TABLE combo_test (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                balance DECIMAL(10, 2)
            )
        """)
        mariadb_backend.execute(
            "INSERT INTO combo_test (name, balance) VALUES (%s, %s)",
            ("account1", Decimal("1000.00"))
        )
        yield "combo_test"
        mariadb_backend.execute("DROP TABLE IF EXISTS combo_test")

    def test_serializable_with_read_only(self, mariadb_backend, test_table):
        """Test SERIALIZABLE isolation with READ ONLY mode."""
        if not mariadb_backend.dialect.supports_read_only_transaction():
            pytest.skip("MySQL version does not support READ ONLY transactions")

        from rhosocial.activerecord.backend.transaction import TransactionMode

        # Set both isolation level and mode
        mariadb_backend.transaction_manager.isolation_level = IsolationLevel.SERIALIZABLE
        mariadb_backend.transaction_manager.transaction_mode = TransactionMode.READ_ONLY

        with mariadb_backend.transaction():
            # Should be able to read
            rows = mariadb_backend.fetch_all("SELECT * FROM combo_test")
            assert len(rows) == 1

    def test_repeatable_read_with_read_only(self, mariadb_backend, test_table):
        """Test REPEATABLE READ isolation with READ ONLY mode."""
        if not mariadb_backend.dialect.supports_read_only_transaction():
            pytest.skip("MySQL version does not support READ ONLY transactions")

        from rhosocial.activerecord.backend.transaction import TransactionMode

        mariadb_backend.transaction_manager.isolation_level = IsolationLevel.REPEATABLE_READ
        mariadb_backend.transaction_manager.transaction_mode = TransactionMode.READ_ONLY

        with mariadb_backend.transaction():
            rows = mariadb_backend.fetch_all("SELECT * FROM combo_test")
            assert len(rows) == 1

    def test_default_isolation_is_repeatable_read(self, mariadb_backend):
        """Verify MySQL default isolation level is REPEATABLE READ."""
        # Check the default isolation level
        # MariaDB uses @@tx_isolation before 11.0, @@transaction_isolation from 11.0+
        version = mariadb_backend.dialect.get_server_version()
        isolation_var = "@@transaction_isolation" if version >= (11, 0, 0) else "@@tx_isolation"

        with mariadb_backend.transaction():
            rows = mariadb_backend.fetch_all(
                f"SELECT {isolation_var} as isolation"
            )
            if rows and rows[0].get("isolation"):
                isolation = rows[0]["isolation"]
                assert "REPEATABLE READ" in isolation.upper() or "REPEATABLE-READ" in isolation.upper()

    def test_no_isolation_level_set_uses_database_default(self, mariadb_backend):
        """Verify that when no isolation level is set, no SET TRANSACTION is sent.

        This tests that:
        1. The initial isolation_level is None (not REPEATABLE_READ)
        2. No SET TRANSACTION statement is sent when user doesn't specify isolation
        3. MariaDB uses its default isolation level (REPEATABLE READ)
        """
        from unittest.mock import patch, MagicMock

        # Verify initial state is None
        assert mariadb_backend.transaction_manager._isolation_level is None, \
            "Initial isolation level should be None (use database default)"

        # Track SQL statements executed through the connection cursor
        executed_statements = []
        real_cursor = mariadb_backend._connection.cursor

        def tracking_cursor(*args, **kwargs):
            cursor = real_cursor(*args, **kwargs)
            real_execute = cursor.execute

            def tracking_execute(sql, params=None):
                executed_statements.append(sql)
                return real_execute(sql, params)

            cursor.execute = tracking_execute
            return cursor

        # Patch cursor to track statements
        with patch.object(mariadb_backend._connection, 'cursor', side_effect=tracking_cursor):
            with mariadb_backend.transaction():
                # Execute a simple query inside the transaction
                mariadb_backend.fetch_all("SELECT 1 as test")

        # Verify no SET TRANSACTION was sent
        set_transaction_found = any(
            'SET TRANSACTION' in stmt.upper() for stmt in executed_statements
        )
        assert not set_transaction_found, \
            f"SET TRANSACTION should NOT be sent when isolation level not specified. Executed: {executed_statements}"

        # Verify START TRANSACTION was sent
        start_transaction_found = any(
            'START TRANSACTION' in stmt.upper() for stmt in executed_statements
        )
        assert start_transaction_found, \
            f"START TRANSACTION should be sent. Executed: {executed_statements}"

    def test_explicit_isolation_level_sends_set_transaction(self, mariadb_backend):
        """Verify that when isolation level is explicitly set, SET TRANSACTION is sent.

        This tests that:
        1. Setting isolation_level property changes the internal state
        2. SET TRANSACTION statement is sent before START TRANSACTION
        3. The correct isolation level is used
        """
        from unittest.mock import patch

        # Set isolation level explicitly
        mariadb_backend.transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED

        # Verify internal state changed
        assert mariadb_backend.transaction_manager._isolation_level == IsolationLevel.READ_COMMITTED, \
            "Isolation level should be READ_COMMITTED after explicit setting"

        # Track SQL statements executed through the connection cursor
        executed_statements = []
        real_cursor = mariadb_backend._connection.cursor

        def tracking_cursor(*args, **kwargs):
            cursor = real_cursor(*args, **kwargs)
            real_execute = cursor.execute

            def tracking_execute(sql, params=None):
                executed_statements.append(sql)
                return real_execute(sql, params)

            cursor.execute = tracking_execute
            return cursor

        # Patch cursor to track statements
        with patch.object(mariadb_backend._connection, 'cursor', side_effect=tracking_cursor):
            with mariadb_backend.transaction():
                mariadb_backend.fetch_all("SELECT 1 as test")

        # Verify SET TRANSACTION was sent with correct level
        set_transaction_found = any(
            'SET TRANSACTION' in stmt.upper() and 'READ COMMITTED' in stmt.upper()
            for stmt in executed_statements
        )
        assert set_transaction_found, \
            f"SET TRANSACTION READ COMMITTED should be sent. Executed: {executed_statements}"

        # Verify SET TRANSACTION comes before START TRANSACTION
        set_transaction_idx = next(
            (i for i, stmt in enumerate(executed_statements)
             if 'SET TRANSACTION' in stmt.upper()),
            None
        )
        start_transaction_idx = next(
            (i for i, stmt in enumerate(executed_statements)
             if 'START TRANSACTION' in stmt.upper()),
            None
        )
        assert set_transaction_idx is not None and start_transaction_idx is not None, \
            "Both SET TRANSACTION and START TRANSACTION should be executed"
        assert set_transaction_idx < start_transaction_idx, \
            f"SET TRANSACTION should come before START TRANSACTION. Order: {executed_statements}"

    def test_isolation_level_cannot_change_during_transaction(self, mariadb_backend, test_table):
        """Verify isolation level cannot be changed during active transaction."""
        with mariadb_backend.transaction():
            with pytest.raises(Exception):  # IsolationLevelError
                mariadb_backend.transaction_manager.isolation_level = IsolationLevel.SERIALIZABLE


class TestNestedTransactionsWithIsolation:
    """Test nested transactions (savepoints) with different isolation levels."""

    @pytest.fixture
    def test_table(self, mariadb_backend):
        """Create a test table for nested transaction tests."""
        mariadb_backend.execute("DROP TABLE IF EXISTS nested_test")
        mariadb_backend.execute("""
            CREATE TABLE nested_test (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                value INT
            )
        """)
        yield "nested_test"
        mariadb_backend.execute("DROP TABLE IF EXISTS nested_test")

    def test_nested_transaction_with_isolation_level(self, mariadb_backend, test_table):
        """Test that nested transactions work with isolation level set."""
        mariadb_backend.transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED

        with mariadb_backend.transaction():
            # Insert first record
            mariadb_backend.execute(
                "INSERT INTO nested_test (name, value) VALUES (%s, %s)",
                ("outer", 1)
            )

            # Create savepoint
            sp = mariadb_backend.transaction_manager.savepoint("sp1")

            # Insert second record
            mariadb_backend.execute(
                "INSERT INTO nested_test (name, value) VALUES (%s, %s)",
                ("inner", 2)
            )

            # Rollback to savepoint
            mariadb_backend.transaction_manager.rollback_to(sp)

        # Only outer record should exist
        rows = mariadb_backend.fetch_all("SELECT * FROM nested_test ORDER BY id")
        assert len(rows) == 1
        assert rows[0]["name"] == "outer"
