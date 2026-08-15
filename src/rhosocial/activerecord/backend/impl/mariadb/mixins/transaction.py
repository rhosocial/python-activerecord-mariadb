# src/rhosocial/activerecord/backend/impl/mariadb/mixins/transaction.py
"""MariaDB transaction mixin.

Provides transaction isolation level management for MariaDB,
which follows MySQL's transaction model.
"""
import logging
from typing import Dict, Optional

from rhosocial.activerecord.backend.errors import TransactionError
from rhosocial.activerecord.backend.transaction import IsolationLevel, IsolationLevelError


class MariaDBTransactionMixin:
    """MariaDB transaction common functionality.

    Provides shared isolation level management for both sync and async
    MariaDB transaction managers.

    MariaDB supports the same isolation levels as MySQL:
    - READ UNCOMMITTED
    - READ COMMITTED
    - REPEATABLE READ (default)
    - SERIALIZABLE

    MariaDB-specific extensions:
    - START TRANSACTION READ ONLY (since 10.0)
    - WAIT timeout for lock waits (since 10.3)
    """

    _ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
        IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
    }

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set transaction isolation level.

        Args:
            level: The isolation level to set.

        Raises:
            IsolationLevelError: If trying to change during active transaction.
            TransactionError: If unsupported isolation level.
        """
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")

        if level is not None and level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        self._isolation_level = level

    def format_set_isolation_level(self, level: IsolationLevel) -> str:
        """Format SET TRANSACTION ISOLATION LEVEL statement.

        Args:
            level: The isolation level to set.

        Returns:
            SQL statement string.
        """
        level_name = self._ISOLATION_LEVELS.get(level)
        if not level_name:
            raise TransactionError(f"Unsupported isolation level: {level}")
        return f"SET TRANSACTION ISOLATION LEVEL {level_name}"

    def format_start_transaction(
        self,
        read_only: bool = False,
        isolation_level: Optional[IsolationLevel] = None
    ) -> str:
        """Format START TRANSACTION statement.

        MariaDB 10.0+ supports READ ONLY transactions.

        Args:
            read_only: If True, start a read-only transaction.
            isolation_level: Optional isolation level to set.

        Returns:
            SQL statement string.
        """
        if read_only:
            return "START TRANSACTION READ ONLY"
        return "START TRANSACTION"

    def supports_read_only_transaction(self) -> bool:
        """Whether READ ONLY transactions are supported.

        MariaDB 10.0+ supports START TRANSACTION READ ONLY.

        Returns:
            True if supported.
        """
        return True

    def supports_savepoint(self) -> bool:
        """Whether savepoints are supported.

        MariaDB supports savepoints in all versions.

        Returns:
            True (always supported).
        """
        return True


__all__ = ['MariaDBTransactionMixin']
