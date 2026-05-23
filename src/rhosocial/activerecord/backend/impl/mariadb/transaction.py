# src/rhosocial/activerecord/backend/impl/mariadb/transaction.py
"""MariaDB transaction management."""

import logging
from typing import Dict, Optional

from rhosocial.activerecord.backend.transaction import TransactionManager, IsolationLevel, TransactionState, TransactionMode
from rhosocial.activerecord.backend.errors import TransactionError


_ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
    IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
    IsolationLevel.READ_COMMITTED: "READ COMMITTED",
    IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
    IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
}


class MariaDBTransactionMixin:
    """Mixin providing common MariaDB transaction functionality."""

    _ISOLATION_LEVELS = _ISOLATION_LEVELS
    _isolation_level: IsolationLevel
    _logger: logging.Logger

    def _get_savepoint_name(self, level: int) -> str:
        """Generate savepoint name for nested transactions.

        Args:
            level: The nesting level of the transaction.

        Returns:
            A savepoint name string.
        """
        return f"SP_{level}"

    def _validate_isolation_level(self, level: IsolationLevel) -> None:
        """Validate that the isolation level is supported by MariaDB.

        Args:
            level: The isolation level to validate.

        Raises:
            TransactionError: If the isolation level is not supported.
        """
        if level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            if hasattr(self, "log"):
                self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _check_no_active_transaction(self) -> None:
        """Check that no transaction is active before changing isolation level.

        Raises:
            TransactionError: If a transaction is currently active.
        """
        if self.is_active:
            error_msg = "Cannot change isolation level during active transaction"
            if hasattr(self, "log"):
                self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported by MariaDB.

        Returns:
            True, as MariaDB always supports savepoints.
        """
        return True


class MariaDBTransactionManager(MariaDBTransactionMixin, TransactionManager):
    """MariaDB transaction manager implementation."""

    def __init__(self, backend, logger=None):
        """Initialize MariaDB transaction manager.

        Args:
            backend: MariaDB backend instance
            logger: Optional logger instance
        """
        super().__init__(backend, logger)
        self._isolation_level = None
        self._transaction_mode = None
        self._state = TransactionState.INACTIVE

    @property
    def connection(self):
        """Get the raw database connection from the backend."""
        return self._backend._connection

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get the current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set the transaction isolation level."""
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        self._check_no_active_transaction()
        self._validate_isolation_level(level)
        self._isolation_level = level

    def _do_begin(self) -> None:
        """Begin MariaDB transaction.

        If an isolation level is explicitly set, sends SET TRANSACTION ISOLATION LEVEL
        before START TRANSACTION. If transaction mode is set (READ ONLY/READ WRITE),
        includes it in the START TRANSACTION statement.
        MariaDB defaults to REPEATABLE READ when no level is set.
        """
        cursor = self.connection.cursor()
        # Set isolation level if explicitly configured
        if self._isolation_level is not None:
            level_name = self._ISOLATION_LEVELS.get(self._isolation_level)
            if level_name:
                set_sql = f"SET TRANSACTION ISOLATION LEVEL {level_name}"
                self.log(logging.DEBUG, f"Executing: {set_sql}")
                cursor.execute(set_sql)

        # Build START TRANSACTION with optional READ ONLY/READ WRITE
        if self._transaction_mode == TransactionMode.READ_ONLY:
            begin_sql = "START TRANSACTION READ ONLY"
        elif self._transaction_mode == TransactionMode.READ_WRITE:
            begin_sql = "START TRANSACTION READ WRITE"
        else:
            begin_sql = "START TRANSACTION"

        self.log(logging.DEBUG, f"Executing: {begin_sql}")
        cursor.execute(begin_sql)
        cursor.close()
        self._state = TransactionState.ACTIVE

    def _do_commit(self) -> None:
        """Commit MariaDB transaction."""
        sql = "COMMIT"
        self.log(logging.DEBUG, f"Executing: {sql}")
        cursor = self.connection.cursor()
        cursor.execute(sql)
        cursor.close()
        self._state = TransactionState.COMMITTED

    def _do_rollback(self) -> None:
        """Rollback MariaDB transaction."""
        sql = "ROLLBACK"
        self.log(logging.DEBUG, f"Executing: {sql}")
        cursor = self.connection.cursor()
        cursor.execute(sql)
        cursor.close()
        self._state = TransactionState.ROLLED_BACK

    def _do_create_savepoint(self, name: str) -> None:
        """Create MariaDB savepoint."""
        try:
            sql = f"SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            cursor = self.connection.cursor()
            cursor.execute(sql)
            cursor.close()
        except Exception as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def _do_release_savepoint(self, name: str) -> None:
        """Release MariaDB savepoint."""
        try:
            sql = f"RELEASE SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            cursor = self.connection.cursor()
            cursor.execute(sql)
            cursor.close()
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to MariaDB savepoint."""
        try:
            sql = f"ROLLBACK TO SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            cursor = self.connection.cursor()
            cursor.execute(sql)
            cursor.close()
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    @property
    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self._transaction_level > 0 and self._state == TransactionState.ACTIVE
