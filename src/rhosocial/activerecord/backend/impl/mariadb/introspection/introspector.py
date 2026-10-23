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
  - Queries information_schema.TABLES/SEQUENCES for the two MariaDB-only
    families: sequences (10.3+; numeric details 11.7+) and table options
  - _parse_* methods are pure Python — shared by sync and async introspectors

Design principle: Sync and Async are separate and cannot coexist.
- SyncMariaDBIntrospector: for synchronous backends
- AsyncMariaDBIntrospector: for asynchronous backends
"""

import copy
import warnings
from typing import Any, Dict, List, Optional

from rhosocial.activerecord.backend.expression.types import DataType
from rhosocial.activerecord.backend.introspection.base import (
    IntrospectorMixin,
    SyncAbstractIntrospector,
    AsyncAbstractIntrospector,
)
from rhosocial.activerecord.backend.introspection.cache import IntrospectionCache
from rhosocial.activerecord.backend.introspection.executor import (
    SyncIntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import (
    IntrospectionDatabaseInfo,
    IntrospectionTableInfo,
    TableType,
    IntrospectionColumnInfo,
    ColumnNullable,
    IndexInfo,
    IndexColumnInfo,
    IndexType,
    IntrospectionForeignKeyInfo,
    ReferentialAction,
    IntrospectionViewInfo,
    IntrospectionTriggerInfo,
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
from .types import SequenceInfo, TableOptionsInfo
from ..mixins.introspection import SEQUENCES_SINCE


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

    def _parse_database_info(self, rows: List[Dict[str, Any]]) -> IntrospectionDatabaseInfo:
        version = self._get_version()
        version_str = ".".join(str(v) for v in version)
        db_name = self._get_default_schema()

        db_row = rows[0] if rows else {}

        return IntrospectionDatabaseInfo(
            name=db_name,
            version=version_str,
            version_tuple=version,
            vendor="MariaDB",  # 与 MySQL 的主要差异
            encoding=db_row.get("DEFAULT_CHARACTER_SET_NAME"),
            collation=db_row.get("DEFAULT_COLLATION_NAME"),
        )

    def _parse_tables(
        self, rows: List[Dict[str, Any]], schema: Optional[str]
    ) -> List[IntrospectionTableInfo]:
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
                IntrospectionTableInfo(
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

    def _parse_data_type(self, col_type: str) -> Optional[DataType]:
        """Read one catalog type string into a ``DataType``, or ``None``.

        Populating ``IntrospectionColumnInfo.parsed_data_type`` is what makes the schema
        differ compare *values* instead of strings. Core's
        ``SchemaDiffer._columns_equivalent`` reads the field twice: when both
        sides carry a type it compares the objects with ``!=``, and only when
        one side is ``None`` does it fall back to comparing the ``data_type``
        string. Every other backend populates it here, via
        ``DataType.parse_data_type_str(dialect, raw)``; MariaDB was the only
        one that left it at its ``None`` default, so on this backend the whole
        type-identity model was inert and the differ compared the base word
        alone -- blind to ``VARCHAR(100)`` vs ``VARCHAR(200)``, to an ``ENUM``'s
        labels, to ``INT`` vs ``INT UNSIGNED``.

        The reason one bad column must not take the table down: ``parse_type``
        ends in ``CustomType``, whose constructor *validates* the raw name as a
        SQL type name and raises ``InvalidTypeNameError`` for anything that is
        not identifier-shaped, and other branches raise ``ValueError`` on
        parameters the server can report that this dialect will not accept. The
        catalog is not under this backend's control -- a MariaDB release can
        add a type, and a restored dump can carry one -- so a single unreadable
        string degrades that one column to the string comparison core already
        implements, and says so, rather than aborting ``list_columns`` for the
        whole table. Measured across all fifteen wired servers (10.2.44 through
        13.1.1) and every type in MariaDB's numeric, string, date/time, spatial
        and JSON vocabularies, no such string exists today: the unmodelled types
        -- ``INET4``, ``INET6``, ``VECTOR(n)`` -- are all plain identifiers and
        come back as ``CustomType``, which is the honest answer for a type this
        backend has no class for. This is the guard, not a repair.

        Returns:
            The parsed type, or ``None`` when the string could not be read at
            all. ``None`` is the field's documented default and the value core's
            differ already treats as "fall back to the string".
        """
        try:
            return DataType.parse_data_type_str(self._backend.dialect, col_type)
        except Exception as exc:  # noqa: BLE001 -- see the docstring
            warnings.warn(
                f"MariaDB reported column type {col_type!r}, which this "
                f"backend's parse_type could not read ({type(exc).__name__}: "
                f"{exc}). That column's parsed_data_type is left unset, so the "
                f"schema differ will compare its data_type string rather than "
                f"the type object. The rest of the table is unaffected.",
                RuntimeWarning,
                stacklevel=2,
            )
            return None

    def _parse_columns(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[IntrospectionColumnInfo]:
        columns = []
        for row in rows:
            nullable = (
                ColumnNullable.NULLABLE
                if row.get("IS_NULLABLE") == "YES"
                else ColumnNullable.NOT_NULL
            )
            col_type = row.get("COLUMN_TYPE") or row.get("DATA_TYPE") or "VARCHAR"
            # A spatial column's declared reference system is not in
            # COLUMN_TYPE: MariaDB reports the bare `point` and keeps the
            # declaration only in I_S.GEOMETRY_COLUMNS.SRID (the column query
            # joins that view; measured on 10.2.44 and 13.1.1). Fold a
            # non-zero SRID back into the type text so the parsed type is the
            # declared one and the differ sees a reference-system change. SRID
            # 0 is MariaDB's default -- what a bare spatial column reports --
            # so it means "no declaration" (srid=None) rather than the
            # distinct REF_SYSTEM_ID=0 value object the server cannot tell
            # apart from it.
            full_type = col_type
            srid = row.get("SRID")
            if srid is not None and int(srid) != 0:
                full_type = f"{col_type} REF_SYSTEM_ID={int(srid)}"
            columns.append(
                IntrospectionColumnInfo(
                    name=row["COLUMN_NAME"],
                    table_name=table_name,
                    schema=schema,
                    ordinal_position=row["ORDINAL_POSITION"],
                    data_type=col_type.split("(")[0].lower(),
                    data_type_full=full_type,
                    parsed_data_type=self._parse_data_type(full_type),
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
    ) -> List[IntrospectionForeignKeyInfo]:
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
        fk_map: Dict[str, IntrospectionForeignKeyInfo] = {}
        for row in rows:
            fk_name = row.get("CONSTRAINT_NAME", "")
            if fk_name not in fk_map:
                on_update_raw = (row.get("UPDATE_RULE") or "NO ACTION").upper()
                on_delete_raw = (row.get("DELETE_RULE") or "NO ACTION").upper()
                fk_map[fk_name] = IntrospectionForeignKeyInfo(
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
    ) -> List[IntrospectionViewInfo]:
        return [
            IntrospectionViewInfo(
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
    ) -> Optional[IntrospectionViewInfo]:
        if not rows:
            return None
        row = rows[0]
        return IntrospectionViewInfo(
            name=row.get("TABLE_NAME", row.get("VIEW_NAME", view_name)),
            schema=schema,
            definition=row.get("VIEW_DEFINITION"),
            check_option=row.get("CHECK_OPTION"),
            is_updatable=row.get("IS_UPDATABLE") == "YES",
        )

    def _parse_triggers(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[IntrospectionTriggerInfo]:
        return [
            IntrospectionTriggerInfo(
                name=row.get("TRIGGER_NAME", ""),
                table_name=row.get("EVENT_OBJECT_TABLE", ""),
                schema=schema,
                timing=row.get("ACTION_TIMING"),
                events=[row["EVENT_MANIPULATION"]] if row.get("EVENT_MANIPULATION") else [],
                definition=row.get("ACTION_STATEMENT"),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------ #
    # MariaDB-only families: sequences and table options
    # ------------------------------------------------------------------ #

    @staticmethod
    def _as_int(value: Any) -> Optional[int]:
        """Read one catalogue integer, keeping "not reported" as ``None``.

        ``information_schema`` reports these as ``Decimal``, and on a server
        without ``information_schema.SEQUENCES`` the column is not in the row
        at all. Both mean "this server told us nothing", which is exactly what
        the typed field's ``None`` says, so everything else is coerced and
        nothing is defaulted.
        """
        return None if value is None else int(value)

    @staticmethod
    def _as_cycle(value: Any) -> Optional[bool]:
        """Read ``CYCLE_OPTION``; MariaDB spells it ``'1'`` / ``'0'``."""
        if value is None:
            return None
        return str(value).strip().lower() in ("1", "y", "yes", "true")

    def _parse_sequence_row(self, row: Dict[str, Any], schema: str) -> SequenceInfo:
        """Read one ``TABLES``/``SEQUENCES`` row into a :class:`SequenceInfo`.

        The detail columns are read with ``.get`` because the query only names
        them on servers that have the view; on older servers their absence is
        the answer, not a parsing error.
        """
        return SequenceInfo(
            name=row.get("TABLE_NAME", ""),
            schema=schema,
            start_value=self._as_int(row.get("START_VALUE")),
            minimum_value=self._as_int(row.get("MINIMUM_VALUE")),
            maximum_value=self._as_int(row.get("MAXIMUM_VALUE")),
            increment=self._as_int(row.get("INCREMENT")),
            cycle=self._as_cycle(row.get("CYCLE_OPTION")),
            # No information_schema view carries a sequence's cache size: it
            # survives only in the text of SHOW CREATE SEQUENCE. Reported as
            # not exposed rather than parsed out of a different kind of source.
            cache_size=None,
            data_type=row.get("DATA_TYPE"),
        )

    def _parse_sequences(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[SequenceInfo]:
        return [self._parse_sequence_row(row, schema) for row in rows]

    def _parse_sequence_info(
        self, rows: List[Dict[str, Any]], name: str, schema: str
    ) -> Optional[SequenceInfo]:
        if not rows:
            return None
        return self._parse_sequence_row(rows[0], schema)

    def _parse_table_options(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[TableOptionsInfo]:
        return [self._parse_table_options_row(row, schema) for row in rows]

    @staticmethod
    def _parse_table_options_row(
        row: Dict[str, Any], schema: str
    ) -> TableOptionsInfo:
        auto_increment = row.get("AUTO_INCREMENT")
        return TableOptionsInfo(
            name=row.get("TABLE_NAME", ""),
            schema=schema,
            table_type=row.get("TABLE_TYPE"),
            engine=row.get("ENGINE"),
            row_format=row.get("ROW_FORMAT"),
            collation=row.get("TABLE_COLLATION"),
            auto_increment=None if auto_increment is None else int(auto_increment),
            comment=row.get("TABLE_COMMENT"),
            create_options=row.get("CREATE_OPTIONS"),
        )

    def _parse_table_options_info(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> Optional[TableOptionsInfo]:
        if not rows:
            return None
        return self._parse_table_options_row(rows[0], schema)

    # ------------------------------------------------------------------ #
    # SQL building — one node per question, rendered by the dialect
    # ------------------------------------------------------------------ #

    def _sequence_target_schema(self, schema: Optional[str]) -> str:
        return schema if schema is not None else self._get_default_schema()

    def _build_sequence_list_sql(self, schema: Optional[str]) -> tuple:
        from ..expression.introspection import MariaDBSequenceQuery

        expr = MariaDBSequenceQuery(self.dialect, self._sequence_target_schema(schema))
        return expr.to_sql()

    def _build_sequence_info_sql(self, name: str, schema: Optional[str]) -> tuple:
        from ..expression.introspection import MariaDBSequenceQuery

        expr = MariaDBSequenceQuery(
            self.dialect, self._sequence_target_schema(schema), name=name
        )
        return expr.to_sql()

    def _build_table_options_sql(
        self, table_name: Optional[str], schema: Optional[str]
    ) -> tuple:
        from ..expression.introspection import MariaDBTableOptionsQuery

        expr = MariaDBTableOptionsQuery(
            self.dialect, self._sequence_target_schema(schema), table_name=table_name
        )
        return expr.to_sql()


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

    def __init__(
        self,
        backend: Any,
        executor: SyncIntrospectorExecutor,
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)
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
    ) -> Optional[IntrospectionTableInfo]:
        key = self._cache.key(
            IntrospectionScope.TABLE, table_name, schema=schema
        )
        cached = self._cache.get(key)
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
        self._cache.set(key, table)
        return table

    # ------------------------------------------------------------------ #
    # MariaDB-only families: sequences and table options
    # ------------------------------------------------------------------ #

    def list_sequences(self, schema: Optional[str] = None) -> List[SequenceInfo]:
        """List the sequences in *schema*.

        Read from ``information_schema.TABLES`` where ``TABLE_TYPE='SEQUENCE'``,
        because a sequence is a table on MariaDB. The numeric facts come from
        ``information_schema.SEQUENCES`` when the server has that view (11.7+)
        and are ``None`` on older servers; see :class:`SequenceInfo`.

        Servers older than 10.3 cannot hold a sequence, so the answer there is
        an empty list and no query is sent -- the cache entry is still written,
        so asking twice costs nothing.

        The result shares ``IntrospectionScope.SEQUENCE`` with nothing else, but
        carries the ``mariadb`` namespace so a generic sequence list added to
        core later cannot answer this one's cache entry.
        """
        key = self._cache.key(
            IntrospectionScope.SEQUENCE, schema=schema, extra="mariadb"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        if self._get_version() < SEQUENCES_SINCE:
            result: List[SequenceInfo] = []
        else:
            sql, params = self._build_sequence_list_sql(schema)
            result = self._parse_sequences(
                self._executor.execute(sql, params),
                self._sequence_target_schema(schema),
            )
        self._cache.set(key, result)
        return result

    def get_sequence_info(
        self, name: str, schema: Optional[str] = None
    ) -> Optional[SequenceInfo]:
        """Return the named sequence, or ``None`` when it does not exist.

        A miss is not cached: this backend's other lookups by name follow the
        same rule, and caching an absence would keep a sequence invisible
        after the next ``CREATE SEQUENCE``.
        """
        key = self._cache.key(
            IntrospectionScope.SEQUENCE, name, schema=schema, extra="mariadb"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        if self._get_version() < SEQUENCES_SINCE:
            return None
        sql, params = self._build_sequence_info_sql(name, schema)
        result = self._parse_sequence_info(
            self._executor.execute(sql, params),
            name,
            self._sequence_target_schema(schema),
        )
        if result is not None:
            self._cache.set(key, result)
        return result

    def list_table_options(
        self, schema: Optional[str] = None
    ) -> List[TableOptionsInfo]:
        """List the storage options of every relation in *schema*.

        ``information_schema.TABLES`` holds base tables, views and sequences in
        one list, and every row is returned with its ``table_type``; a caller
        wanting only base tables filters on that rather than having the family
        hidden here.

        The cache entry lives under ``IntrospectionScope.TABLE`` -- these are
        table facts -- with its own ``mariadb:table-options`` namespace, so it
        cannot be answered by (or answer) the generic table list.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, schema=schema, extra="mariadb:table-options"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self._build_table_options_sql(None, schema)
        result = self._parse_table_options(
            self._executor.execute(sql, params),
            self._sequence_target_schema(schema),
        )
        self._cache.set(key, result)
        return result

    def get_table_options(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableOptionsInfo]:
        """Return the storage options of one relation, or ``None``."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name,
            schema=schema,
            extra="mariadb:table-options",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self._build_table_options_sql(table_name, schema)
        result = self._parse_table_options_info(
            self._executor.execute(sql, params),
            table_name,
            self._sequence_target_schema(schema),
        )
        if result is not None:
            self._cache.set(key, result)
        return result


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

    def __init__(
        self,
        backend: Any,
        executor: AsyncIntrospectorExecutor,
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)
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
    ) -> Optional[IntrospectionTableInfo]:
        key = self._cache.key(
            IntrospectionScope.TABLE, table_name, schema=schema
        )
        cached = self._cache.get(key)
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
        self._cache.set(key, table)
        return table

    # ------------------------------------------------------------------ #
    # MariaDB-only families: sequences and table options
    # ------------------------------------------------------------------ #

    async def list_sequences(self, schema: Optional[str] = None) -> List[SequenceInfo]:
        """List the sequences in *schema*.

        Read from ``information_schema.TABLES`` where ``TABLE_TYPE='SEQUENCE'``,
        because a sequence is a table on MariaDB. The numeric facts come from
        ``information_schema.SEQUENCES`` when the server has that view (11.7+)
        and are ``None`` on older servers; see :class:`SequenceInfo`.

        Servers older than 10.3 cannot hold a sequence, so the answer there is
        an empty list and no query is sent -- the cache entry is still written,
        so asking twice costs nothing.
        """
        key = self._cache.key(
            IntrospectionScope.SEQUENCE, schema=schema, extra="mariadb"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        if self._get_version() < SEQUENCES_SINCE:
            result: List[SequenceInfo] = []
        else:
            sql, params = self._build_sequence_list_sql(schema)
            result = self._parse_sequences(
                await self._executor.execute(sql, params),
                self._sequence_target_schema(schema),
            )
        self._cache.set(key, result)
        return result

    async def get_sequence_info(
        self, name: str, schema: Optional[str] = None
    ) -> Optional[SequenceInfo]:
        """Return the named sequence, or ``None`` when it does not exist."""
        key = self._cache.key(
            IntrospectionScope.SEQUENCE, name, schema=schema, extra="mariadb"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        if self._get_version() < SEQUENCES_SINCE:
            return None
        sql, params = self._build_sequence_info_sql(name, schema)
        result = self._parse_sequence_info(
            await self._executor.execute(sql, params),
            name,
            self._sequence_target_schema(schema),
        )
        if result is not None:
            self._cache.set(key, result)
        return result

    async def list_table_options(
        self, schema: Optional[str] = None
    ) -> List[TableOptionsInfo]:
        """List the storage options of every relation in *schema*.

        ``information_schema.TABLES`` holds base tables, views and sequences in
        one list, and every row is returned with its ``table_type``; a caller
        wanting only base tables filters on that rather than having the family
        hidden here.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, schema=schema, extra="mariadb:table-options"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self._build_table_options_sql(None, schema)
        result = self._parse_table_options(
            await self._executor.execute(sql, params),
            self._sequence_target_schema(schema),
        )
        self._cache.set(key, result)
        return result

    async def get_table_options(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableOptionsInfo]:
        """Return the storage options of one relation, or ``None``."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name,
            schema=schema,
            extra="mariadb:table-options",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self._build_table_options_sql(table_name, schema)
        result = self._parse_table_options_info(
            await self._executor.execute(sql, params),
            table_name,
            self._sequence_target_schema(schema),
        )
        if result is not None:
            self._cache.set(key, result)
        return result
