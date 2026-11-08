# src/rhosocial/activerecord/backend/impl/mariadb/introspection/status_introspector.py
"""MariaDB server status introspector.

Provides server status information by querying MariaDB's SHOW VARIABLES,
SHOW STATUS, and information_schema.

Two families this engine answers are typed in this repository rather than
in core: the binary log and replication (``status_types.py``). They ride
the overview this module builds as an ``MariaDBServerOverview`` -- the core
shape plus its own fields -- because a slot on core's ``ServerOverview``
would assert that every other engine has something it does not have
(``.claude/rules/introspection.md`` §5).

Nothing here is a Galera reader. The ``wsrep_*`` variables and the
``SHOW STATUS LIKE 'wsrep%'`` answers exist only on a Galera-enabled build,
and a stock primary/replica server answers none of them, so no cluster
field is claimed: what the commands below answer is what every MariaDB
server answers.

Design principle: Sync and Async are separate and cannot coexist.
- MariaDBStatusIntrospector: for synchronous backends
- AsyncMariaDBStatusIntrospector: for asynchronous backends
"""

from typing import Any, Dict, List, Optional

from ..expression.show import (
    ShowMasterStatusStatement,
    ShowSlaveStatusStatement,
    ShowStatusStatement,
    ShowVariablesStatement,
)
from ..expression.status import (
    MariaDBDatabaseListQuery,
    MariaDBSessionInfoQuery,
    MariaDBStorageSizeQuery,
    MariaDBUserListQuery,
    MariaDBVersionQuery,
)
from rhosocial.activerecord.backend.introspection.status import (
    StatusItem,
    StatusCategory,
    DatabaseBriefInfo,
    UserInfo,
    ConnectionInfo,
    StorageInfo,
    SessionInfo,
    AbstractStatusIntrospector,
    AsyncAbstractStatusIntrospector,
)
from .status_types import (
    MariaDBBinaryLogInfo,
    MariaDBReplicationInfo,
    MariaDBServerOverview,
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

#: The variables MariaDB answers for, beside the SHOW rows the two families
#: read. Grouped here so a family's sources stay in one place: the variables
#: a row question needs are asked on every run, and a row question is skipped
#: only when its own variable says the answer is empty anyway.
MARIADB_BINLOG_VARIABLES = [
    "log_bin",
    "binlog_format",
    "gtid_binlog_pos",
    "gtid_strict_mode",
]
MARIADB_REPLICATION_VARIABLES = [
    "server_id",
    "log_slave_updates",
]


class MariaDBStatusIntrospectorMixin:
    """Shared non-I/O logic for MariaDB status introspectors."""

    def _get_vendor_name(self) -> str:
        return "MariaDB"

    def parse_variable_value(self, value: Any) -> Any:
        if isinstance(value, str):
            if value.isdigit():
                return int(value)
            low = value.lower()
            if low in ("on", "yes", "true"):
                return True
            if low in ("off", "no", "false"):
                return False
        return value

    def parse_optional_bool(self, value: Any) -> Optional[bool]:
        """Read one yes/no variable, keeping "not reported" as ``None``.

        MariaDB spells switches ON/OFF (and sometimes 1/0); both mean the
        same switch. ``None`` means the server did not answer, which is not
        the same as OFF -- a caller must not turn one into the other.
        """
        if value is None:
            return None
        return bool(self.parse_variable_value(value))

    def parse_optional_int(self, value: Any) -> Optional[int]:
        """Read one numeric fact, keeping "not reported" as ``None``.

        ``SHOW MASTER STATUS`` reports positions as text and a NULL column
        as ``None``; both spellings go through here rather than a ternary
        at each call site, so "the server said nothing" stays one concept.
        """
        if value is None:
            return None
        return int(value)

    def parse_db_list(self, value: Any) -> List[str]:
        """Read one comma-separated database filter into names.

        ``SHOW MASTER STATUS`` writes both filters as comma-separated text;
        an empty string is no filter, not an unread one.
        """
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [str(name).strip() for name in value if str(name).strip()]
        text = str(value).strip()
        if not text:
            return []
        return [name.strip() for name in text.split(",") if name.strip()]

    def _create_status_item(
        self, name: str, value: Any, category: StatusCategory,
        description: Optional[str] = None, unit: Optional[str] = None,
        is_readonly: bool = False, is_dynamic: bool = True,
    ) -> StatusItem:
        return StatusItem(
            name=name, value=self.parse_variable_value(value),
            category=category, description=description, unit=unit,
            is_readonly=is_readonly, is_dynamic=is_dynamic,
        )

    def parse_binary_log_info(
        self,
        variables: Dict[str, Any],
        master_status_rows: Optional[List[Dict[str, Any]]],
    ) -> MariaDBBinaryLogInfo:
        """Read the binlog family from its two sources.

        The variables are always asked, so ``log_enabled`` and the format
        answer even on a server with the log off. The ``SHOW MASTER STATUS``
        row is asked only while the log is on, and its three states are kept
        distinct: ``None`` rows means the command was not asked, ``[]`` means
        asked and answered with nothing (the log is off, or the row is not
        readable), and one row is the log the server is writing.
        """
        info = MariaDBBinaryLogInfo(
            log_enabled=self.parse_optional_bool(variables.get("log_bin")),
            log_format=variables.get("binlog_format") or None,
            gtid_binlog_pos=variables.get("gtid_binlog_pos") or None,
            gtid_strict_mode=self.parse_optional_bool(variables.get("gtid_strict_mode")),
        )
        if not master_status_rows:
            return info
        row = master_status_rows[0]
        info.current_log_file = row.get("file") or None
        info.current_log_position = self.parse_optional_int(row.get("position"))
        info.binlog_do_db = self.parse_db_list(row.get("binlog_do_db"))
        info.binlog_ignore_db = self.parse_db_list(row.get("binlog_ignore_db"))
        info.executed_gtid_set = row.get("executed_gtid_set") or None
        return info

    def parse_replication_info(
        self,
        variables: Dict[str, Any],
        slave_status_rows: Optional[List[Dict[str, Any]]],
    ) -> MariaDBReplicationInfo:
        """Read the replication family from its two sources.

        ``server_id`` and ``log_slave_updates`` answer on every server. The
        ``SHOW SLAVE STATUS`` row answers the replica side, and its three
        states are the same three the binlog row has: not asked (``None``),
        asked with no row (not a replica), asked with one row (this is a
        replica, and the columns describe the connection).

        No Galera field is filled here and the reason is a fact about the
        server, not about this code: the ``wsrep_*`` state exists only on a
        Galera build, and a replica of a Galera cluster is an ordinary
        ``SHOW SLAVE STATUS`` row. See :class:`MariaDBReplicationInfo`.
        """
        server_id = variables.get("server_id")
        info = MariaDBReplicationInfo(
            server_id=None if server_id is None else int(server_id),
            log_slave_updates=self.parse_optional_bool(variables.get("log_slave_updates")),
        )
        if slave_status_rows is None:
            return info
        info.is_replica = bool(slave_status_rows)
        if not slave_status_rows:
            return info
        row = slave_status_rows[0]
        info.slave_io_running = row.get("slave_io_running")
        info.slave_sql_running = row.get("slave_sql_running")
        info.master_host = row.get("master_host")
        info.master_port = self.parse_optional_int(row.get("master_port"))
        info.master_user = row.get("master_user")
        info.seconds_behind_master = self.parse_optional_int(row.get("seconds_behind_master"))
        info.master_log_file = row.get("master_log_file")
        info.read_master_log_pos = self.parse_optional_int(row.get("read_master_log_pos"))
        info.relay_master_log_file = row.get("relay_master_log_file")
        info.slave_io_state = row.get("slave_io_state")
        info.last_io_errno = self.parse_optional_int(row.get("last_io_errno"))
        info.last_io_error = row.get("last_io_error")
        info.last_sql_errno = self.parse_optional_int(row.get("last_sql_errno"))
        info.last_sql_error = row.get("last_sql_error")
        info.relay_log_file = row.get("relay_log_file")
        info.relay_log_pos = self.parse_optional_int(row.get("relay_log_pos"))
        info.exec_master_log_pos = self.parse_optional_int(row.get("exec_master_log_pos"))
        info.using_gtid = row.get("using_gtid")
        info.gtid_io_pos = row.get("gtid_io_pos")
        return info

    def _build_server_overview(
        self,
        version: str,
        session: SessionInfo,
        configuration: List[StatusItem],
        performance: List[StatusItem],
        connections: ConnectionInfo,
        storage: StorageInfo,
        databases: List[DatabaseBriefInfo],
        users: List[UserInfo],
        binary_log: Optional[MariaDBBinaryLogInfo],
        replication: Optional[MariaDBReplicationInfo],
    ) -> MariaDBServerOverview:
        """Build MariaDB's overview: the core shape plus its own families.

        The return is MariaDB's subclass, and ``get_overview()``'s core
        signature does not change -- the subclass is a legal covariant return
        of the core one (``.claude/rules/introspection.md`` §5).
        """
        return MariaDBServerOverview(
            server_version=version,
            server_vendor=self._get_vendor_name(),
            session=session,
            configuration=configuration + performance,
            connections=connections,
            storage=storage,
            databases=databases,
            users=users,
            binary_log=binary_log,
            replication=replication,
        )


class MariaDBStatusIntrospector(MariaDBStatusIntrospectorMixin, AbstractStatusIntrospector):
    """Synchronous MariaDB status introspector."""

    def _execute_query(self, sql: str, params: tuple = ()) -> List[tuple]:
        cursor = self._backend._connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def _execute_query_dict(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        cursor = self._backend._connection.cursor()
        try:
            cursor.execute(sql, params)
            columns = [desc[0].lower() for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def _show_variables(self, names: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in names:
            try:
                sql, params = ShowVariablesStatement(
                    self._backend.dialect, like_pattern=name
                ).to_sql()
                rows = self._execute_query(sql, params)
                if rows:
                    result[rows[0][0].lower()] = rows[0][1]
            except Exception:
                pass
        return result

    def _show_status(self, names: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in names:
            try:
                sql, params = ShowStatusStatement(
                    self._backend.dialect, like_pattern=name, session=False
                ).to_sql()
                rows = self._execute_query(sql, params)
                if rows:
                    result[rows[0][0]] = rows[0][1]
            except Exception:
                pass
        return result

    def get_overview(self) -> MariaDBServerOverview:
        version = self._get_version_string()
        session = self.get_session_info()
        config = self.list_configuration()
        perf = self.list_performance_metrics()
        conn = self.get_connection_info()
        storage = self.get_storage_info()
        databases = self.list_databases()
        users = self.list_users()
        binary_log = self.get_binary_log_info()
        replication = self.get_replication_info()
        return self._build_server_overview(
            version,
            session,
            config,
            perf,
            conn,
            storage,
            databases,
            users,
            binary_log,
            replication,
        )

    def get_binary_log_info(self) -> MariaDBBinaryLogInfo:
        """Answer the binary log family, or as much of it as was answered.

        The variables answer on every server. The row is asked only while
        the log is on, because MariaDB answers ``SHOW MASTER STATUS`` with
        an empty set when it is off, and asking anyway would spend a round
        trip to learn what the variable already says.
        """
        variables = self._show_variables(MARIADB_BINLOG_VARIABLES)
        if variables.get("log_bin", "").lower() not in ("on", "1", "true"):
            return self.parse_binary_log_info(variables, [])
        return self.parse_binary_log_info(
            variables,
            self._execute_query_dict(*ShowMasterStatusStatement(self._backend.dialect).to_sql()),
        )

    def get_replication_info(self) -> MariaDBReplicationInfo:
        """Answer the replication family, or as much of it as was answered.

        The variables answer on every server. ``SHOW SLAVE STATUS`` answers
        the replica side; when it cannot be asked at all the identity facts
        still come back and ``is_replica`` stays ``None``, because "no
        answer" is not "not a replica".
        """
        variables = self._show_variables(MARIADB_REPLICATION_VARIABLES)
        try:
            rows = self._execute_query_dict(
                *ShowSlaveStatusStatement(self._backend.dialect).to_sql()
            )
        except Exception:
            rows = None
        return self.parse_replication_info(variables, rows)

    def _get_version_string(self) -> str:
        try:
            rows = self._execute_query(*MariaDBVersionQuery(self._backend.dialect).to_sql())
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
            rows = self._execute_query_dict(
                *MariaDBStorageSizeQuery(self._backend.dialect).to_sql()
            )
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
            rows = self._execute_query_dict(
                *MariaDBDatabaseListQuery(self._backend.dialect).to_sql()
            )
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
            rows = self._execute_query_dict(
                *MariaDBUserListQuery(self._backend.dialect).to_sql()
            )
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
            rows = self._execute_query_dict(
                *MariaDBSessionInfoQuery(self._backend.dialect).to_sql()
            )
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
        except Exception:
            return SessionInfo()


class AsyncMariaDBStatusIntrospector(MariaDBStatusIntrospectorMixin, AsyncAbstractStatusIntrospector):
    """Asynchronous MariaDB status introspector."""

    async def _execute_query(self, sql: str, params: tuple = ()) -> List[tuple]:
        cursor = self._backend._connection.cursor()
        try:
            await cursor.execute(sql, params)
            return await cursor.fetchall()
        finally:
            await cursor.close()

    async def _execute_query_dict(
        self, sql: str, params: tuple = ()
    ) -> List[Dict[str, Any]]:
        cursor = self._backend._connection.cursor()
        try:
            await cursor.execute(sql, params)
            columns = [desc[0].lower() for desc in cursor.description]
            return [dict(zip(columns, row)) for row in await cursor.fetchall()]
        finally:
            await cursor.close()

    async def _show_variables(self, names: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in names:
            try:
                sql, params = ShowVariablesStatement(
                    self._backend.dialect, like_pattern=name
                ).to_sql()
                rows = await self._execute_query(sql, params)
                if rows:
                    result[rows[0][0].lower()] = rows[0][1]
            except Exception:
                pass
        return result

    async def _show_status(self, names: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in names:
            try:
                sql, params = ShowStatusStatement(
                    self._backend.dialect, like_pattern=name, session=False
                ).to_sql()
                rows = await self._execute_query(sql, params)
                if rows:
                    result[rows[0][0]] = rows[0][1]
            except Exception:
                pass
        return result

    async def get_overview(self) -> MariaDBServerOverview:
        version = await self._get_version_string()
        session = await self.get_session_info()
        config = await self.list_configuration()
        perf = await self.list_performance_metrics()
        conn = await self.get_connection_info()
        storage = await self.get_storage_info()
        databases = await self.list_databases()
        users = await self.list_users()
        binary_log = await self.get_binary_log_info()
        replication = await self.get_replication_info()
        return self._build_server_overview(
            version,
            session,
            config,
            perf,
            conn,
            storage,
            databases,
            users,
            binary_log,
            replication,
        )

    async def get_binary_log_info(self) -> MariaDBBinaryLogInfo:
        """Answer the binary log family, or as much of it as was answered."""
        variables = await self._show_variables(MARIADB_BINLOG_VARIABLES)
        if variables.get("log_bin", "").lower() not in ("on", "1", "true"):
            return self.parse_binary_log_info(variables, [])
        return self.parse_binary_log_info(
            variables,
            await self._execute_query_dict(
                *ShowMasterStatusStatement(self._backend.dialect).to_sql()
            ),
        )

    async def get_replication_info(self) -> MariaDBReplicationInfo:
        """Answer the replication family, or as much of it was answered."""
        variables = await self._show_variables(MARIADB_REPLICATION_VARIABLES)
        try:
            rows = await self._execute_query_dict(
                *ShowSlaveStatusStatement(self._backend.dialect).to_sql()
            )
        except Exception:
            rows = None
        return self.parse_replication_info(variables, rows)

    async def _get_version_string(self) -> str:
        try:
            rows = await self._execute_query(
                *MariaDBVersionQuery(self._backend.dialect).to_sql()
            )
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
            rows = await self._execute_query_dict(
                *MariaDBStorageSizeQuery(self._backend.dialect).to_sql()
            )
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
            rows = await self._execute_query_dict(
                *MariaDBDatabaseListQuery(self._backend.dialect).to_sql()
            )
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
            rows = await self._execute_query_dict(
                *MariaDBUserListQuery(self._backend.dialect).to_sql()
            )
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
            rows = await self._execute_query_dict(
                *MariaDBSessionInfoQuery(self._backend.dialect).to_sql()
            )
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
        except Exception:
            return SessionInfo()
