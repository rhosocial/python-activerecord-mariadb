import logging
from typing import Dict, Optional
from mariadb import Error as MariaDBError

from ...errors import TransactionError
from ...transaction import TransactionManager, IsolationLevel, TransactionState


class MariaDBTransactionManager(TransactionManager):
    """MariaDB transaction manager implementation"""

    # MariaDB supported isolation level mappings
    _ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",  # MariaDB default
        IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
    }

    def __init__(self, connection, logger=None):
        """Initialize MariaDB transaction manager

        Args:
            connection: MariaDB database connection
            logger: Optional logger instance
        """
        super().__init__(connection, logger)
        self._active_savepoint = None
        self._savepoint_counter = 0
        self._state = TransactionState.INACTIVE

    def _set_isolation_level(self) -> None:
        """Set transaction isolation level

        This is called at the start of each transaction
        """
        if self._isolation_level:
            level = self._ISOLATION_LEVELS.get(self._isolation_level)
            if level:
                try:
                    self.log(logging.DEBUG, f"Setting isolation level to {level}")
                    cursor = self._connection.cursor()
                    cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {level}")
                    cursor.close()
                except MariaDBError as e:
                    error_msg = f"Failed to set isolation level to {level}: {str(e)}"
                    self.log(logging.ERROR, error_msg)
                    raise TransactionError(error_msg)
            else:
                error_msg = f"Unsupported isolation level: {self._isolation_level}"
                self.log(logging.ERROR, error_msg)
                raise TransactionError(error_msg)

    def _do_begin(self) -> None:
        """Begin MariaDB transaction

        Sets isolation level and starts transaction

        Raises:
            TransactionError: If begin fails
        """
        try:
            # Set isolation level first
            self._set_isolation_level()

            # Start transaction
            # MariaDB connector doesn't have start_transaction method
            # Instead, we need to execute BEGIN
            cursor = self._connection.cursor()
            self.log(logging.DEBUG, "Executing: BEGIN")
            cursor.execute("BEGIN")
            cursor.close()
            self._state = TransactionState.ACTIVE
            self.log(logging.INFO, f"Started transaction with isolation level {self._isolation_level}")

        except MariaDBError as e:
            error_msg = f"Failed to begin transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_commit(self) -> None:
        """Commit MariaDB transaction

        Raises:
            TransactionError: If commit fails
        """
        try:
            self.log(logging.DEBUG, "Committing transaction")
            self._connection.commit()
            self._state = TransactionState.COMMITTED
            self.log(logging.INFO, "Transaction committed")
        except MariaDBError as e:
            error_msg = f"Failed to commit transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)
        finally:
            self._active_savepoint = None
            self._savepoint_counter = 0

    def _do_rollback(self) -> None:
        """Rollback MariaDB transaction

        Raises:
            TransactionError: If rollback fails
        """
        try:
            self.log(logging.DEBUG, "Rolling back transaction")
            self._connection.rollback()
            self._state = TransactionState.ROLLED_BACK
            self.log(logging.INFO, "Transaction rolled back")
        except MariaDBError as e:
            error_msg = f"Failed to rollback transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)
        finally:
            self._active_savepoint = None
            self._savepoint_counter = 0

    def _get_savepoint_name(self, level: int) -> str:
        """Generate savepoint name for nested transactions

        Args:
            level: Transaction nesting level

        Returns:
            str: Savepoint name
        """
        return f"SP_{level}"

    def _do_create_savepoint(self, name: str) -> None:
        """Create MariaDB savepoint

        Args:
            name: Savepoint name

        Raises:
            TransactionError: If create savepoint fails
        """
        try:
            cursor = self._connection.cursor()
            sql = f"SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            cursor.execute(sql)
            cursor.close()
            self._active_savepoint = name
            self.log(logging.INFO, f"Created savepoint: {name}")
        except MariaDBError as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_release_savepoint(self, name: str) -> None:
        """Release MariaDB savepoint

        Args:
            name: Savepoint name

        Raises:
            TransactionError: If release savepoint fails
        """
        try:
            cursor = self._connection.cursor()
            sql = f"RELEASE SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            cursor.execute(sql)
            cursor.close()
            if self._active_savepoint == name:
                self._active_savepoint = None
            self.log(logging.INFO, f"Released savepoint: {name}")
        except MariaDBError as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to MariaDB savepoint

        Args:
            name: Savepoint name

        Raises:
            TransactionError: If rollback to savepoint fails
        """
        try:
            cursor = self._connection.cursor()
            sql = f"ROLLBACK TO SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            cursor.execute(sql)
            cursor.close()
            if self._active_savepoint == name:
                self._active_savepoint = None
            self.log(logging.INFO, f"Rolled back to savepoint: {name}")
        except MariaDBError as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported

        Returns:
            bool: Always True for MariaDB
        """
        return True

    @property
    def is_active(self) -> bool:
        """Check if transaction is active

        Returns:
            bool: True if in transaction
        """
        # For MariaDB we check transaction level and state
        is_active = self._transaction_level > 0 and self._state == TransactionState.ACTIVE
        return is_active

    def get_active_savepoint(self) -> Optional[str]:
        """Get name of active savepoint

        Returns:
            Optional[str]: Active savepoint name or None
        """
        return self._active_savepoint