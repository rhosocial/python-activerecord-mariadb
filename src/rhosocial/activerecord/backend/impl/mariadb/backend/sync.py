# src/rhosocial/activerecord/backend/impl/mariadb/backend/sync.py
"""
MariaDB-specific synchronous implementation of the StorageBackend.

This module provides the concrete implementation for interacting with MariaDB databases,
handling connections, queries, transactions, and type adaptations tailored for MariaDB's
specific behaviors and SQL dialect.

Features:
- Connection health checking (Plan A: pre-check)
- Automatic reconnection on connection errors (Plan B: retry)
- Comprehensive error handling with MariaDB error code mapping
- Query logging support
- RETURNING clause support for INSERT, DELETE, REPLACE
"""

import logging
import time
import datetime
import mariadb
from typing import Any, Dict, List, Optional, Tuple, Union

from rhosocial.activerecord.backend.base import StorageBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.errors import (
    ConnectionError,
    DatabaseError,
    IntegrityError,
    OperationalError,
    QueryError,
    DeadlockError,
)
from rhosocial.activerecord.backend.options import DeleteOptions, ExecutionOptions, InsertOptions, StatementType, UpdateOptions
from rhosocial.activerecord.backend.result import QueryResult
from rhosocial.activerecord.backend.introspection.backend_mixin import IntrospectorBackendMixin
from rhosocial.activerecord.backend.introspection.executor import SyncIntrospectorExecutor
from rhosocial.activerecord.backend.explain import SyncExplainBackendMixin

from ..config import MariaDBConnectionConfig
from ..dialect import MariaDBDialect
from ..transaction import MariaDBTransactionManager
from ..mixins import MariaDBBackendMixin, MariaDBConcurrencyMixin

# MariaDB connection error codes that indicate connection loss
# Reference: https://mariadb.com/kb/en/mariadb-error-codes/
CONNECTION_ERROR_CODES = {
    2003,  # CR_CONN_HOST_ERROR - Can't connect to MariaDB server
    2006,  # CR_SERVER_GONE_ERROR - MariaDB server has gone away
    2013,  # CR_SERVER_LOST - Lost connection to MariaDB server during query
    2048,  # CR_CONN_UNKNOW_PROTOCOL - Invalid connection protocol
    2055,  # CR_SERVER_LOST_EXTENDED - Lost connection to MariaDB server
    2502,  # CR_SERVER_GONE - The server has gone away
}


class MariaDBBackend(MariaDBBackendMixin, MariaDBConcurrencyMixin, SyncExplainBackendMixin, IntrospectorBackendMixin, StorageBackend):
    """Synchronous MariaDB backend implementation.

    Provides:
    - Connection health checking with automatic reconnection
    - Comprehensive error handling
    - Introspection support via the `introspector` property
    - RETURNING clause support for INSERT, DELETE, REPLACE

    Connection Error Handling:
    Plan A (Pre-check): Before each operation, check if connection is alive
    Plan B (Retry): If connection error occurs mid-query, retry up to max_retries
    """

    def __init__(
        self,
        connection_config: Optional[Union[ConnectionConfig, MariaDBConnectionConfig]] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        version: Optional[Tuple[int, int, int]] = None,
        **kwargs,
    ):
        """Initialize MariaDB backend.

        Args:
            connection_config: Connection configuration object.
            host: Database host (default: localhost).
            port: Database port (default: 3306).
            database: Database name (required).
            username: Database username.
            password: Database password.
            version: Expected MariaDB server version tuple.
            **kwargs: Additional connection parameters.
        """
        if connection_config is None:
            if database is None:
                raise ValueError("Either connection_config or database must be provided")
            connection_config = MariaDBConnectionConfig(
                host=host or "localhost",
                port=port or 3306,
                database=database,
                username=username,
                password=password,
                **kwargs,
            )

        if not isinstance(connection_config, MariaDBConnectionConfig):
            connection_config = MariaDBConnectionConfig(
                host=getattr(connection_config, "host", "localhost"),
                port=getattr(connection_config, "port", 3306),
                database=connection_config.database,
                username=getattr(connection_config, "username", None),
                password=getattr(connection_config, "password", None),
                charset=getattr(connection_config, "charset", "utf8mb4"),
                options=getattr(connection_config, "options", {}),
            )

        super().__init__(connection_config=connection_config)
        self._cursor = None
        self._version = version or (10, 11, 0)
        self._dialect = MariaDBDialect(self._version)
        self._register_mariadb_adapters()

    def _register_mariadb_adapters(self):
        """Register MariaDB-specific type adapters."""
        from ..adapters import (
            MariaDBBlobAdapter,
            MariaDBBooleanAdapter,
            MariaDBDateAdapter,
            MariaDBDatetimeAdapter,
            MariaDBDecimalAdapter,
            MariaDBEnumAdapter,
            MariaDBJSONAdapter,
            MariaDBSetAdapter,
            MariaDBTimeAdapter,
            MariaDBUUIDAdapter,
        )

        adapters = [
            MariaDBBlobAdapter(),
            MariaDBBooleanAdapter(),
            MariaDBDateAdapter(),
            MariaDBDatetimeAdapter(self._version),
            MariaDBDecimalAdapter(),
            MariaDBEnumAdapter(use_int_storage=False),
            MariaDBJSONAdapter(),
            MariaDBSetAdapter(),
            MariaDBTimeAdapter(),
            MariaDBUUIDAdapter(),
        ]

        for adapter in adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type, allow_override=True)

        self.log(logging.DEBUG, "Registered MariaDB-specific type adapters")

    @property
    def dialect(self) -> MariaDBDialect:
        """Get the MariaDB dialect instance."""
        return self._dialect

    def connect(self) -> None:
        """Establish a connection to the MariaDB database."""
        try:
            self.log(
                logging.INFO,
                f"Connecting to MariaDB database: {self.config.host}:{self.config.port}/{self.config.database}"
            )

            conn_params = {
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "user": self.config.username,
                "password": self.config.password,
            }

            if hasattr(self.config, "autocommit"):
                conn_params["autocommit"] = self.config.autocommit

            if hasattr(self.config, "charset") and self.config.charset:
                conn_params["init_command"] = f"SET NAMES {self.config.charset}"

            if hasattr(self.config, "ssl_disabled"):
                if not self.config.ssl_disabled:
                    conn_params["ssl"] = True
                if hasattr(self.config, "tls_version") and self.config.tls_version:
                    conn_params["tls_version"] = self.config.tls_version
                if hasattr(self.config, "ssl_verify_cert") and self.config.ssl_verify_cert:
                    conn_params["ssl_verify_cert"] = self.config.ssl_verify_cert
                if hasattr(self.config, "ssl_verify_identity") and self.config.ssl_verify_identity:
                    conn_params["ssl_verify_identity"] = self.config.ssl_verify_identity

            self._connection = mariadb.connect(**conn_params)
            self.log(logging.INFO, "Connected to MariaDB database successfully")
            self._fetch_concurrency_hint()
            self.introspect_and_adapt()
        except mariadb.Error as e:
            self.log(logging.ERROR, f"Failed to connect to MariaDB database: {str(e)}")
            raise ConnectionError(f"Failed to connect: {str(e)}") from e

    def disconnect(self) -> None:
        """Close the connection to the MariaDB database."""
        try:
            if self._connection:
                self.log(logging.INFO, "Disconnecting from MariaDB database")
                if self._transaction_manager and self._transaction_manager.is_active:
                    self.log(logging.WARNING, "Active transaction detected during disconnect, rolling back")
                    try:
                        self._transaction_manager.rollback()
                    except Exception:
                        pass
                self._connection.close()
                self._connection = None
                self._cursor = None
                self._transaction_manager = None
                self.log(logging.INFO, "Disconnected from MariaDB database")
            else:
                self.log(logging.DEBUG, "Disconnect called on already closed connection")
        except mariadb.Error as e:
            self.log(logging.ERROR, f"Error during disconnect: {str(e)}")
            raise ConnectionError(f"Failed to disconnect: {str(e)}") from e

    def ping(self, reconnect: bool = True) -> bool:
        """Test the database connection and optionally reconnect.

        Args:
            reconnect: If True, attempt to reconnect if the connection is dead.

        Returns:
            True if the connection is alive or was successfully reconnected.
        """
        if not self._connection:
            self.log(logging.DEBUG, "No active connection during ping")
            if reconnect:
                try:
                    self.log(logging.INFO, "Reconnecting during ping")
                    self.connect()
                    return True
                except ConnectionError as e:
                    self.log(logging.WARNING, f"Reconnection failed during ping: {str(e)}")
                    return False
            return False

        try:
            self.log(logging.DEBUG, "Testing connection with SELECT 1")
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except mariadb.Error as e:
            self.log(logging.WARNING, f"Ping failed: {str(e)}")
            if reconnect:
                try:
                    self.log(logging.INFO, "Reconnecting after failed ping")
                    self.disconnect()
                    self.connect()
                    return True
                except ConnectionError as e:
                    self.log(logging.WARNING, f"Reconnection failed after ping: {str(e)}")
                    return False
            return False

    def _get_cursor(self):
        """Get a database cursor with automatic connection health checking.

        This method implements automatic connection health checking (Plan A):
        - Checks if connection object exists
        - Attempts a simple query to verify connection is valid
        - Automatically reconnects if connection was lost
        """
        if not self._connection:
            self.log(logging.DEBUG, "No connection, connecting...")
            self.connect()
        else:
            try:
                cursor = self._connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
            except (mariadb.Error, OSError, BrokenPipeError):
                self.log(logging.DEBUG, "Connection lost, reconnecting...")
                self.disconnect()
                self.connect()

        return self._connection.cursor()

    def _is_connection_error(self, error: Exception) -> bool:
        """Check if an error indicates a connection loss.

        Args:
            error: The exception to check.

        Returns:
            True if the error indicates a connection problem.
        """
        if hasattr(error, 'errno'):
            if error.errno in CONNECTION_ERROR_CODES:
                return True

        error_str = str(error).lower()
        connection_error_patterns = [
            'server has gone away',
            'lost connection',
            "can't connect",
            'connection refused',
            'broken pipe',
            'connection reset',
            'connection timed out',
        ]
        return any(pattern in error_str for pattern in connection_error_patterns)

    def _reconnect(self) -> bool:
        """Attempt to reconnect to the MariaDB server.

        Returns:
            True if reconnection was successful, False otherwise.
        """
        try:
            self.log(logging.INFO, "Attempting to reconnect...")
            self.disconnect()
            self.connect()
            self.log(logging.INFO, "Reconnection successful")
            return True
        except Exception as e:
            self.log(logging.ERROR, f"Reconnection failed: {str(e)}")
            return False

    def _handle_mariadb_error(self, error: Exception) -> None:
        """Handle MariaDB-specific errors and convert to appropriate exceptions.

        Args:
            error: The MariaDB error to handle.

        Raises:
            Appropriate exception based on the error type.
        """
        error_msg = str(error)
        error_code = getattr(error, 'errno', None)

        if isinstance(error, mariadb.OperationalError):
            if error_code in CONNECTION_ERROR_CODES:
                self.log(logging.ERROR, f"Connection error ({error_code}): {error_msg}")
                raise ConnectionError(error_msg) from error
            if "Connection timed out" in error_msg or "Can't connect" in error_msg:
                self.log(logging.ERROR, f"Connection error: {error_msg}")
                raise ConnectionError(error_msg) from error
            if "Deadlock found" in error_msg:
                self.log(logging.ERROR, f"Deadlock: {error_msg}")
                raise DeadlockError(error_msg) from error
            if "Lock wait timeout exceeded" in error_msg:
                self.log(logging.ERROR, f"Lock timeout: {error_msg}")
                raise OperationalError(error_msg) from error
            self.log(logging.ERROR, f"MariaDB operational error: {error_msg}")
            raise OperationalError(error_msg) from error

        if isinstance(error, mariadb.IntegrityError):
            if "Duplicate entry" in error_msg:
                self.log(logging.ERROR, f"Duplicate key error: {error_msg}")
                raise IntegrityError(f"Duplicate key error: {error_msg}") from error
            if "foreign key constraint" in error_msg.lower():
                self.log(logging.ERROR, f"Foreign key constraint violation: {error_msg}")
                raise IntegrityError(f"Foreign key constraint violation: {error_msg}") from error
            if "cannot be null" in error_msg.lower():
                self.log(logging.ERROR, f"Null constraint violation: {error_msg}")
                raise IntegrityError(f"Null constraint violation: {error_msg}") from error
            self.log(logging.ERROR, f"MariaDB integrity error: {error_msg}")
            raise IntegrityError(error_msg) from error

        if isinstance(error, mariadb.ProgrammingError):
            self.log(logging.ERROR, f"MariaDB programming error: {error_msg}")
            raise QueryError(error_msg) from error

        if isinstance(error, mariadb.Error):
            self.log(logging.ERROR, f"MariaDB error: {error_msg}")
            raise DatabaseError(error_msg) from error

        self.log(logging.ERROR, f"Unhandled error: {error_msg}")
        raise error

    def _handle_error(self, error: Exception) -> None:
        """Handle MariaDB-specific errors."""
        self._handle_mariadb_error(error)

    def _prepare_sql_and_params(
        self,
        sql: str,
        params: Optional[Union[Tuple, Dict, List]]
    ) -> Tuple[str, Tuple]:
        """Prepare SQL and parameters for MariaDB.

        Applies type adapter conversions via prepare_parameters() before
        passing values to the MariaDB driver.

        Args:
            sql: SQL statement.
            params: Parameters for the statement.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if isinstance(params, dict):
            final_params = tuple(params.values()) if params else ()
        elif isinstance(params, (tuple, list)):
            final_params = tuple(params) if params else ()
        else:
            final_params = params or ()

        # Apply type adapters for driver-incompatible types (datetime, dict, list, etc.)
        if final_params:
            all_suggestions = self.get_default_adapter_suggestions()
            param_adapters = []
            for param_value in final_params:
                py_type = type(param_value)
                suggestion = all_suggestions.get(py_type)
                param_adapters.append(suggestion if suggestion else None)
            final_params = self.prepare_parameters(final_params, param_adapters)

        return sql, final_params

    def execute(
        self,
        sql: str,
        params: Optional[Union[Tuple, Dict, List]] = None,
        *,
        options=None,
        max_retries: int = 2,
        **kwargs
    ) -> Optional[QueryResult]:
        """Execute a SQL query with automatic reconnection on connection errors.

        This method implements Plan B: Error retry mechanism for handling
        connection loss that occurs mid-query.

        Args:
            sql: The SQL statement to execute.
            params: Parameters for the statement.
            options: Execution options.
            max_retries: Maximum retry attempts for connection errors.
            **kwargs: Additional arguments.

        Returns:
            QueryResult or None if execution failed.
        """
        if options is None:
            sql_upper = sql.strip().upper()
            if sql_upper.startswith(('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'PRAGMA', 'EXPLAIN')):
                stmt_type = StatementType.DQL
            elif sql_upper.startswith(('INSERT', 'UPDATE', 'DELETE', 'REPLACE')):
                stmt_type = StatementType.DML
            else:
                stmt_type = StatementType.DDL

            column_mapping = kwargs.get('column_mapping')
            column_adapters = kwargs.get('column_adapters')

            options = ExecutionOptions(
                stmt_type=stmt_type,
                process_result_set=None,
                column_adapters=column_adapters,
                column_mapping=column_mapping
            )
        else:
            if 'column_mapping' in kwargs:
                options.column_mapping = kwargs['column_mapping']
            if 'column_adapters' in kwargs:
                options.column_adapters = kwargs['column_adapters']

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return self._execute_internal(sql, params, options)
            except (mariadb.OperationalError, mariadb.Error) as e:
                last_error = e

                if self._is_connection_error(e) and attempt < max_retries:
                    self.log(
                        logging.WARNING,
                        f"Connection error on attempt {attempt + 1}/{max_retries + 1}: {str(e)}"
                    )
                    if self._reconnect():
                        continue
                    else:
                        self.log(logging.ERROR, "Reconnection failed, aborting retry")
                        break
                else:
                    break

        if last_error:
            self._handle_error(last_error)

        raise DatabaseError(f"Execution failed after {max_retries + 1} attempts")

    def _execute_internal(
            self,
        sql: str,
        params: Optional[Union[Tuple, Dict, List]] = None,
        options: Optional[ExecutionOptions] = None
    ) -> Optional[QueryResult]:
        """Internal execute without retry logic.

        Args:
            sql: SQL statement.
            params: Parameters for the statement.
            options: Execution options for result processing.

        Returns:
            QueryResult or None if execution produced no results.
        """
        cursor = self._get_cursor()
        sql, params = self._prepare_sql_and_params(sql, params)
        cursor.execute(sql, params)

        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            row_data = [dict(zip(columns, row)) for row in rows] if rows else []
            result = QueryResult(
                data=row_data,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid if hasattr(cursor, 'lastrowid') else None,
            )
            # DML with RETURNING produces a result set but still needs commit
            if not self.in_transaction and options and options.stmt_type == StatementType.DML:
                self._connection.commit()
        else:
            if not self.in_transaction:
                self._connection.commit()
            result = QueryResult(
                data=None,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid if hasattr(cursor, 'lastrowid') else None,
            )

        if options and (options.column_mapping or options.column_adapters):
            result = self._apply_result_mapping(result, options)

        return result

    def _apply_result_mapping(
        self,
        result: QueryResult,
        options: ExecutionOptions
    ) -> QueryResult:
        """Apply column mapping and adapters to a query result.

        Args:
            result: The raw query result.
            options: Execution options with mapping/adapters.

        Returns:
            Transformed QueryResult.
        """
        column_mapping = options.column_mapping or {}
        column_adapters = options.column_adapters or {}

        if not result.data:
            return result

        data = result.data
        if isinstance(data, list) and len(data) > 0:
            first_row = data[0]
            if isinstance(first_row, dict):
                # Apply adapters first (using original column names)
                if column_adapters:
                    adapted_data = []
                    for row in data:
                        adapted_row = dict(row)
                        for col_name, (adapter, target_type) in column_adapters.items():
                            if col_name in adapted_row:
                                adapted_row[col_name] = adapter.from_database(
                                    row[col_name], target_type
                                )
                        adapted_data.append(adapted_row)
                    data = adapted_data

                # Then apply column name mapping
                if column_mapping:
                    mapped_data = []
                    for row in data:
                        mapped_row = {column_mapping.get(k, k): v for k, v in row.items()}
                        mapped_data.append(mapped_row)
                    data = mapped_data

                result.data = data

        return result

    def execute_many(self, sql: str, params_list: List[Tuple]) -> Optional[QueryResult]:
        """Execute batch operations with the same SQL statement and multiple parameter sets.

        Args:
            sql: The SQL statement to execute.
            params_list: List of parameter tuples.

        Returns:
            QueryResult or None.
        """
        self.log(logging.DEBUG, f"Executing batch operation with {len(params_list)} parameter sets")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._get_cursor()
            cursor.executemany(sql, params_list)
            rowcount = cursor.rowcount
            duration = time.perf_counter() - start_time

            self.log(
                logging.DEBUG,
                f"Batch operation completed, affected {rowcount} rows, duration={duration:.3f}s"
            )
            return QueryResult(affected_rows=rowcount, duration=duration)
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            self._handle_error(e)
            return None

    def executescript(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script.

        MariaDB supports multiple statements in a single execute() call.
        This method executes the entire script without splitting, which
        properly handles BEGIN...END blocks in triggers, procedures, and functions.

        Args:
            sql_script: SQL script with multiple statements separated by semicolons.
        """
        self.log(logging.DEBUG, "Executing SQL script")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._get_cursor()

            # MariaDB supports multi-statement execution directly
            # Execute the entire script - this handles BEGIN...END blocks correctly
            cursor.execute(sql_script)

            # Consume all result sets (for multi-statement queries)
            while cursor.nextset():
                pass

            duration = time.perf_counter() - start_time
            self.log(logging.DEBUG, f"SQL script executed successfully, duration={duration:.3f}s")
        except Exception as e:
            self.log(logging.ERROR, f"Error executing SQL script: {str(e)}")
            self._handle_error(e)

    @property
    def transaction_manager(self) -> MariaDBTransactionManager:
        """Get the transaction manager."""
        if not self._transaction_manager:
            if not self._connection:
                self.log(logging.DEBUG, "Initializing connection for transaction manager")
                self.connect()
            self.log(logging.DEBUG, "Creating new transaction manager")
            self._transaction_manager = MariaDBTransactionManager(self, self.logger)
        return self._transaction_manager

    def get_server_version(self) -> Tuple[int, int, int]:
        """Get MariaDB server version.

        Returns:
            Tuple of (major, minor, patch) version numbers.
        """
        if self._server_version_cache is not None:
            return self._server_version_cache

        try:
            if not self._connection:
                self.connect()
            cursor = self._connection.cursor()
            cursor.execute("SELECT VERSION()")
            version_str = cursor.fetchone()[0]
            cursor.close()

            parts = version_str.split("-")[0].split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0

            self._server_version_cache = (major, minor, patch)
            self.log(logging.INFO, f"Detected MariaDB version: {major}.{minor}.{patch}")
            return self._server_version_cache
        except Exception as e:
            error_msg = f"Failed to determine MariaDB version: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise OperationalError(error_msg) from e

    def introspect_and_adapt(self) -> None:
        """Introspect backend and adapt to actual server capabilities."""
        if not self._connection:
            self.connect()

        version = self.get_server_version()
        self._version = version
        self._dialect = MariaDBDialect(version)
        self._register_mariadb_adapters()
        self.log(logging.INFO, f"Adapted dialect version to MariaDB {version[0]}.{version[1]}.{version[2]}")

    def _create_introspector(self):
        """Create the MariaDB introspector instance."""
        from ..introspection import SyncMariaDBIntrospector
        return SyncMariaDBIntrospector(self, SyncIntrospectorExecutor(self))

    def insert(self, options: InsertOptions) -> QueryResult:
        """Insert a record with special handling for RETURNING clause."""
        result = super().insert(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    def update(self, options: UpdateOptions) -> QueryResult:
        """Update records with special handling for RETURNING clause."""
        result = super().update(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    def delete(self, options: DeleteOptions) -> QueryResult:
        """Delete records with special handling for RETURNING clause."""
        result = super().delete(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    def _parse_explain_result(self, raw_rows, sql, duration):
        """Parse EXPLAIN result for MariaDB."""
        from ..explain import MariaDBExplainResult, MariaDBExplainRow
        rows = [MariaDBExplainRow(**r) for r in raw_rows]
        return MariaDBExplainResult(raw_rows=raw_rows, sql=sql, duration=duration, rows=rows)
