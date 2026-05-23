# tests/rhosocial/activerecord_mariadb_test/feature/backend/expression/test_expressions_transaction.py
"""Tests for MariaDB transaction expression classes.

MariaDB Transaction Behavior:
- Isolation level must be set BEFORE START TRANSACTION using SET TRANSACTION
- START TRANSACTION can include READ ONLY / READ WRITE modes
- The dialect's format_begin_transaction() only returns START TRANSACTION
- SetTransactionExpression is used for isolation level settings
"""
import pytest
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionExpression,
    CommitTransactionExpression,
    RollbackTransactionExpression,
    SavepointExpression,
    ReleaseSavepointExpression,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode


class TestMariaDBBeginTransactionExpression:
    """Tests for MariaDB BeginTransactionExpression."""

    def test_basic_begin(self, mariadb_dialect):
        """Test basic START TRANSACTION."""
        expr = BeginTransactionExpression(mariadb_dialect)
        sql, params = expr.to_sql()
        assert sql == "START TRANSACTION"
        assert params == ()

    def test_begin_with_isolation_level_returns_only_start(self, mariadb_dialect):
        """Test that isolation level is set via SET TRANSACTION before START TRANSACTION."""
        expr = BeginTransactionExpression(mariadb_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert "SET TRANSACTION ISOLATION LEVEL" in sql
        assert "START TRANSACTION" in sql
        assert params == ()
        assert mariadb_dialect.supports_isolation_level_in_begin() == False

    def test_begin_read_only(self, mariadb_dialect):
        """Test START TRANSACTION READ ONLY."""
        expr = BeginTransactionExpression(mariadb_dialect)
        expr.read_only()
        sql, params = expr.to_sql()
        assert sql == "START TRANSACTION READ ONLY"
        assert params == ()

    @pytest.mark.parametrize("level", [
        IsolationLevel.READ_UNCOMMITTED,
        IsolationLevel.READ_COMMITTED,
        IsolationLevel.REPEATABLE_READ,
        IsolationLevel.SERIALIZABLE,
    ])
    def test_begin_with_isolation_returns_start_transaction(self, mariadb_dialect, level):
        """Test that isolation level is set via SET TRANSACTION before START TRANSACTION."""
        expr = BeginTransactionExpression(mariadb_dialect)
        expr.isolation_level(level)
        sql, params = expr.to_sql()
        assert "SET TRANSACTION ISOLATION LEVEL" in sql
        assert "START TRANSACTION" in sql
        assert params == ()


class TestMariaDBSetTransactionExpression:
    """Tests for MariaDB SetTransactionExpression."""

    def test_set_isolation_level(self, mariadb_dialect):
        """Test SET TRANSACTION ISOLATION LEVEL."""
        expr = SetTransactionExpression(mariadb_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert sql == "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"
        assert params == ()

    @pytest.mark.parametrize("level,expected_name", [
        (IsolationLevel.READ_UNCOMMITTED, "READ UNCOMMITTED"),
        (IsolationLevel.READ_COMMITTED, "READ COMMITTED"),
        (IsolationLevel.REPEATABLE_READ, "REPEATABLE READ"),
        (IsolationLevel.SERIALIZABLE, "SERIALIZABLE"),
    ])
    def test_all_isolation_levels(self, mariadb_dialect, level, expected_name):
        """Test all isolation levels in SET TRANSACTION."""
        expr = SetTransactionExpression(mariadb_dialect)
        expr.isolation_level(level)
        sql, params = expr.to_sql()
        assert expected_name in sql
        assert params == ()

    def test_set_read_only(self, mariadb_dialect):
        """Test SET TRANSACTION READ ONLY."""
        expr = SetTransactionExpression(mariadb_dialect)
        expr.read_only()
        sql, params = expr.to_sql()
        assert sql == "SET TRANSACTION READ ONLY"
        assert params == ()

    def test_set_read_write(self, mariadb_dialect):
        """Test SET TRANSACTION READ WRITE."""
        expr = SetTransactionExpression(mariadb_dialect)
        expr.read_write()
        sql, params = expr.to_sql()
        assert sql == "SET TRANSACTION READ WRITE"
        assert params == ()


class TestMariaDBCommitRollback:
    """Tests for MariaDB COMMIT and ROLLBACK."""

    def test_commit(self, mariadb_dialect):
        """Test COMMIT statement."""
        expr = CommitTransactionExpression(mariadb_dialect)
        sql, params = expr.to_sql()
        assert sql == "COMMIT"
        assert params == ()

    def test_rollback(self, mariadb_dialect):
        """Test ROLLBACK statement."""
        expr = RollbackTransactionExpression(mariadb_dialect)
        sql, params = expr.to_sql()
        assert sql == "ROLLBACK"
        assert params == ()

    def test_rollback_to_savepoint(self, mariadb_dialect):
        """Test ROLLBACK TO SAVEPOINT statement."""
        expr = RollbackTransactionExpression(mariadb_dialect)
        expr.to_savepoint("my_savepoint")
        sql, params = expr.to_sql()
        assert "ROLLBACK" in sql
        assert "SAVEPOINT" in sql
        assert params == ()


class TestMariaDBSavepoint:
    """Tests for MariaDB SAVEPOINT operations."""

    def test_savepoint(self, mariadb_dialect):
        """Test SAVEPOINT statement."""
        expr = SavepointExpression(mariadb_dialect, "my_savepoint")
        sql, params = expr.to_sql()
        assert "SAVEPOINT" in sql
        assert "my_savepoint" in sql
        assert params == ()

    def test_release_savepoint(self, mariadb_dialect):
        """Test RELEASE SAVEPOINT statement."""
        expr = ReleaseSavepointExpression(mariadb_dialect, "my_savepoint")
        sql, params = expr.to_sql()
        assert "RELEASE SAVEPOINT" in sql
        assert "my_savepoint" in sql
        assert params == ()


class TestMariaDBTransactionCapabilities:
    """Tests for MariaDB transaction capabilities."""

    def test_supports_transaction_mode(self, mariadb_dialect):
        """Test MariaDB supports transaction mode."""
        assert mariadb_dialect.supports_transaction_mode() == True

    def test_supports_isolation_level_in_begin(self, mariadb_dialect):
        """Test MariaDB does not support isolation level in BEGIN."""
        assert mariadb_dialect.supports_isolation_level_in_begin() == False

    def test_supports_read_only_transaction(self, mariadb_dialect):
        """Test MariaDB supports READ ONLY transactions."""
        assert mariadb_dialect.supports_read_only_transaction() == True

    def test_supports_deferrable_transaction(self, mariadb_dialect):
        """Test MariaDB does not support DEFERRABLE transactions."""
        assert mariadb_dialect.supports_deferrable_transaction() == False

    def test_supports_savepoint(self, mariadb_dialect):
        """Test MariaDB supports savepoints."""
        assert mariadb_dialect.supports_savepoint() == True
