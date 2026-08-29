# src/rhosocial/activerecord/backend/impl/mariadb/async_transaction.py
"""Async MariaDB transaction management."""

import logging
from typing import Optional

from rhosocial.activerecord.backend.transaction import (
    AsyncTransactionManager,
    IsolationLevel,
    TransactionState,
    TransactionMode,
)
from rhosocial.activerecord.backend.errors import TransactionError

from .transaction import MariaDBTransactionMixin


class AsyncMariaDBTransactionManager(MariaDBTransactionMixin, AsyncTransactionManager):
    """Async MariaDB transaction manager implementation."""

    def __init__(self, backend, logger=None):
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

    @property
    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self._transaction_level > 0 and self._state == TransactionState.ACTIVE

    async def _do_begin(self) -> None:
        """Begin MariaDB transaction.

        If an isolation level is explicitly set, sends SET TRANSACTION ISOLATION LEVEL
        before START TRANSACTION. If transaction mode is set (READ ONLY/READ WRITE),
        includes it in the START TRANSACTION statement.

        Uses cursor directly to avoid auto-commit logic in backend.execute().
        """
        cursor = self._backend._connection.cursor()
        # Set isolation level if explicitly configured
        if self._isolation_level is not None:
            level_name = self._ISOLATION_LEVELS.get(self._isolation_level)
            if level_name:
                set_sql = f"SET TRANSACTION ISOLATION LEVEL {level_name}"
                self.log(logging.DEBUG, f"Executing: {set_sql}")
                await cursor.execute(set_sql)

        # Build START TRANSACTION with optional mode
        if self._transaction_mode == TransactionMode.READ_ONLY:
            begin_sql = "START TRANSACTION READ ONLY"
        elif self._transaction_mode == TransactionMode.READ_WRITE:
            begin_sql = "START TRANSACTION READ WRITE"
        else:
            begin_sql = "START TRANSACTION"

        self.log(logging.DEBUG, f"Executing: {begin_sql}")
        await cursor.execute(begin_sql)
        await cursor.close()
        self._state = TransactionState.ACTIVE

    async def _do_commit(self) -> None:
        """Commit MariaDB transaction."""
        sql = "COMMIT"
        self.log(logging.DEBUG, f"Executing: {sql}")
        cursor = self._backend._connection.cursor()
        await cursor.execute(sql)
        await cursor.close()
        self._state = TransactionState.COMMITTED

    async def _do_rollback(self) -> None:
        """Rollback MariaDB transaction."""
        sql = "ROLLBACK"
        self.log(logging.DEBUG, f"Executing: {sql}")
        cursor = self._backend._connection.cursor()
        await cursor.execute(sql)
        await cursor.close()
        self._state = TransactionState.ROLLED_BACK

    async def _do_create_savepoint(self, name: str) -> None:
        """Create MariaDB savepoint."""
        try:
            escaped_name = self._backend.dialect.format_identifier(name)
            sql = f"SAVEPOINT {escaped_name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            cursor = self._backend._connection.cursor()
            await cursor.execute(sql)
            await cursor.close()
        except Exception as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def _do_release_savepoint(self, name: str) -> None:
        """Release MariaDB savepoint."""
        try:
            escaped_name = self._backend.dialect.format_identifier(name)
            sql = f"RELEASE SAVEPOINT {escaped_name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            cursor = self._backend._connection.cursor()
            await cursor.execute(sql)
            await cursor.close()
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to MariaDB savepoint."""
        try:
            escaped_name = self._backend.dialect.format_identifier(name)
            sql = f"ROLLBACK TO SAVEPOINT {escaped_name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            cursor = self._backend._connection.cursor()
            await cursor.execute(sql)
            await cursor.close()
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e
