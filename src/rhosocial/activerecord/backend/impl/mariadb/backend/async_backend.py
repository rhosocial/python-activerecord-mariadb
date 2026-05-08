# src/rhosocial/activerecord/backend/impl/mariadb/backend/async_backend.py
"""
Async MariaDB Backend Implementation.

This module provides an async implementation of MariaDB backend.
Uses mariadb 2.0.0+ async support (asyncConnect) for async MariaDB operations.
"""

import logging
import time
from typing import List, Optional, Tuple, Union

from rhosocial.activerecord.backend.base import AsyncStorageBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.errors import ConnectionError, IntegrityError, OperationalError, QueryError, DatabaseError, DeadlockError
from rhosocial.activerecord.backend.options import InsertOptions, UpdateOptions, DeleteOptions
from rhosocial.activerecord.backend.result import QueryResult
from rhosocial.activerecord.backend.introspection.backend_mixin import IntrospectorBackendMixin
from rhosocial.activerecord.backend.introspection.executor import AsyncIntrospectorExecutor

from ..config import MariaDBConnectionConfig
from ..dialect import MariaDBDialect
from ..mixins import MariaDBBackendMixin, AsyncMariaDBConcurrencyMixin

try:
    import mariadb
    # mariadb 2.0.0+ provides async support via asyncConnect
    if not hasattr(mariadb, 'asyncConnect'):
        raise ImportError(
            "Async MariaDB support requires 'mariadb' package version 2.0.0 or later. "
            "Install with: pip install mariadb>=2.0.0rc2 --pre"
        )
except ImportError:
    raise ImportError(
        "Async MariaDB support requires 'mariadb' package version 2.0.0 or later. "
        "Install with: pip install mariadb>=2.0.0rc2 --pre"
    )


class AsyncMariaDBBackend(AsyncMariaDBConcurrencyMixin, MariaDBBackendMixin, IntrospectorBackendMixin, AsyncStorageBackend):
    """Async MariaDB backend implementation.

    Provides introspection support via the `introspector` property.
    """

    def __init__(
        self,
        connection_config: Optional[Union[ConnectionConfig, MariaDBConnectionConfig]] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ):
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
        self._dialect = MariaDBDialect()

    @property
    def dialect(self) -> MariaDBDialect:
        return self._dialect

    async def connect(self) -> None:
        """Establish a connection to the MariaDB database asynchronously."""
        try:
            self.log(logging.INFO, f"Connecting to MariaDB database: {self.config.host}:{self.config.port}/{self.config.database}")

            conn_params = {
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "user": self.config.username,
                "password": self.config.password,
            }
            # Note: mariadb 2.0.0+ async driver doesn't support charset parameter directly
            # Use init_command to set charset if needed
            if hasattr(self.config, "charset") and self.config.charset:
                conn_params["init_command"] = f"SET NAMES {self.config.charset}"
            if hasattr(self.config, "autocommit"):
                conn_params["autocommit"] = self.config.autocommit

            # SSL configuration
            if hasattr(self.config, "ssl_disabled"):
                if not self.config.ssl_disabled:
                    conn_params["ssl"] = True
                    if hasattr(self.config, "tls_version") and self.config.tls_version:
                        conn_params["tls_version"] = self.config.tls_version
                    if hasattr(self.config, "ssl_verify_cert") and self.config.ssl_verify_cert:
                        conn_params["ssl_verify_cert"] = self.config.ssl_verify_cert
                    if hasattr(self.config, "ssl_verify_identity") and self.config.ssl_verify_identity:
                        conn_params["ssl_verify_identity"] = self.config.ssl_verify_identity

            self._connection = await mariadb.asyncConnect(**conn_params)
            self.log(logging.INFO, "Connected to MariaDB database successfully")
        except Exception as e:
            self.log(logging.ERROR, f"Failed to connect to MariaDB database: {str(e)}")
            raise ConnectionError(f"Failed to connect: {str(e)}") from e

    async def disconnect(self) -> None:
        """Close the connection to the MariaDB database asynchronously."""
        try:
            if self._connection:
                self.log(logging.INFO, "Disconnecting from MariaDB database")
                if self._transaction_manager and self._transaction_manager.is_active:
                    self.log(logging.WARNING, "Active transaction detected during disconnect, rolling back")
                    await self._transaction_manager.rollback()
                await self._connection.close()
                self._connection = None
                self._transaction_manager = None
                self.log(logging.INFO, "Disconnected from MariaDB database")
            else:
                self.log(logging.DEBUG, "Disconnect called on already closed connection")
        except Exception as e:
            self.log(logging.ERROR, f"Error during disconnect: {str(e)}")
            raise ConnectionError(f"Failed to disconnect: {str(e)}") from e

    async def ping(self, reconnect: bool = True) -> bool:
        """Test the database connection and optionally reconnect asynchronously."""
        if not self._connection:
            self.log(logging.DEBUG, "No active connection during ping")
            if reconnect:
                try:
                    self.log(logging.INFO, "Reconnecting during ping")
                    await self.connect()
                    return True
                except ConnectionError as e:
                    self.log(logging.WARNING, f"Reconnection failed during ping: {str(e)}")
            return False

        try:
            self.log(logging.DEBUG, "Testing connection with SELECT 1")
            cursor = self._connection.cursor()
            await cursor.execute("SELECT 1")
            await cursor.close()
            return True
        except Exception as e:
            self.log(logging.WARNING, f"Ping failed: {str(e)}")
            if reconnect:
                try:
                    self.log(logging.INFO, "Reconnecting after failed ping")
                    await self.connect()
                    return True
                except ConnectionError as e:
                    self.log(logging.WARNING, f"Reconnection failed after ping: {str(e)}")
            return False

    async def _get_cursor(self):
        """Get database cursor for async operations.

        Note: This method is async to maintain compatibility with the base class
        and AsyncIntrospectorExecutor, but the underlying cursor() call is not async.
        """
        return self._connection.cursor()

    def _handle_mariadb_error(self, error: Exception) -> None:
        """Handle MariaDB-specific errors."""
        error_msg = str(error)

        if "Connection" in error_msg or "connect" in error_msg.lower():
            self.log(logging.ERROR, f"Connection error: {error_msg}")
            raise ConnectionError(error_msg) from error
        elif "Deadlock" in error_msg:
            self.log(logging.ERROR, f"Deadlock: {error_msg}")
            raise DeadlockError(error_msg) from error
        elif "Duplicate entry" in error_msg:
            self.log(logging.ERROR, f"Duplicate key error: {error_msg}")
            raise IntegrityError(f"Duplicate key error: {error_msg}") from error
        elif "foreign key constraint" in error_msg.lower():
            self.log(logging.ERROR, f"Foreign key constraint violation: {error_msg}")
            raise IntegrityError(f"Foreign key constraint violation: {error_msg}") from error
        elif "syntax" in error_msg.lower():
            self.log(logging.ERROR, f"SQL syntax error: {error_msg}")
            raise QueryError(error_msg) from error
        else:
            self.log(logging.ERROR, f"Unhandled MariaDB error: {error_msg}")
            raise DatabaseError(f"Unhandled MariaDB error: {error_msg}") from error

    async def _handle_error(self, error: Exception) -> None:
        """Handle MariaDB-specific errors asynchronously."""
        self._handle_mariadb_error(error)

    async def _prepare_sql_and_params(self, sql: str, params: Optional[Union[Tuple, dict, List]]) -> Tuple[str, Tuple]:
        """Prepare SQL and parameters."""
        if isinstance(params, dict):
            final_params = tuple(params.values()) if params else ()
        elif isinstance(params, (tuple, list)):
            final_params = tuple(params) if params else ()
        else:
            final_params = params or ()
        return sql, final_params

    async def execute(self, sql: str, params: Optional[Union[Tuple, dict, List]] = None) -> Optional[QueryResult]:
        """Execute a SQL query and return results asynchronously."""
        self.log(logging.INFO, f"Executing: {sql}")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                await self.connect()

            cursor = await self._get_cursor()
            sql, final_params = await self._prepare_sql_and_params(sql, params)

            await cursor.execute(sql, final_params)
            duration = time.perf_counter() - start_time

            if cursor.description:
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = await cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows] if rows else []
                result = QueryResult(
                    data=data,
                    affected_rows=cursor.rowcount,
                    last_insert_id=cursor.lastrowid,
                    duration=duration,
                )
            else:
                result = QueryResult(
                    data=None,
                    affected_rows=cursor.rowcount,
                    last_insert_id=cursor.lastrowid,
                    duration=duration,
                )

            await cursor.close()
            self.log(logging.INFO, f"Query executed successfully, affected_rows={result.affected_rows}, duration={duration:.3f}s")
            return result

        except Exception as e:
            self.log(logging.ERROR, f"Error executing query: {str(e)}")
            await self._handle_error(e)
            return None

    async def execute_many(self, sql: str, params_list: List[Tuple]) -> Optional[QueryResult]:
        """Execute batch operations asynchronously."""
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                await self.connect()

            cursor = await self._get_cursor()
            await cursor.executemany(sql, params_list)
            duration = time.perf_counter() - start_time

            await cursor.close()
            self.log(logging.INFO, f"Batch operation completed, affected {cursor.rowcount} rows, duration={duration:.3f}s")
            return QueryResult(affected_rows=cursor.rowcount, duration=duration)
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            await self._handle_error(e)
            return None

    async def executescript(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script asynchronously.

        MariaDB supports multiple statements in a single execute() call.
        This method executes the entire script without splitting, which
        properly handles BEGIN...END blocks in triggers, procedures, and functions.

        Args:
            sql_script: SQL script with multiple statements separated by semicolons.
        """
        self.log(logging.INFO, "Executing SQL script")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                await self.connect()

            cursor = await self._get_cursor()

            # MariaDB supports multi-statement execution directly
            # Execute the entire script - this handles BEGIN...END blocks correctly
            await cursor.execute(sql_script)

            # Consume all result sets (for multi-statement queries)
            while cursor.nextset():
                pass

            await cursor.close()
            duration = time.perf_counter() - start_time
            self.log(logging.INFO, f"SQL script executed successfully, duration={duration:.3f}s")
        except Exception as e:
            self.log(logging.ERROR, f"Error executing SQL script: {str(e)}")
            await self._handle_error(e)

    async def get_server_version(self) -> Tuple[int, int, int]:
        """Get MariaDB server version asynchronously.

        Returns:
            Tuple of (major, minor, patch) version numbers.
        """
        if self._server_version_cache is not None:
            return self._server_version_cache

        try:
            if not self._connection:
                await self.connect()
            cursor = self._connection.cursor()
            await cursor.execute("SELECT VERSION()")
            row = await cursor.fetchone()
            await cursor.close()
            version_str = row[0]

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

    async def introspect_and_adapt(self) -> None:
        """Introspect backend and adapt to actual server capabilities."""
        if not self._connection:
            await self.connect()

        version = await self.get_server_version()
        self._dialect.version = version
        self.log(logging.INFO, f"Adapted dialect version to MariaDB {version[0]}.{version[1]}.{version[2]}")

    def _create_introspector(self):
        """Create the async MariaDB introspector instance.

        Returns:
            AsyncMariaDBIntrospector for asynchronous introspection.
        """
        from ..introspection import AsyncMariaDBIntrospector
        return AsyncMariaDBIntrospector(self, AsyncIntrospectorExecutor(self))

    async def insert(self, options: InsertOptions) -> QueryResult:
        """Insert a record with special handling for RETURNING clause."""
        result = await super().insert(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    async def update(self, options: UpdateOptions) -> QueryResult:
        """Update records with special handling for RETURNING clause."""
        result = await super().update(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    async def delete(self, options: DeleteOptions) -> QueryResult:
        """Delete records with special handling for RETURNING clause."""
        result = await super().delete(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result
