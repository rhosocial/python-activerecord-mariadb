# src/rhosocial/activerecord/backend/impl/mariadb/backend/sync.py
"""
MariaDB-specific synchronous implementation of the StorageBackend.

This module provides the concrete implementation for interacting with MariaDB databases,
handling connections, queries, transactions, and type adaptations tailored for MariaDB's
specific behaviors and SQL dialect.
"""

import logging
import time
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
from rhosocial.activerecord.backend.options import DeleteOptions, InsertOptions, UpdateOptions
from rhosocial.activerecord.backend.result import QueryResult

from ..config import MariaDBConnectionConfig
from ..dialect import MariaDBDialect, SQLDialectBase
from ..transaction import MariaDBTransactionManager


class MariaDBBackend(StorageBackend):
    """Synchronous MariaDB backend implementation."""

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
        self._cursor = None
        self._dialect = MariaDBDialect()

    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def connect(self) -> None:
        """Establish a connection to the MariaDB database."""
        try:
            self.log(logging.INFO, f"Connecting to MariaDB database: {self.config.host}:{self.config.port}/{self.config.database}")

            conn_params = {
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "user": self.config.username,
                "password": self.config.password,
            }

            if hasattr(self.config, "autocommit"):
                conn_params["autocommit"] = self.config.autocommit

            if hasattr(self.config, "charset"):
                conn_params["charset"] = self.config.charset

            if hasattr(self.config, "ssl_disabled"):
                if not self.config.ssl_disabled:
                    conn_params["ssl"] = True
                    if hasattr(self.config, "ssl_verify_cert") and self.config.ssl_verify_cert:
                        conn_params["ssl_verify_cert"] = self.config.ssl_verify_cert
                    if hasattr(self.config, "ssl_verify_identity") and self.config.ssl_verify_identity:
                        conn_params["ssl_verify_identity"] = self.config.ssl_verify_identity

            self._connection = mariadb.connect(**conn_params)
            self.log(logging.INFO, "Connected to MariaDB database successfully")
        except mariadb.Error as e:
            self.log(logging.ERROR, f"Failed to connect to MariaDB database: {str(e)}")
            raise ConnectionError(f"Failed to connect: {str(e)}") from e

    def disconnect(self) -> None:
        """Close the connection to the MariaDB database."""
        try:
            if self._connection:
                self.log(logging.INFO, "Disconnecting from MariaDB database")
                if self.transaction_manager.is_active:
                    self.log(logging.WARNING, "Active transaction detected during disconnect, rolling back")
                    self.transaction_manager.rollback()
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
        """Test the database connection and optionally reconnect."""
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
                    self.connect()
                    return True
                except ConnectionError as e:
                    self.log(logging.WARNING, f"Reconnection failed after ping: {str(e)}")
                    return False
            return False

    def _get_cursor(self):
        """Get or create cursor for MariaDB."""
        return self._connection.cursor()

    def _handle_mariadb_error(self, error: Exception) -> None:
        """Handle MariaDB-specific errors and convert to appropriate exceptions."""
        error_msg = str(error)

        if isinstance(error, mariadb.Error):
            if isinstance(error, mariadb.OperationalError):
                if "Connection timed out" in error_msg or "Can't connect" in error_msg:
                    self.log(logging.ERROR, f"Connection error: {error_msg}")
                    raise ConnectionError(error_msg) from error
                elif "Deadlock found" in error_msg:
                    self.log(logging.ERROR, f"Deadlock: {error_msg}")
                    raise DeadlockError(error_msg) from error
                self.log(logging.ERROR, f"MariaDB operational error: {error_msg}")
                raise OperationalError(error_msg) from error
            elif isinstance(error, mariadb.IntegrityError):
                if "Duplicate entry" in error_msg:
                    self.log(logging.ERROR, f"Duplicate key error: {error_msg}")
                    raise IntegrityError(f"Duplicate key error: {error_msg}") from error
                elif "foreign key constraint" in error_msg.lower():
                    self.log(logging.ERROR, f"Foreign key constraint violation: {error_msg}")
                    raise IntegrityError(f"Foreign key constraint violation: {error_msg}") from error
                self.log(logging.ERROR, f"MariaDB integrity error: {error_msg}")
                raise IntegrityError(error_msg) from error
            elif isinstance(error, mariadb.ProgrammingError):
                self.log(logging.ERROR, f"MariaDB programming error: {error_msg}")
                raise QueryError(error_msg) from error
            else:
                self.log(logging.ERROR, f"Unhandled MariaDB error: {error_msg}")
                raise DatabaseError(f"Unhandled MariaDB error: {error_msg}") from error
        else:
            self.log(logging.ERROR, f"Unhandled non-MariaDB error: {error_msg}")
            raise error

    def _handle_error(self, error: Exception) -> None:
        """Handle MariaDB-specific errors."""
        self._handle_mariadb_error(error)

    def _prepare_sql_and_params(self, sql: str, params: Optional[Union[Tuple, Dict, List]]) -> Tuple[str, Tuple]:
        """Prepare SQL and parameters for MariaDB."""
        if isinstance(params, dict):
            final_params = tuple(params.values()) if params else ()
        elif isinstance(params, (tuple, list)):
            final_params = tuple(params) if params else ()
        else:
            final_params = params or ()
        return sql, final_params

    def execute(self, sql: str, params: Optional[Union[Tuple, Dict, List]] = None) -> Optional[QueryResult]:
        """Execute a SQL query and return results."""
        self.log(logging.INFO, f"Executing: {sql}")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._get_cursor()
            sql, final_params = self._prepare_sql_and_params(sql, params)

            cursor.execute(sql, final_params)
            duration = time.perf_counter() - start_time

            if cursor.description:
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
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

            self.log(logging.INFO, f"Query executed successfully, affected_rows={result.affected_rows}, duration={duration:.3f}s")
            return result

        except Exception as e:
            self.log(logging.ERROR, f"Error executing query: {str(e)}")
            self._handle_error(e)
            return None

    def executescript(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script."""
        self.log(logging.INFO, "Executing SQL script")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._get_cursor()

            for statement in sql_script.split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)

            duration = time.perf_counter() - start_time
            self.log(logging.INFO, f"SQL script executed successfully, duration={duration:.3f}s")
        except Exception as e:
            self.log(logging.ERROR, f"Error executing SQL script: {str(e)}")
            self._handle_error(e)

    def execute_many(self, sql: str, params_list: List[Tuple]) -> Optional[QueryResult]:
        """Execute batch operations with the same SQL statement and multiple parameter sets."""
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._get_cursor()
            cursor.executemany(sql, params_list)
            duration = time.perf_counter() - start_time

            self.log(logging.INFO, f"Batch operation completed, affected {cursor.rowcount} rows, duration={duration:.3f}s")
            return QueryResult(affected_rows=cursor.rowcount, duration=duration)
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            self._handle_error(e)
            return None

    @property
    def transaction_manager(self) -> MariaDBTransactionManager:
        """Get the transaction manager."""
        if not self._transaction_manager:
            if not self._connection:
                self.log(logging.DEBUG, "Initializing connection for transaction manager")
                self.connect()
            self.log(logging.DEBUG, "Creating new transaction manager")
            self._transaction_manager = MariaDBTransactionManager(self._connection, self.logger)
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
        """Introspect backend and adapt backend instance to actual server capabilities."""
        if not self._connection:
            self.connect()

        version = self.get_server_version()
        self._dialect.version = version
        self.log(logging.INFO, f"Adapted dialect version to MariaDB {version[0]}.{version[1]}.{version[2]}")

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
