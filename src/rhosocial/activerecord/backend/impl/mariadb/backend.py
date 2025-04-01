import logging
import time
from typing import Optional, Tuple, List, Dict, Union, Any

import mariadb
from mariadb import Error as MariaDBError, IntegrityError as MariaDBIntegrityError, ProgrammingError, \
    OperationalError as MariaDBOperationalError, DatabaseError as MariaDBDatabaseError

from .dialect import MariaDBDialect, SQLDialectBase, MariaDBSQLBuilder
from .transaction import MariaDBTransactionManager
from ...base import StorageBackend, ColumnTypes
from ...errors import (
    ConnectionError,
    IntegrityError,
    OperationalError,
    QueryError,
    DeadlockError,
    DatabaseError,
    ReturningNotSupportedError,
    JsonOperationNotSupportedError
)
from ...typing import QueryResult, ConnectionConfig


class MariaDBBackend(StorageBackend):
    """MariaDB storage backend implementation"""

    def __init__(self, **kwargs):
        """Initialize MariaDB backend

        Args:
            **kwargs: Configuration parameters including:
                - connection_config: ConnectionConfig instance
                - logger: Optional logger instance
                - pool_size: Connection pool size
                - pool_name: Pool name for identification
                - Other standard MariaDB connection parameters
        """
        super().__init__(**kwargs)
        self._cursor = None
        self._pool = None
        self._transaction_manager = None
        self._server_version_cache = None

        # Configure MariaDB specific settings
        if isinstance(self.config, ConnectionConfig):
            self._connection_args = self._prepare_connection_args(self.config)
        else:
            self._connection_args = kwargs

        self._dialect = MariaDBDialect(self.config)

    def _prepare_connection_args(self, config: ConnectionConfig) -> Dict:
        """Prepare MariaDB connection arguments

        Args:
            config: Connection configuration

        Returns:
            Dict: MariaDB connection arguments
        """
        args = config.to_dict()

        # Map config parameters to MariaDB connector parameters
        param_mapping = {
            'database': 'database',
            'username': 'user',
            'password': 'password',
            'host': 'host',
            'port': 'port',
            'charset': 'charset',
            'ssl_ca': 'ssl_ca',
            'ssl_cert': 'ssl_cert',
            'ssl_key': 'ssl_key',
            'pool_size': 'pool_size',
            'pool_name': 'pool_name'
        }

        connection_args = {}
        for config_key, mariadb_key in param_mapping.items():
            if config_key in args:
                connection_args[mariadb_key] = args[config_key]

        # Add additional options
        connection_args.update({
            'autocommit': False,  # We'll handle transactions explicitly
            'connection_timeout': self.config.pool_timeout
        })

        # MariaDB doesn't support pool directly in the connector, so we'll handle it separately

        return connection_args

    @property
    def dialect(self) -> SQLDialectBase:
        """Get MariaDB dialect"""
        return self._dialect

    def build_sql(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters for MariaDB

        Uses MariaDBSQLBuilder to handle MariaDB-specific parameter placeholders

        Args:
            sql: Raw SQL with ? placeholders
            params: SQL parameters

        Returns:
            Tuple[str, Tuple]: (Processed SQL, Processed parameters)
        """
        builder = MariaDBSQLBuilder(self.dialect)
        return builder.build(sql, params)

    def connect(self) -> None:
        """Establish connection to MariaDB server

        Creates a connection using the MariaDB connector

        Raises:
            ConnectionError: If connection fails
        """
        # Clear version cache on new connection
        self._server_version_cache = None

        try:
            self.log(logging.INFO, f"Connecting to MariaDB server: {self.config.host}:{self.config.port}")

            # Create single connection
            self._connection = mariadb.connect(**self._connection_args)
            self.log(logging.DEBUG, "Created direct connection")

            # Configure session
            cursor = self._connection.cursor()
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
            self.log(logging.DEBUG, "Set transaction isolation level to READ COMMITTED")

            if self.config.timezone:
                cursor.execute(f"SET time_zone = '{self.config.timezone}'")
                self.log(logging.DEBUG, f"Set time_zone to {self.config.timezone}")

            cursor.close()
            self.log(logging.INFO, "Connected to MariaDB successfully")

            # Get server version immediately after connecting
            self.get_server_version()

        except MariaDBError as e:
            error_msg = f"Failed to connect: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise ConnectionError(error_msg)

    def disconnect(self) -> None:
        """Close database connection"""
        # Clear version cache on disconnect
        self._server_version_cache = None

        if self._connection:
            try:
                self.log(logging.INFO, "Disconnecting from MariaDB")
                if self._cursor:
                    self._cursor.close()
                    self._cursor = None

                # Use transaction_manager's is_active property rather than in_transaction
                if self._transaction_manager and self._transaction_manager.is_active:
                    self.log(logging.WARNING, "Active transaction detected during disconnect, rolling back")
                    self._transaction_manager.rollback()

                self._connection.close()
                self.log(logging.INFO, "Disconnected from MariaDB successfully")
            except MariaDBError as e:
                error_msg = f"Error during disconnect: {str(e)}"
                self.log(logging.ERROR, error_msg)
                raise ConnectionError(f"Failed to disconnect: {str(e)}")
            finally:
                self._connection = None
                self._cursor = None
                self._transaction_manager = None

    def ping(self, reconnect: bool = True) -> bool:
        """Test database connection

        Args:
            reconnect: Whether to attempt reconnection if connection is lost

        Returns:
            bool: True if connection is alive
        """
        if not self._connection:
            self.log(logging.DEBUG, "No active connection during ping")
            if reconnect:
                self.log(logging.INFO, "Reconnecting during ping")
                self.connect()
                return True
            return False

        try:
            self.log(logging.DEBUG, "Pinging MariaDB connection")
            self._connection.ping()
            self.log(logging.DEBUG, "Ping successful")
            return True
        except MariaDBError as e:
            self.log(logging.WARNING, f"Ping failed: {str(e)}")
            if reconnect:
                self.log(logging.INFO, "Reconnecting after failed ping")
                self.connect()
                return True
            return False

    def execute(
            self,
            sql: str,
            params: Optional[Tuple] = None,
            returning: bool = False,
            column_types: Optional[ColumnTypes] = None,
            returning_columns: Optional[List[str]] = None,
            force_returning: bool = False) -> Optional[QueryResult]:
        """Execute SQL statement with support for RETURNING clause in MariaDB 10.5+

        Args:
            sql: SQL statement
            params: Query parameters
            returning: Whether to return result set
            column_types: Column type mapping
            returning_columns: Specific columns to return
            force_returning: Force using RETURNING if supported

        Returns:
            Optional[QueryResult]: Query results

        Raises:
            ConnectionError: Database connection failed
            QueryError: Invalid SQL
            DatabaseError: Other database errors
        """
        start_time = time.perf_counter()

        # Log query with parameters
        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")

        try:
            # Ensure active connection
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            # Parse statement type
            stmt_type = sql.strip().split(None, 1)[0].upper()
            is_select = stmt_type == "SELECT"
            is_dml = stmt_type in ("INSERT", "UPDATE", "DELETE")
            need_returning = returning and is_dml

            # Check RETURNING support for DML statements
            if need_returning:
                handler = self.dialect.returning_handler
                if not handler.is_supported:
                    error_msg = "RETURNING clause not supported by MariaDB version. Version 10.5 or higher is required."
                    self.log(logging.WARNING, error_msg)
                    raise ReturningNotSupportedError(error_msg)

                # Format and append RETURNING clause
                sql += " " + handler.format_clause(returning_columns)
                self.log(logging.DEBUG, f"Added RETURNING clause: {sql}")

            # Get or create cursor - use dictionary=True to get results as dictionaries
            cursor = self._cursor or self._connection.cursor(dictionary=True)

            # Process SQL and parameters
            final_sql, final_params = self.build_sql(sql, params)
            self.log(logging.DEBUG, f"Processed SQL: {final_sql}")

            # Convert parameters if needed
            if final_params:
                processed_params = tuple(
                    self.dialect.value_mapper.to_database(value, None)
                    for value in final_params
                )
            else:
                processed_params = None

            # Execute query
            cursor.execute(final_sql, processed_params)

            # Handle result set
            data = None
            if is_select or (need_returning and handler.is_supported):
                rows = cursor.fetchall()
                row_count = len(rows) if rows else 0
                self.log(logging.DEBUG, f"Fetched {row_count} rows")

                if column_types:
                    # Apply type conversions
                    self.log(logging.DEBUG, "Applying type conversions")
                    data = []
                    for row in rows:
                        converted_row = {}
                        for key, value in row.items():
                            db_type = column_types.get(key)
                            if db_type is not None:
                                converted_row[key] = (
                                    self.dialect.value_mapper.from_database(
                                        value, db_type
                                    )
                                )
                            else:
                                converted_row[key] = value
                        data.append(converted_row)
                else:
                    data = rows

            duration = time.perf_counter() - start_time

            # Log completion metrics
            if is_dml:
                self.log(logging.INFO,
                         f"{stmt_type} affected {cursor.rowcount} rows, "
                         f"last_insert_id={cursor.lastrowid}, duration={duration:.3f}s")
            elif is_select:
                row_count = len(data) if data is not None else 0
                self.log(logging.INFO, f"{stmt_type} returned {row_count} rows, duration={duration:.3f}s")

            # Build result
            result = QueryResult(
                data=data,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid,
                duration=duration
            )

            return result

        except MariaDBError as e:
            self.log(logging.ERROR, f"MariaDB error: {str(e)}")
            self._handle_error(e)

    def _handle_error(self, error: Exception) -> None:
        """Handle MariaDB specific errors

        Args:
            error: MariaDB exception

        Raises:
            Appropriate exception type for the error
        """
        if isinstance(error, MariaDBError):
            msg = str(error)

            if isinstance(error, MariaDBIntegrityError):
                if "Duplicate entry" in msg:
                    self.log(logging.ERROR, f"Unique constraint violation: {msg}")
                    raise IntegrityError(f"Unique constraint violation: {msg}")
                elif "foreign key constraint fails" in msg.lower():
                    self.log(logging.ERROR, f"Foreign key constraint violation: {msg}")
                    raise IntegrityError(f"Foreign key constraint violation: {msg}")
                self.log(logging.ERROR, f"Integrity error: {msg}")
                raise IntegrityError(msg)

            elif isinstance(error, MariaDBOperationalError):
                if "Lock wait timeout exceeded" in msg:
                    self.log(logging.ERROR, f"Lock wait timeout exceeded: {msg}")
                    raise DeadlockError(msg)
                elif "deadlock" in msg.lower():
                    self.log(logging.ERROR, f"Deadlock detected: {msg}")
                    raise DeadlockError(msg)
                self.log(logging.ERROR, f"Operational error: {msg}")
                raise OperationalError(msg)

            elif isinstance(error, ProgrammingError):
                self.log(logging.ERROR, f"SQL error: {msg}")
                raise QueryError(msg)

            elif isinstance(error, MariaDBDatabaseError):
                self.log(logging.ERROR, f"Database error: {msg}")
                raise DatabaseError(msg)

            # Log unknown MariaDB errors
            self.log(logging.ERROR, f"Unhandled MariaDB error: {msg}")

        # Log and re-raise other errors
        self.log(logging.ERROR, f"Unhandled error: {str(error)}")
        raise error

    def execute_many(
            self,
            sql: str,
            params_list: List[Tuple]
    ) -> Optional[QueryResult]:
        """Execute batch operations

        Args:
            sql: SQL statement
            params_list: List of parameter tuples

        Returns:
            QueryResult: Execution results
        """
        start_time = time.perf_counter()
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._connection.cursor()

            # Convert parameters
            converted_params = []
            for params in params_list:
                if params:
                    converted = tuple(
                        self.dialect.value_mapper.to_database(value, None)
                        for value in params
                    )
                    converted_params.append(converted)

            cursor.executemany(sql, converted_params)
            duration = time.perf_counter() - start_time

            self.log(logging.INFO,
                     f"Batch operation completed, affected {cursor.rowcount} rows, duration={duration:.3f}s")

            return QueryResult(
                affected_rows=cursor.rowcount,
                duration=duration
            )

        except MariaDBError as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            self._handle_error(e)

    def _handle_auto_commit(self) -> None:
        """Handle auto commit based on MariaDB connection and transaction state.

        This method will commit the current connection if:
        1. Connection exists and is open
        2. There is no active transaction managed by transaction_manager

        It's used by insert/update/delete operations to ensure changes are
        persisted immediately when auto_commit=True is specified.
        """
        try:
            # Check if connection exists
            if not self._connection:
                return

            # Check if we're not in an active transaction
            if not self._transaction_manager or not self._transaction_manager.is_active:
                # For MariaDB, we need to commit explicitly
                self._connection.commit()
                self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            # Just log the error but don't raise - this is a convenience feature
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    @property
    def transaction_manager(self) -> MariaDBTransactionManager:
        """Get transaction manager"""
        if not self._transaction_manager:
            if not self._connection:
                self.log(logging.DEBUG, "Initializing connection for transaction manager")
                self.connect()
            self.log(logging.DEBUG, "Creating new transaction manager")
            self._transaction_manager = MariaDBTransactionManager(self._connection, self.logger)
        return self._transaction_manager

    @property
    def supports_returning(self) -> bool:
        """Check if RETURNING is supported

        Returns:
            bool: True if MariaDB version is 10.5 or higher
        """
        supported = self.dialect.returning_handler.is_supported
        self.log(logging.DEBUG, f"RETURNING clause support: {supported}")
        return supported

    def get_server_version(self) -> tuple:
        """Get MariaDB server version

        Returns version tuple (major, minor, patch) with caching
        to avoid repeated queries. Version is cached per connection.

        Returns:
            tuple: Server version as (major, minor, patch)
        """
        # Return cached version if available
        if self._server_version_cache:
            return self._server_version_cache

        # If we have connection config version, use it
        if hasattr(self.config, 'version') and self.config.version:
            self._server_version_cache = self.config.version
            return self._server_version_cache

        # Otherwise query the server
        try:
            if not self._connection:
                self.connect()

            self.log(logging.DEBUG, "Querying MariaDB server version")
            cursor = self._connection.cursor()
            cursor.execute("SELECT VERSION()")
            version_str = cursor.fetchone()[0]
            cursor.close()

            # Parse version string (e.g. "10.5.13-MariaDB" into (10, 5, 13))
            # Handle strings like "10.5.13-MariaDB" or "10.6.5-MariaDB-1:10.6.5+maria~focal"
            version_parts = version_str.split('-')[0].split('.')
            major = int(version_parts[0])
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0
            patch = int(version_parts[2]) if len(version_parts) > 2 else 0

            # Cache the result
            self._server_version_cache = (major, minor, patch)

            # Update dialect's version information
            self._update_dialect_version(self._server_version_cache)

            self.log(logging.INFO, f"Detected MariaDB version: {major}.{minor}.{patch}")
            return self._server_version_cache

        except Exception as e:
            # Log the error
            error_msg = f"Failed to determine MariaDB version: {str(e)}"
            self.log(logging.ERROR, error_msg)
            # Default to a relatively recent version
            default_version = (10, 5, 0)
            self.log(logging.WARNING,
                     f"Using default MariaDB version {default_version} instead of actual version")
            self._server_version_cache = default_version
            return default_version

    def _update_dialect_version(self, version: tuple) -> None:
        """Update the dialect's version information

        Args:
            version: Database server version tuple (major, minor, patch)
        """
        self._dialect._version = version

        # Also update version information in dialect's handlers
        if hasattr(self._dialect, '_returning_handler'):
            self._dialect._returning_handler._version = version

        if hasattr(self._dialect, '_aggregate_handler'):
            self._dialect._aggregate_handler._version = version

        if hasattr(self._dialect, '_json_operation_handler'):
            self._dialect._json_operation_handler._version = version

    def format_json_operation(self, column: Union[str, Any], path: Optional[str] = None,
                              operation: str = "extract", value: Any = None,
                              alias: Optional[str] = None) -> str:
        """Format JSON operation according to database dialect.

        Delegates to the dialect's json_operation_handler for database-specific formatting.

        Args:
            column: JSON column name or expression
            path: JSON path
            operation: Operation type (extract, contains, exists, etc.)
            value: Value for operations that need it (contains, insert, etc.)
            alias: Optional alias for the result

        Returns:
            str: Database-specific JSON operation SQL

        Raises:
            JsonOperationNotSupportedError: If JSON operations not supported
        """
        if not hasattr(self.dialect, 'json_operation_handler'):
            raise JsonOperationNotSupportedError(
                f"JSON operations not supported by {self.dialect.__class__.__name__}"
            )

        return self.dialect.json_operation_handler.format_json_operation(
            column=column,
            path=path,
            operation=operation,
            value=value,
            alias=alias
        )