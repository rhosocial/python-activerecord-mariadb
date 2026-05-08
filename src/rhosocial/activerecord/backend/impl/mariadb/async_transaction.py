# src/rhosocial/activerecord/backend/impl/mariadb/async_transaction.py
"""Async MariaDB transaction management."""

import logging
from typing import Optional

from rhosocial.activerecord.backend.transaction import AsyncTransactionManager, IsolationLevel, TransactionState
from rhosocial.activerecord.backend.errors import TransactionError


class AsyncMariaDBTransactionManager(AsyncTransactionManager):
    """Async MariaDB transaction manager implementation."""

    def __init__(self, backend, logger=None):
        super().__init__(backend, logger)
        self._isolation_level = IsolationLevel.REPEATABLE_READ
        self._state = TransactionState.INACTIVE

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            raise TransactionError("Cannot change isolation level during active transaction")
        if level not in (IsolationLevel.READ_UNCOMMITTED, IsolationLevel.READ_COMMITTED,
                         IsolationLevel.REPEATABLE_READ, IsolationLevel.SERIALIZABLE):
            raise TransactionError(f"Unsupported isolation level: {level}")
        self._isolation_level = level

    @property
    def is_active(self) -> bool:
        return self._transaction_level > 0 and self._state == TransactionState.ACTIVE

    def supports_savepoint(self) -> bool:
        return True