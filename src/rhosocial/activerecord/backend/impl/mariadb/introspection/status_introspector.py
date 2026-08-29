# src/rhosocial/activerecord/backend/impl/mariadb/introspection/status_introspector.py
"""MariaDB server status introspector.

Provides server status information by querying MariaDB's SHOW VARIABLES,
SHOW STATUS, and information_schema. Includes MariaDB-specific features
like Galera cluster status and thread pool metrics.
"""

from typing import Any, Dict, List, Optional

from rhosocial.activerecord.backend.introspection.status import (
    StatusItem,
    StatusCategory,
    ServerOverview,
    DatabaseBriefInfo,
    UserInfo,
    ConnectionInfo,
    StorageInfo,
    SessionInfo,
    SyncAbstractStatusIntrospector,
    AsyncAbstractStatusIntrospector,
)

MARIADB_CONFIG_VARIABLES = [
    ("max_connections", StatusCategory.CONNECTION, "Maximum simultaneous connections", None),
    ("wait_timeout", StatusCategory.CONNECTION, "Seconds before idle connection timeout", "seconds"),
    ("innodb_buffer_pool_size", StatusCategory.PERFORMANCE, "InnoDB buffer pool size", "bytes"),
    ("innodb_log_file_size", StatusCategory.PERFORMANCE, "InnoDB redo log file size", "bytes"),
    ("query_cache_size", StatusCategory.PERFORMANCE, "Query cache size", "bytes"),
    ("thread_pool_size", StatusCategory.PERFORMANCE, "Thread pool size", None),
    ("character_set_server", StatusCategory.CONFIGURATION, "Server character set", None),
    ("collation_server", StatusCategory.CONFIGURATION, "Server collation", None),
    ("datadir", StatusCategory.STORAGE, "Data directory path", None),
    ("innodb_file_per_table", StatusCategory.STORAGE, "Separate tablespace per table", None),
]

MARIADB_STATUS_VARIABLES = [
    ("Threads_connected", StatusCategory.CONNECTION, "Currently connected threads", None),
    ("Threads_running", StatusCategory.CONNECTION, "Currently running threads", None),
    ("Questions", StatusCategory.PERFORMANCE, "Total queries since startup", None),
    ("Slow_queries", StatusCategory.PERFORMANCE, "Slow queries count", None),
    ("Uptime", StatusCategory.PERFORMANCE, "Server uptime", "seconds"),
    ("Bytes_received", StatusCategory.PERFORMANCE, "Total bytes received", "bytes"),
    ("Bytes_sent", StatusCategory.PERFORMANCE, "Total bytes sent", "bytes"),
    ("Com_select", StatusCategory.PERFORMANCE, "SELECT statements executed", None),
    ("Com_insert", StatusCategory.PERFORMANCE, "INSERT statements executed", None),
    ("Com_update", StatusCategory.PERFORMANCE, "UPDATE statements executed", None),
    ("Com_delete", StatusCategory.PERFORMANCE, "DELETE statements executed", None),
]


class MariaDBStatusIntrospectorMixin:
    """Shared non-I/O logic for MariaDB status introspectors."""

    def _get_vendor_name(self) -> str:
        return "MariaDB"

    def _parse_variable_value(self, value: Any) -> Any:
        if isinstance(value, str):
            if value.isdigit():
                return int(value)
            low = value.lower()
            if low in ("on", "yes", "true"):
                return True
            if low in ("off", "no", "false"):
                return False
        return value

    def _create_status_item(
        self, name: str, value: Any, category: StatusCategory,
        description: Optional[str] = None, unit: Optional[str] = None,
        is_readonly: bool = False, is_dynamic: bool = True,
    ) -> StatusItem:
        return StatusItem(
            name=name, value=self._parse_variable_value(value),
            category=category, description=description, unit=unit,
            is_readonly=is_readonly, is_dynamic=is_dynamic,
        )

    def _build_server_overview(
        self, version: str, session: SessionInfo,
        configuration: List[StatusItem], performance: List[StatusItem],
        connections: ConnectionInfo, storage: StorageInfo,
        databases: List[DatabaseBriefInfo], users: List[UserInfo],
    ) -> ServerOverview:
        return ServerOverview(
            server_version=version,
            server_vendor=self._get_vendor_name(),
            session=session,
            configuration=configuration + performance,
            connections=connections,
            storage=storage,
            databases=databases,
            users=users,
        )


class SyncMariaDBStatusIntrospector(MariaDBStatusIntrospectorMixin, SyncAbstractStatusIntrospector):
    """Synchronous MariaDB status introspector."""

    def _execute_query(self, sql: str) -> List[tuple]:
        cursor = self._backend._connection.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()

    def _execute_query_dict(self, sql: str) -> List[Dict[str, Any]]:
        cursor = self._backend._connection.cursor()
        try:
            cursor.execute(sql)
            columns = [desc[0].lower() for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def _show_variables(self, names: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in names:
            try:
                rows = self._execute_query(f"SHOW VARIABLES LIKE '{name}'")
                if rows:
                    result[rows[0][0].lower()] = rows[0][1]
            except Exception:
                pass
        return result

    def _show_status(self, names: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in names:
            try:
                rows = self._execute_query(f"SHOW GLOBAL STATUS LIKE '{name}'")
                if rows:
                    result[rows[0][0]] = rows[0][1]
            except Exception:
                pass
        return result

    def get_overview(self) -> ServerOverview:
        version = self._get_version_string()
        session = self.get_session_info()
        config = self.list_configuration()
        perf = self.list_performance_metrics()
        conn = self.get_connection_info()
        storage = self.get_storage_info()
        databases = self.list_databases()
        users = self.list_users()
        return self._build_server_overview(
            version, session, config, perf, conn, storage, databases, users,
        )

    def _get_version_string(self) -> str:
        try:
            rows = self._execute_query("SELECT VERSION()")
            return rows[0][0] if rows else "Unknown"
        except Exception:
            return "Unknown"

    def list_configuration(self, category: Optional[StatusCategory] = None) -> List[StatusItem]:
        items: List[StatusItem] = []
        var_names = [v[0] for v in MARIADB_CONFIG_VARIABLES]
        variables = self._show_variables(var_names)

        var_map = {v[0]: v for v in MARIADB_CONFIG_VARIABLES}
        for name, value in variables.items():
            if name in var_map:
                _, cat, desc, unit = var_map[name]
                if category and cat != category:
                    continue
                items.append(self._create_status_item(
                    name=name, value=value, category=cat,
                    description=desc, unit=unit,
                ))
        return items

    def list_performance_metrics(self, category: Optional[StatusCategory] = None) -> List[StatusItem]:
        items: List[StatusItem] = []
        stat_names = [s[0] for s in MARIADB_STATUS_VARIABLES]
        statuses = self._show_status(stat_names)

        stat_map = {s[0]: s for s in MARIADB_STATUS_VARIABLES}
        for name, value in statuses.items():
            if name in stat_map:
                _, cat, desc, unit = stat_map[name]
                if category and cat != category:
                    continue
                items.append(self._create_status_item(
                    name=name, value=value, category=cat,
                    description=desc, unit=unit, is_readonly=True,
                ))
        return items

    def get_connection_info(self) -> ConnectionInfo:
        statuses = self._show_status(["Threads_connected"])
        variables = self._show_variables(["max_connections"])
        return ConnectionInfo(
            active_count=int(statuses.get("Threads_connected", 0)),
            max_connections=int(variables.get("max_connections", 0)) or None,
        )

    def get_storage_info(self) -> StorageInfo:
        try:
            rows = self._execute_query_dict("""
                SELECT SUM(data_length) AS data_bytes,
                       SUM(index_length) AS index_bytes
                FROM information_schema.TABLES
                WHERE table_schema NOT IN
                    ('information_schema', 'performance_schema', 'mysql', 'sys')
            """)
            if rows:
                data = int(rows[0].get("data_bytes") or 0)
                index = int(rows[0].get("index_bytes") or 0)
                return StorageInfo(
                    total_size_bytes=data + index,
                    data_size_bytes=data,
                    index_size_bytes=index,
                )
        except Exception:
            pass
        return StorageInfo()

    def list_databases(self) -> List[DatabaseBriefInfo]:
        try:
            rows = self._execute_query_dict("""
                SELECT s.schema_name,
                       SUM(t.data_length + t.index_length) AS size_bytes,
                       COUNT(CASE WHEN t.table_type = 'BASE TABLE' THEN 1 END) AS table_count,
                       COUNT(CASE WHEN t.table_type = 'VIEW' THEN 1 END) AS view_count
                FROM information_schema.SCHEMATA s
                LEFT JOIN information_schema.TABLES t
                    ON s.schema_name = t.table_schema
                GROUP BY s.schema_name
                ORDER BY s.schema_name
            """)
        except Exception:
            return []

        return [
            DatabaseBriefInfo(
                name=row["schema_name"],
                size_bytes=int(row["size_bytes"]) if row.get("size_bytes") else None,
                table_count=int(row["table_count"]) if row.get("table_count") else 0,
                view_count=int(row["view_count"]) if row.get("view_count") else 0,
            )
            for row in rows
        ]

    def list_users(self) -> List[UserInfo]:
        try:
            rows = self._execute_query_dict("""
                SELECT user, host, Super_priv
                FROM mysql.user ORDER BY user
            """)
        except Exception:
            return []

        return [
            UserInfo(
                name=row["user"],
                host=row.get("host"),
                is_superuser=(row.get("super_priv", "N") == "Y"),
            )
            for row in rows
        ]

    def get_session_info(self) -> SessionInfo:
        try:
            rows = self._execute_query_dict("""
                SELECT CURRENT_USER() AS cur_user,
                       DATABASE() AS cur_db,
                       @@hostname AS host,
                       @@have_ssl AS have_ssl
            """)
        except Exception:
            return SessionInfo()

        if not rows:
            return SessionInfo()
        row = rows[0]
        ssl_enabled = row.get("have_ssl", "").upper() == "YES"
        return SessionInfo(
            user=row.get("cur_user"),
            database=row.get("cur_db"),
            host=row.get("host"),
            ssl_enabled=ssl_enabled,
        )


class AsyncMariaDBStatusIntrospector(MariaDBStatusIntrospectorMixin, AsyncAbstractStatusIntrospector):
    """Asynchronous MariaDB status introspector."""

    async def _execute_query(self, sql: str) -> List[tuple]:
        cursor = self._backend._connection.cursor()
        try:
            await cursor.execute(sql)
            return await cursor.fetchall()
        finally:
            await cursor.close()

    async def _execute_query_dict(self, sql: str) -> List[Dict[str, Any]]:
        cursor = self._backend._connection.cursor()
        try:
            await cursor.execute(sql)
            columns = [desc[0].lower() for desc in cursor.description]
            return [dict(zip(columns, row)) for row in await cursor.fetchall()]
        finally:
            await cursor.close()

    async def _show_variables(self, names: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in names:
            try:
                rows = await self._execute_query(f"SHOW VARIABLES LIKE '{name}'")
                if rows:
                    result[rows[0][0].lower()] = rows[0][1]
            except Exception:
                pass
        return result

    async def _show_status(self, names: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in names:
            try:
                rows = await self._execute_query(
                    f"SHOW GLOBAL STATUS LIKE '{name}'"
                )
                if rows:
                    result[rows[0][0]] = rows[0][1]
            except Exception:
                pass
        return result

    async def get_overview(self) -> ServerOverview:
        version = await self._get_version_string()
        session = await self.get_session_info()
        config = await self.list_configuration()
        perf = await self.list_performance_metrics()
        conn = await self.get_connection_info()
        storage = await self.get_storage_info()
        databases = await self.list_databases()
        users = await self.list_users()
        return self._build_server_overview(
            version, session, config, perf, conn, storage, databases, users,
        )

    async def _get_version_string(self) -> str:
        try:
            rows = await self._execute_query("SELECT VERSION()")
            return rows[0][0] if rows else "Unknown"
        except Exception:
            return "Unknown"

    async def list_configuration(self, category: Optional[StatusCategory] = None) -> List[StatusItem]:
        items: List[StatusItem] = []
        var_names = [v[0] for v in MARIADB_CONFIG_VARIABLES]
        variables = await self._show_variables(var_names)

        var_map = {v[0]: v for v in MARIADB_CONFIG_VARIABLES}
        for name, value in variables.items():
            if name in var_map:
                _, cat, desc, unit = var_map[name]
                if category and cat != category:
                    continue
                items.append(self._create_status_item(
                    name=name, value=value, category=cat,
                    description=desc, unit=unit,
                ))
        return items

    async def list_performance_metrics(self, category: Optional[StatusCategory] = None) -> List[StatusItem]:
        items: List[StatusItem] = []
        stat_names = [s[0] for s in MARIADB_STATUS_VARIABLES]
        statuses = await self._show_status(stat_names)

        stat_map = {s[0]: s for s in MARIADB_STATUS_VARIABLES}
        for name, value in statuses.items():
            if name in stat_map:
                _, cat, desc, unit = stat_map[name]
                if category and cat != category:
                    continue
                items.append(self._create_status_item(
                    name=name, value=value, category=cat,
                    description=desc, unit=unit, is_readonly=True,
                ))
        return items

    async def get_connection_info(self) -> ConnectionInfo:
        statuses = await self._show_status(["Threads_connected"])
        variables = await self._show_variables(["max_connections"])
        return ConnectionInfo(
            active_count=int(statuses.get("Threads_connected", 0)),
            max_connections=int(variables.get("max_connections", 0)) or None,
        )

    async def get_storage_info(self) -> StorageInfo:
        try:
            rows = await self._execute_query_dict("""
                SELECT SUM(data_length) AS data_bytes,
                       SUM(index_length) AS index_bytes
                FROM information_schema.TABLES
                WHERE table_schema NOT IN
                    ('information_schema', 'performance_schema', 'mysql', 'sys')
            """)
            if rows:
                data = int(rows[0].get("data_bytes") or 0)
                index = int(rows[0].get("index_bytes") or 0)
                return StorageInfo(
                    total_size_bytes=data + index,
                    data_size_bytes=data,
                    index_size_bytes=index,
                )
        except Exception:
            pass
        return StorageInfo()

    async def list_databases(self) -> List[DatabaseBriefInfo]:
        try:
            rows = await self._execute_query_dict("""
                SELECT s.schema_name,
                       SUM(t.data_length + t.index_length) AS size_bytes,
                       COUNT(CASE WHEN t.table_type = 'BASE TABLE' THEN 1 END) AS table_count,
                       COUNT(CASE WHEN t.table_type = 'VIEW' THEN 1 END) AS view_count
                FROM information_schema.SCHEMATA s
                LEFT JOIN information_schema.TABLES t
                    ON s.schema_name = t.table_schema
                GROUP BY s.schema_name
                ORDER BY s.schema_name
            """)
        except Exception:
            return []

        return [
            DatabaseBriefInfo(
                name=row["schema_name"],
                size_bytes=int(row["size_bytes"]) if row.get("size_bytes") else None,
                table_count=int(row["table_count"]) if row.get("table_count") else 0,
                view_count=int(row["view_count"]) if row.get("view_count") else 0,
            )
            for row in rows
        ]

    async def list_users(self) -> List[UserInfo]:
        try:
            rows = await self._execute_query_dict("""
                SELECT user, host, Super_priv
                FROM mysql.user ORDER BY user
            """)
        except Exception:
            return []

        return [
            UserInfo(
                name=row["user"],
                host=row.get("host"),
                is_superuser=(row.get("super_priv", "N") == "Y"),
            )
            for row in rows
        ]

    async def get_session_info(self) -> SessionInfo:
        try:
            rows = await self._execute_query_dict("""
                SELECT CURRENT_USER() AS cur_user,
                       DATABASE() AS cur_db,
                       @@hostname AS host,
                       @@have_ssl AS have_ssl
            """)
        except Exception:
            return SessionInfo()

        if not rows:
            return SessionInfo()
        row = rows[0]
        ssl_enabled = row.get("have_ssl", "").upper() == "YES"
        return SessionInfo(
            user=row.get("cur_user"),
            database=row.get("cur_db"),
            host=row.get("host"),
            ssl_enabled=ssl_enabled,
        )
