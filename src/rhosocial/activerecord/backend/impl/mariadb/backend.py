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

    @property
    def is_mariadb(self) -> bool:
        """Flag to identify MariaDB backend for compatibility checks"""
        return True

    def _is_select_statement(self, stmt_type: str) -> bool:
        """
        Check if statement is a SELECT-like query.

        MariaDB includes additional read-only statements.

        Args:
            stmt_type: Statement type

        Returns:
            bool: True if statement is a read-only query
        """
        return stmt_type in ("SELECT", "EXPLAIN", "SHOW", "DESCRIBE", "DESC", "ANALYZE")

    def _check_returning_compatibility(self, options: ReturningOptions) -> None:
        """
        Check MariaDB version compatibility for RETURNING clause.

        MariaDB supports RETURNING from version 10.5.0.

        Args:
            options: RETURNING options

        Raises:
            ReturningNotSupportedError: If MariaDB version doesn't support RETURNING and not forced
        """
        server_version = self.get_server_version()
        if server_version < (10, 5, 0) and not options.force:
            version_str = '.'.join(map(str, server_version))
            error_msg = (
                f"RETURNING clause not supported in MariaDB {version_str}. "
                f"Version 10.5.0 or higher is required. "
                f"Set force=True to attempt anyway if you understand the limitations."
            )
            self.log(logging.WARNING, error_msg)
            raise ReturningNotSupportedError(error_msg)

    def _prepare_returning_clause(self, sql: str, options: ReturningOptions, stmt_type: str) -> str:
        """
        Prepare RETURNING clause for MariaDB.

        MariaDB 10.5+ supports RETURNING natively.

        Args:
            sql: SQL statement
            options: RETURNING options
            stmt_type: Statement type

        Returns:
            str: SQL statement with RETURNING clause
        """
        # Get returning handler from dialect
        handler = self.dialect.returning_handler

        # Format RETURNING clause
        if options.has_column_specification():
            # Format advanced RETURNING clause with columns, expressions, aliases
            returning_clause = handler.format_advanced_clause(
                options.columns,
                options.expressions,
                options.aliases,
                options.dialect_options
            )
        else:
            # Use simple RETURNING *
            returning_clause = handler.format_clause(None)

        # Append RETURNING clause to SQL
        sql += " " + returning_clause
        self.log(logging.DEBUG, f"Added RETURNING clause: {sql}")

        return sql

    def _get_cursor(self):
        """
        Get or create cursor for MariaDB.

        MariaDB supports dictionary cursors.

        Returns:
            mariadb.connection.cursor: MariaDB cursor
        """
        if self._cursor:
            return self._cursor

        # Create cursor with dictionary=True for dict-like access
        cursor = self._connection.cursor(dictionary=True)
        return cursor

    def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """
        Execute query in MariaDB.

        Args:
            cursor: MariaDB cursor
            sql: SQL statement
            params: Query parameters

        Returns:
            mariadb.cursor: Cursor with executed query
        """
        # Parse statement type for special handling if needed
        stmt_type = self._get_statement_type(sql)

        # Execute with parameters if provided
        if params:
            # Convert parameters for MariaDB
            processed_params = tuple(
                self.dialect.value_mapper.to_database(value, None)
                for value in params
            )
            cursor.execute(sql, processed_params)
        else:
            cursor.execute(sql)

        return cursor

    def _process_result_set(self, cursor, is_select: bool, need_returning: bool, column_types: Optional[ColumnTypes]) -> \
    Optional[List[Dict]]:
        """
        Process query result set for MariaDB.

        Args:
            cursor: MariaDB cursor with executed query
            is_select: Whether this is a SELECT query
            need_returning: Whether RETURNING clause was used
            column_types: Column type mapping for conversion

        Returns:
            Optional[List[Dict]]: Processed result rows or None
        """
        if not (is_select or need_returning):
            return None

        # Fetch all rows
        rows = cursor.fetchall()
        self.log(logging.DEBUG, f"Fetched {len(rows)} rows")

        if not rows:
            return []

        # Apply type conversions if specified
        if column_types:
            self.log(logging.DEBUG, "Applying type conversions")
            data = []

            # Process each row with type conversion
            for row in rows:
                converted_row = {}
                for key, value in row.items():
                    db_type = column_types.get(key)
                    if db_type is not None:
                        converted_row[key] = self.dialect.value_mapper.from_database(value, db_type)
                    else:
                        converted_row[key] = value
                data.append(converted_row)

            return data

        # Return rows directly if no type conversion needed
        return rows

    def _build_query_result(self, cursor, data: Optional[List[Dict]], duration: float) -> QueryResult:
        """
        Build QueryResult object from execution results.

        Args:
            cursor: MariaDB cursor
            data: Processed result data
            duration: Query execution duration

        Returns:
            QueryResult: Query result object
        """
        return QueryResult(
            data=data,
            affected_rows=getattr(cursor, 'rowcount', 0),
            last_insert_id=getattr(cursor, 'lastrowid', None),
            duration=duration
        )

    def _handle_auto_commit_if_needed(self) -> None:
        """
        Handle auto-commit for MariaDB.

        MariaDB requires explicit commit when not in transaction.
        """
        try:
            # Check if connection exists
            if not self._connection:
                return

            # Check if we're not in an active transaction
            if not self._transaction_manager or not self._transaction_manager.is_active:
                self._connection.commit()
                self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            # Just log the error but don't raise
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    def _handle_execution_error(self, error: Exception):
        """
        Handle MariaDB-specific errors during execution.

        Args:
            error: Exception raised during execution

        Raises:
            Appropriate database exception
        """
        if isinstance(error, mariadb.Error):
            # Get MariaDB error code if available
            code = getattr(error, 'errno', None)
            msg = str(error)

            if isinstance(error, mariadb.IntegrityError):
                if "Duplicate entry" in msg:
                    self.log(logging.ERROR, f"Unique constraint violation: {msg}")
                    raise IntegrityError(f"Unique constraint violation: {msg}")
                elif "foreign key constraint fails" in msg.lower():
                    self.log(logging.ERROR, f"Foreign key constraint violation: {msg}")
                    raise IntegrityError(f"Foreign key constraint violation: {msg}")
                self.log(logging.ERROR, f"Integrity error: {msg}")
                raise IntegrityError(msg)

            elif isinstance(error, mariadb.OperationalError):
                if "Lock wait timeout exceeded" in msg:
                    self.log(logging.ERROR, f"Lock wait timeout exceeded: {msg}")
                    raise DeadlockError(msg)
                elif "deadlock" in msg.lower():
                    self.log(logging.ERROR, f"Deadlock detected: {msg}")
                    raise DeadlockError(msg)

        # Call parent handler for common error processing
        super()._handle_execution_error(error)

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