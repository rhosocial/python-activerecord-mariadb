# src/rhosocial/activerecord/backend/impl/mariadb/async_transaction.py
"""Async MariaDB transaction management."""

import logging
from typing import Optional

from rhosocial.activerecord.backend.transaction import AsyncTransactionManager, IsolationLevel, TransactionState
from rhosocial.activerecord.backend.errors import TransactionError


_ISOLATION_LEVELS = {
    IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
    IsolationLevel.READ_COMMITTED: "READ COMMITTED",
    IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
    IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
}


class AsyncMariaDBTransactionManager(AsyncTransactionManager):
    """Async MariaDB transaction manager implementation."""

    def __init__(self, connection, logger=None):
        """Initialize async MariaDB transaction manager.

        Args:
            connection: MariaDB database connection
            logger: Optional logger instance
        """
        super().__init__(connection, logger)
        self._isolation_level = IsolationLevel.REPEATABLE_READ
        self._state = TransactionState.INACTIVE

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get the current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set the transaction isolation level."""
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            raise TransactionError("Cannot change isolation level during active transaction")
        if level not in _ISOLATION_LEVELS:
            raise TransactionError(f"Unsupported isolation level: {level}")
        self._isolation_level = level

    async def _do_begin(self) -> None:
        """Begin MariaDB transaction asynchronously."""
        level_name = _ISOLATION_LEVELS.get(self._isolation_level, "REPEATABLE READ")

        isolation_sql = f"SET TRANSACTION ISOLATION LEVEL {level_name}"
        self.log(logging.DEBUG, f"Executing: {isolation_sql}")
        await self.connection.execute(isolation_sql)

        begin_sql = "BEGIN"
        self.log(logging.DEBUG, f"Executing: {begin_sql}")
        await self.connection.execute(begin_sql)
        self._state = TransactionState.ACTIVE

    async def _do_commit(self) -> None:
        """Commit MariaDB transaction asynchronously."""
        sql = "COMMIT"
        self.log(logging.DEBUG, f"Executing: {sql}")
        await self.connection.execute(sql)
        self._state = TransactionState.COMMITTED

    async def _do_rollback(self) -> None:
        """Rollback MariaDB transaction asynchronously."""
        sql = "ROLLBACK"
        self.log(logging.DEBUG, f"Executing: {sql}")
        await self.connection.execute(sql)
        self._state = TransactionState.ROLLED_BACK

    async def _do_create_savepoint(self, name: str) -> None:
        """Create MariaDB savepoint asynchronously."""
        try:
            sql = f"SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            await self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def _do_release_savepoint(self, name: str) -> None:
        """Release MariaDB savepoint asynchronously."""
        try:
            sql = f"RELEASE SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            await self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to MariaDB savepoint asynchronously."""
        try:
            sql = f"ROLLBACK TO SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            await self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    @property
    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self._transaction_level > 0 and self._state == TransactionState.ACTIVE

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported."""
        return True
