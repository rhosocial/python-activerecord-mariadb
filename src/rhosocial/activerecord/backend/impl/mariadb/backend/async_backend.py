# src/rhosocial/activerecord/backend/impl/mariadb/backend/async_backend.py
"""Asynchronous MariaDB-specific implementation of the AsyncStorageBackend.

This module provides the concrete async implementation for interacting with
MariaDB databases, handling connections, queries, transactions, and type
adaptations tailored for MariaDB's specific behaviors and SQL dialect.
"""

import datetime
import logging
import time
from typing import List, Optional, Tuple, Any, Dict

from rhosocial.activerecord.backend.base import AsyncStorageBackend
from rhosocial.activerecord.backend.errors import (
    ConnectionError,
    DatabaseError,
    DeadlockError,
    IntegrityError,
    OperationalError,
    QueryError,
)
from rhosocial.activerecord.backend.result import QueryResult
from rhosocial.activerecord.backend.introspection.backend_mixin import IntrospectorBackendMixin
from rhosocial.activerecord.backend.explain import AsyncExplainBackendMixin

from ..config import MariaDBConnectionConfig
from ..dialect import MariaDBDialect
from ..async_transaction import AsyncMariaDBTransactionManager
from ..mixins import AsyncMariaDBConcurrencyMixin, MariaDBBackendMixin


class AsyncMariaDBBackend(
    AsyncExplainBackendMixin,
    MariaDBBackendMixin,
    IntrospectorBackendMixin,
    AsyncMariaDBConcurrencyMixin,
    AsyncStorageBackend,
):
    """Asynchronous MariaDB-specific backend implementation.

    This backend uses the mariadb connector's native async support, provided by
    Connector/Python 2.0 through ``mariadb.asyncConnect``.
    """

    def __init__(self, **kwargs):
        """Initialize async MariaDB backend with connection configuration.

        Args:
            version: Expected MariaDB server version tuple (major, minor, patch).
                     Used for dialect and type adapter initialization.
                     Defaults to (10, 5, 0). Can be passed as 'version' in kwargs.
        """
        version = kwargs.pop('version', None) or (10, 5, 0)

        connection_config = kwargs.get('connection_config')

        if connection_config is None:
            config_params = {}
            mariadb_specific_params = [
                'host', 'port', 'database', 'username', 'password',
                'charset', 'collation', 'timezone', 'version',
                'pool_size', 'pool_timeout', 'pool_name',
                'ssl_ca', 'ssl_cert', 'ssl_key',
                'ssl_verify_cert', 'ssl_verify_identity',
                'log_queries', 'log_level',
                'autocommit', 'init_command',
                'connect_timeout', 'read_timeout', 'write_timeout',
                'ssl_disabled', 'socket_timeout', 'reconnect',
            ]

            for param in mariadb_specific_params:
                if param in kwargs:
                    config_params[param] = kwargs[param]

            if 'charset' not in config_params:
                config_params['charset'] = 'utf8mb4'
            if 'autocommit' not in config_params:
                config_params['autocommit'] = False
            if 'host' not in config_params:
                config_params['host'] = 'localhost'
            if 'port' not in config_params:
                config_params['port'] = 3306

            kwargs['connection_config'] = MariaDBConnectionConfig(**config_params)

        super().__init__(**kwargs)

        self._version = version
        self._dialect = None
        self._transaction_manager = AsyncMariaDBTransactionManager(self, self.logger)

        self._register_mariadb_adapters()

        self.log(logging.INFO, "AsyncMariaDBBackend initialized")

    async def executescript(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script asynchronously.

        MariaDB accepts the whole script in a single execute(), which keeps
        BEGIN...END blocks in triggers, procedures and functions intact.

        Args:
            sql_script: SQL script with statements separated by semicolons.
        """
        self.log(logging.DEBUG, "Executing SQL script")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                await self.connect()

            cursor = self._cursor or await self._get_cursor()

            await cursor.execute(sql_script)

            # Consume every result set; nextset is synchronous in 2.0
            while cursor.nextset():
                pass

            duration = time.perf_counter() - start_time
            self.log(logging.DEBUG, f"SQL script executed successfully, duration={duration:.3f}s")
        except Exception as e:
            self.log(logging.ERROR, f"Error executing SQL script: {str(e)}")
            self._handle_error(e)

    def _parse_explain_result(self, raw_rows, sql, duration):
        """Parse EXPLAIN result into MariaDB's typed result."""
        from ..explain import MariaDBExplainResult, MariaDBExplainRow

        rows = [MariaDBExplainRow(**r) for r in raw_rows]
        return MariaDBExplainResult(raw_rows=raw_rows, sql=sql, duration=duration, rows=rows)

    def _create_introspector(self) -> Any:
        """Create an AsyncMariaDBIntrospector backed by an AsyncIntrospectorExecutor."""
        from rhosocial.activerecord.backend.introspection.executor import AsyncIntrospectorExecutor
        from ..introspection import AsyncMariaDBIntrospector

        return AsyncMariaDBIntrospector(self, AsyncIntrospectorExecutor(self))

    async def introspect_and_adapt(self) -> None:
        """Introspect backend and adapt to actual server capabilities.

        This method ensures a connection exists, queries the actual MariaDB
        server version, and updates the backend's internal state accordingly.
        """
        if not self._connection:
            await self.connect()
        actual_version = await self.get_server_version()
        if self._version != actual_version:
            self._version = actual_version
            self._dialect = MariaDBDialect(actual_version)
            self._register_mariadb_adapters()
            self.log(logging.INFO, f"Adapted to MariaDB server version {actual_version}")

    async def connect(self):
        """Establish async connection to MariaDB database.

        Requires Connector/Python 2.0, which exposes the async API as
        ``mariadb.asyncConnect``.
        """
        import mariadb

        if not hasattr(mariadb, "asyncConnect"):
            raise ImportError(
                "The async MariaDB backend needs mariadb 2.0, which provides "
                "asyncConnect. Install it with: pip install "
                "'mariadb>=2.0.0rc2'. Note that 1.1 exposed the async API as "
                "mariadb.aio instead."
            )

        await self._connect_mariadb_async()

    async def _connect_mariadb_async(self):
        """Connect using mariadb async connector."""
        import mariadb

        try:
            conn_params = self.config.get_connection_params()

            self._connection = await mariadb.asyncConnect(**conn_params)

            init_command = getattr(self.config, 'init_command', None)
            if init_command:
                cursor = self._connection.cursor()
                await cursor.execute(init_command)
                await cursor.close()

            self.log(
                logging.INFO,
                f"Connected to MariaDB database: "
                f"{self.config.host}:{self.config.port}/{self.config.database}"
            )
            await self._fetch_concurrency_hint()
        except mariadb.Error as e:
            self.log(logging.ERROR, f"Failed to connect to MariaDB database: {str(e)}")
            raise ConnectionError(f"Failed to connect to MariaDB: {str(e)}") from e

    async def disconnect(self):
        """Close async connection to MariaDB database."""
        if self._connection:
            try:
                if self.transaction_manager.is_active:
                    await self.transaction_manager.rollback()

                await self._connection.close()
                self._connection = None
                self.log(logging.INFO, "Disconnected from MariaDB database")
            except Exception as e:
                self.log(logging.ERROR, f"Error during disconnect: {str(e)}")
                raise OperationalError(f"Error during MariaDB disconnect: {str(e)}") from e

    async def _get_cursor(self):
        """Get a database cursor, ensuring connection is active."""
        if not self._connection:
            await self.connect()

        return self._connection.cursor()

    async def execute_many(self, sql: str, params_list: List[Tuple]) -> QueryResult:
        """Execute the same SQL statement multiple times with different parameters."""
        if not self._connection:
            await self.connect()

        cursor = None
        start_time = datetime.datetime.now()

        try:
            cursor = await self._get_cursor()

            if getattr(self.config, 'log_queries', False):
                self.log(logging.DEBUG, f"Executing batch operation: {sql}")
                self.log(logging.DEBUG, f"With {len(params_list)} parameter sets")

            affected_rows = 0
            for params in params_list:
                await cursor.execute(sql, params)
                affected_rows += cursor.rowcount

            duration = (datetime.datetime.now() - start_time).total_seconds()

            result = QueryResult(
                affected_rows=affected_rows,
                data=None,
                duration=duration
            )

            self.log(
                logging.INFO,
                f"Batch operation completed, affected {affected_rows} rows, "
                f"duration={duration:.3f}s"
            )
            return result

        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            await self._handle_error(e)
        finally:
            if cursor:
                await cursor.close()

    async def get_server_version(self) -> tuple:
        """Get MariaDB server version asynchronously."""
        if not self._connection:
            await self.connect()

        cursor = None
        try:
            cursor = await self._get_cursor()
            await cursor.execute("SELECT VERSION()")
            version_row = await cursor.fetchone()
            version_str = version_row[0] if version_row else "10.5.0"

            # Strip the vendor suffix: "13.1.1-MariaDB-ubu2604" -> "13.1.1".
            version_clean = version_str.split('-')[0]

            version_parts = version_clean.split('.')

            major = int(version_parts[0]) if len(version_parts) > 0 else 10
            minor = int(version_parts[1]) if len(version_parts) > 1 else 5
            patch = int(version_parts[2]) if len(version_parts) > 2 else 0

            version_tuple = (major, minor, patch)

            self.log(logging.INFO, f"MariaDB server version: {major}.{minor}.{patch}")
            return version_tuple
        except Exception as e:
            self.log(logging.WARNING, f"Could not determine MariaDB version: {str(e)}, defaulting to 10.5.0")
            return (10, 5, 0)
        finally:
            if cursor:
                await cursor.close()

    async def ping(self, reconnect: bool = True) -> bool:
        """Test the MariaDB connection and optionally reconnect.

        Args:
            reconnect: If True, attempt to reconnect when the connection is dead.

        Returns:
            True if the connection answered, or was successfully reconnected.
        """
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
            return False

        try:
            self.log(logging.DEBUG, "Testing connection with SELECT 1")
            cursor = await self._get_cursor()
            await cursor.execute("SELECT 1")
            await cursor.fetchone()
            await cursor.close()

            return True
        except Exception as e:
            self.log(logging.WARNING, f"MariaDB connection ping failed: {str(e)}")
            if reconnect:
                try:
                    await self.disconnect()
                    await self.connect()
                    return True
                except Exception as connect_error:
                    self.log(logging.ERROR, f"Failed to reconnect: {str(connect_error)}")
                    return False
            return False

    async def _handle_error(self, error: Exception) -> None:
        """Delegate to the shared driver error mapping."""
        self._handle_mariadb_error(error)

    async def _handle_auto_commit(self) -> None:
        """Handle auto commit based on connection and transaction state."""
        try:
            if not self._connection:
                return

            if not self._transaction_manager or not self._transaction_manager.is_active:
                if not getattr(self.config, 'autocommit', False):
                    await self._connection.commit()
                    self.log(logging.DEBUG, "Auto-committed operation")
        except Exception as e:
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    async def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        *,
        options=None,
        **kwargs
    ) -> QueryResult:
        """Execute a SQL statement with optional parameters asynchronously."""
        from rhosocial.activerecord.backend.options import ExecutionOptions, StatementType

        if options is None:
            sql_upper = sql.strip().upper()
            if sql_upper.startswith(('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
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

        return await super().execute(sql, params, options=options)
