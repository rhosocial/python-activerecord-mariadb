# src/rhosocial/activerecord/backend/impl/mariadb/introspection/introspector.py
"""
MariaDB concrete introspectors.

Implements SyncAbstractIntrospector and AsyncAbstractIntrospector for MariaDB
databases using the information_schema system tables for metadata queries.

The introspectors are exposed via ``backend.introspector`` and also provide
MariaDB-specific access through ``backend.introspector.show``.

Architecture:
  - SQL generation: Delegated to MariaDBIntrospectionMixin.format_*_query()
    methods in the Dialect layer via Expression.to_sql()
  - Query execution: Handled by IntrospectorExecutor
  - Result parsing: _parse_* methods in this module (pure Python, no I/O)

Key behaviours:
  - Queries information_schema.TABLES, COLUMNS, STATISTICS,
    KEY_COLUMN_USAGE, REFERENTIAL_CONSTRAINTS, VIEWS, TRIGGERS
  - _parse_* methods are pure Python — shared by sync and async introspectors

Design principle: Sync and Async are separate and cannot coexist.
- SyncMariaDBIntrospector: for synchronous backends
- AsyncMariaDBIntrospector: for asynchronous backends
"""

import copy
from typing import Any, Dict, List, Optional

from rhosocial.activerecord.backend.introspection.base import (
    IntrospectorMixin,
    SyncAbstractIntrospector,
    AsyncAbstractIntrospector,
)
from rhosocial.activerecord.backend.introspection.executor import (
    SyncIntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import (
    DatabaseInfo,
    TableInfo,
    TableType,
    ColumnInfo,
    ColumnNullable,
    IndexInfo,
    IndexColumnInfo,
    IndexType,
    ForeignKeyInfo,
    ReferentialAction,
    ViewInfo,
    TriggerInfo,
    IntrospectionScope,
)
from .show_introspector import (
    SyncShowIntrospector,
    AsyncShowIntrospector,
)
from .status_introspector import (
    SyncMariaDBStatusIntrospector,
    AsyncMariaDBStatusIntrospector,
)


class MariaDBIntrospectorMixin(IntrospectorMixin):
    """Mixin providing shared MariaDB-specific introspection logic.

    Both SyncMariaDBIntrospector and AsyncMariaDBIntrospector inherit
    from this mixin to share:
    - Default schema handling
    - MariaDB version detection
    - _parse_* implementations

    SQL generation is delegated to the Dialect layer via Expression.to_sql()
    which calls MariaDBIntrospectionMixin.format_*_query() methods.
    """

    def _get_default_schema(self) -> str:
        """Return the MariaDB database name from the backend config."""
        if hasattr(self._backend, 'config') and hasattr(self._backend.config, 'database'):
            return self._backend.config.database or ""
        return ""

    def _get_version(self) -> tuple:
        """Return the MariaDB server version tuple from the backend."""
        return getattr(self._backend, '_version', (10, 11, 0))

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O
    # ------------------------------------------------------------------ #

    def _parse_database_info(self, rows: List[Dict[str, Any]]) -> DatabaseInfo:
        version = self._get_version()
        version_str = ".".join(str(v) for v in version)
        db_name = self._get_default_schema()

        db_row = rows[0] if rows else {}

        return DatabaseInfo(
            name=db_name,
            version=version_str,
            version_tuple=version,
            vendor="MariaDB",  # 与 MySQL 的主要差异
            encoding=db_row.get("DEFAULT_CHARACTER_SET_NAME"),
            collation=db_row.get("DEFAULT_COLLATION_NAME"),
        )

    def _parse_tables(
        self, rows: List[Dict[str, Any]], schema: Optional[str]
    ) -> List[TableInfo]:
        target_db = schema if schema is not None else self._get_default_schema()
        table_type_map = {
            "BASE TABLE": TableType.BASE_TABLE,
            "VIEW": TableType.VIEW,
            "SYSTEM VIEW": TableType.SYSTEM_TABLE,
        }
        tables = []
        for row in rows:
            t_type = table_type_map.get(row.get("TABLE_TYPE", "BASE TABLE"), TableType.BASE_TABLE)
            tables.append(
                TableInfo(
                    name=row["TABLE_NAME"],
                    schema=target_db,
                    table_type=t_type,
                    comment=row.get("TABLE_COMMENT"),
                    row_count=row.get("TABLE_ROWS"),
                    size_bytes=row.get("DATA_LENGTH"),
                    auto_increment=row.get("AUTO_INCREMENT"),
                    create_time=str(row["CREATE_TIME"]) if row.get("CREATE_TIME") else None,
                    update_time=str(row["UPDATE_TIME"]) if row.get("UPDATE_TIME") else None,
                )
            )
        return tables

    def _parse_columns(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[ColumnInfo]:
        columns = []
        for row in rows:
            nullable = (
                ColumnNullable.NULLABLE
                if row.get("IS_NULLABLE") == "YES"
                else ColumnNullable.NOT_NULL
            )
            col_type = row.get("COLUMN_TYPE") or row.get("DATA_TYPE") or "VARCHAR"
            columns.append(
                ColumnInfo(
                    name=row["COLUMN_NAME"],
                    table_name=table_name,
                    schema=schema,
                    ordinal_position=row["ORDINAL_POSITION"],
                    data_type=col_type.split("(")[0].lower(),
                    data_type_full=col_type,
                    nullable=nullable,
                    default_value=row.get("COLUMN_DEFAULT"),
                    is_primary_key=row.get("COLUMN_KEY") == "PRI",
                    is_unique=row.get("COLUMN_KEY") == "UNI",
                    is_auto_increment="auto_increment" in (row.get("EXTRA") or "").lower(),
                    comment=row.get("COLUMN_COMMENT"),
                    character_maximum_length=row.get("CHARACTER_MAXIMUM_LENGTH"),
                    numeric_precision=row.get("NUMERIC_PRECISION"),
                    numeric_scale=row.get("NUMERIC_SCALE"),
                    charset=row.get("CHARACTER_SET_NAME"),
                    collation=row.get("COLLATION_NAME"),
                )
            )
        return columns

    def _parse_indexes(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[IndexInfo]:
        index_type_map = {
            "BTREE": IndexType.BTREE,
            "HASH": IndexType.HASH,
            "FULLTEXT": IndexType.FULLTEXT,
            "SPATIAL": IndexType.SPATIAL,
            "RTREE": IndexType.SPATIAL,
        }
        index_map: Dict[str, IndexInfo] = {}
        for row in rows:
            idx_name = row.get("INDEX_NAME") or row.get("Key_name", "")
            if idx_name not in index_map:
                idx_type_str = (row.get("INDEX_TYPE") or "BTREE").upper()
                index_map[idx_name] = IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=schema,
                    is_unique=int(row.get("NON_UNIQUE", row.get("Non_unique", 1))) == 0,
                    is_primary=idx_name == "PRIMARY",
                    index_type=index_type_map.get(idx_type_str, IndexType.BTREE),
                    columns=[],
                )
            index_map[idx_name].columns.append(
                IndexColumnInfo(
                    name=row.get("COLUMN_NAME") or row.get("Column_name", ""),
                    ordinal_position=int(row.get("SEQ_IN_INDEX") or row.get("Seq_in_index", 1)),
                    is_descending=False,
                )
            )
        return list(index_map.values())

    def _parse_foreign_keys(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[ForeignKeyInfo]:
        action_map = {
            "NO_ACTION": ReferentialAction.NO_ACTION,
            "NO ACTION": ReferentialAction.NO_ACTION,
            "RESTRICT": ReferentialAction.RESTRICT,
            "CASCADE": ReferentialAction.CASCADE,
            "SET_NULL": ReferentialAction.SET_NULL,
            "SET NULL": ReferentialAction.SET_NULL,
            "SET_DEFAULT": ReferentialAction.SET_DEFAULT,
            "SET DEFAULT": ReferentialAction.SET_DEFAULT,
        }
        fk_map: Dict[str, ForeignKeyInfo] = {}
        for row in rows:
            fk_name = row.get("CONSTRAINT_NAME", "")
            if fk_name not in fk_map:
                on_update_raw = (row.get("UPDATE_RULE") or "NO ACTION").upper()
                on_delete_raw = (row.get("DELETE_RULE") or "NO ACTION").upper()
                fk_map[fk_name] = ForeignKeyInfo(
                    name=fk_name,
                    table_name=table_name,
                    schema=schema,
                    referenced_table=row.get("REFERENCED_TABLE_NAME", ""),
                    on_update=action_map.get(on_update_raw, ReferentialAction.NO_ACTION),
                    on_delete=action_map.get(on_delete_raw, ReferentialAction.NO_ACTION),
                    columns=[],
                    referenced_columns=[],
                )
            fk_map[fk_name].columns.append(row.get("COLUMN_NAME", ""))
            fk_map[fk_name].referenced_columns.append(row.get("REFERENCED_COLUMN_NAME", ""))
        return list(fk_map.values())

    def _parse_views(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[ViewInfo]:
        return [
            ViewInfo(
                name=row.get("TABLE_NAME", row.get("VIEW_NAME", "")),
                schema=schema,
                definition=row.get("VIEW_DEFINITION"),
                check_option=row.get("CHECK_OPTION"),
                is_updatable=row.get("IS_UPDATABLE") == "YES",
            )
            for row in rows
        ]

    def _parse_view_info(
        self,
        rows: List[Dict[str, Any]],
        view_name: str,
        schema: str,
    ) -> Optional[ViewInfo]:
        if not rows:
            return None
        row = rows[0]
        return ViewInfo(
            name=row.get("TABLE_NAME", row.get("VIEW_NAME", view_name)),
            schema=schema,
            definition=row.get("VIEW_DEFINITION"),
            check_option=row.get("CHECK_OPTION"),
            is_updatable=row.get("IS_UPDATABLE") == "YES",
        )

    def _parse_triggers(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[TriggerInfo]:
        return [
            TriggerInfo(
                name=row.get("TRIGGER_NAME", ""),
                table_name=row.get("EVENT_OBJECT_TABLE", ""),
                schema=schema,
                timing=row.get("ACTION_TIMING"),
                events=[row["EVENT_MANIPULATION"]] if row.get("EVENT_MANIPULATION") else [],
                definition=row.get("ACTION_STATEMENT"),
            )
            for row in rows
        ]


class SyncMariaDBIntrospector(MariaDBIntrospectorMixin, SyncAbstractIntrospector):
    """Synchronous introspector for MariaDB backends.

    In addition to the standard SyncAbstractIntrospector interface, exposes the
    ``.show`` sub-introspector for direct SHOW command access::

        # Standard API
        tables = backend.introspector.list_tables()

        # MariaDB-specific
        create_sql = backend.introspector.show.create_table("users")
        variables  = backend.introspector.show.variables(like="max_%")
    """

    def __init__(self, backend: Any, executor: SyncIntrospectorExecutor) -> None:
        super().__init__(backend, executor)
        self._show_instance: Optional[SyncShowIntrospector] = None
        self._status_instance: Optional[SyncMariaDBStatusIntrospector] = None

    @property
    def show(self) -> SyncShowIntrospector:
        """MariaDB-specific SHOW sub-introspector (lazily created)."""
        if self._show_instance is None:
            self._show_instance = SyncShowIntrospector(self._backend, self._executor)
        return self._show_instance

    @property
    def status(self) -> SyncMariaDBStatusIntrospector:
        """MariaDB server status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = SyncMariaDBStatusIntrospector(self._backend)
        return self._status_instance

    # ------------------------------------------------------------------ #
    # get_table_info override
    # ------------------------------------------------------------------ #

    def get_table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableInfo]:
        key = self._make_cache_key(
            IntrospectionScope.TABLE, table_name, schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        tables = self.list_tables(schema)
        table = next((t for t in tables if t.name == table_name), None)
        if table is None:
            return None

        table = copy.copy(table)
        table.columns = self.list_columns(table_name, schema)
        table.indexes = self.list_indexes(table_name, schema)
        table.foreign_keys = self.list_foreign_keys(table_name, schema)
        self._set_cached(key, table)
        return table


class AsyncMariaDBIntrospector(MariaDBIntrospectorMixin, AsyncAbstractIntrospector):
    """Asynchronous introspector for MariaDB backends.

    In addition to the standard AsyncAbstractIntrospector interface, exposes the
    ``.show`` sub-introspector for direct SHOW command access::

        # Standard API
        tables = await backend.introspector.list_tables()

        # MariaDB-specific
        create_sql = await backend.introspector.show.create_table("users")
        variables  = await backend.introspector.show.variables(like="max_%")
    """

    def __init__(self, backend: Any, executor: AsyncIntrospectorExecutor) -> None:
        super().__init__(backend, executor)
        self._show_instance: Optional[AsyncShowIntrospector] = None
        self._status_instance: Optional[AsyncMariaDBStatusIntrospector] = None

    @property
    def show(self) -> AsyncShowIntrospector:
        """MariaDB-specific SHOW sub-introspector (lazily created)."""
        if self._show_instance is None:
            self._show_instance = AsyncShowIntrospector(self._backend, self._executor)
        return self._show_instance

    @property
    def status(self) -> AsyncMariaDBStatusIntrospector:
        """MariaDB server status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = AsyncMariaDBStatusIntrospector(self._backend)
        return self._status_instance

    # ------------------------------------------------------------------ #
    # get_table_info override
    # ------------------------------------------------------------------ #

    async def get_table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableInfo]:
        key = self._make_cache_key(
            IntrospectionScope.TABLE, table_name, schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        tables = await self.list_tables(schema)
        table = next((t for t in tables if t.name == table_name), None)
        if table is None:
            return None

        table = copy.copy(table)
        table.columns = await self.list_columns(table_name, schema)
        table.indexes = await self.list_indexes(table_name, schema)
        table.foreign_keys = await self.list_foreign_keys(table_name, schema)
        self._set_cached(key, table)
        return table
