# src/rhosocial/activerecord/backend/impl/mariadb/introspection/introspector.py
"""
MariaDB concrete introspectors.

Implements AbstractIntrospector and AsyncAbstractIntrospector for MariaDB
databases using the information_schema system tables for metadata queries.

The introspectors are exposed via ``backend.introspector`` and also provide
MariaDB-specific access through ``backend.introspector.show``.

Architecture:
  - SQL generation: Delegated to MariaDBIntrospectionMixin.format_*_query()
    methods in the Dialect layer via Expression.to_sql()
  - Query execution: Handled by IntrospectorExecutor
  - Result parsing: parse_* methods in this module (pure Python, no I/O)

Key behaviours:
  - Queries information_schema.TABLES, COLUMNS, STATISTICS,
    KEY_COLUMN_USAGE, REFERENTIAL_CONSTRAINTS, VIEWS, TRIGGERS
  - Queries information_schema.TABLES/SEQUENCES for the two MariaDB-only
    families: sequences (10.3+; numeric details 11.7+) and table options
  - Answers the dependency family from REFERENTIAL_CONSTRAINTS (foreign
    keys only) and the DDL family from SHOW CREATE TABLE, whose result
    columns are the engine's own spellings (see parse_ddl_statements)
  - parse_* methods are pure Python — shared by sync and async introspectors

Design principle: Sync and Async are separate and cannot coexist.
- MariaDBIntrospector: for synchronous backends
- AsyncMariaDBIntrospector: for asynchronous backends
"""

import copy
import warnings
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.types import DataType
from rhosocial.activerecord.backend.introspection.base import (
    IntrospectorMixin,
    AbstractIntrospector,
    AsyncAbstractIntrospector,
)
from rhosocial.activerecord.backend.introspection.cache import IntrospectionCache
from rhosocial.activerecord.backend.introspection.executor import (
    IntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import (
    ConstraintState,
    DerivedObjectState,
    IndexState,
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
    ItemKind,
    PartitionBound,
    PartitionScheme,
    PartitionState,
    SequenceState,
    StorageOptionsState,
    TableState,
    DDLStatement,
)
from rhosocial.activerecord.backend.introspection.errors import ObjectNotFoundError
from .show_introspector import (
    ShowIntrospector,
    AsyncShowIntrospector,
)
from .status_introspector import (
    MariaDBStatusIntrospector,
    AsyncMariaDBStatusIntrospector,
)
from .type_parser import MariaDBTypeParser
from .types import (
    SequenceInfo,
    TableOptionsInfo,
    MariaDBPartitionInfo,
    MariaDBRoutineInfo,
    MariaDBRoutineParameterInfo,
    MariaDBConstraintInfo,
)
from ..mixins.introspection import SEQUENCES_SINCE

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.introspection import (
        MariaDBSequenceQuery,
        MariaDBTableOptionsQuery,
        MariaDBPartitionQuery,
        MariaDBRoutineQuery,
        MariaDBConstraintQuery,
    )


class MariaDBIntrospectorMixin(IntrospectorMixin):
    """Mixin providing shared MariaDB-specific introspection logic.

    Both MariaDBIntrospector and AsyncMariaDBIntrospector inherit
    from this mixin to share:
    - Default schema handling
    - The version a database record reports (``server_version``)
    - parse_* implementations

    SQL generation is delegated to the Dialect layer via Expression.to_sql()
    which calls MariaDBIntrospectionMixin.format_*_query() methods.
    """

    #: Kinds of shared object MariaDB holds and this backend can query by name.
    #: ``item_exists`` answers every one of them from the catalogue.
    ITEM_KINDS_QUERIED = frozenset(
        {
            ItemKind.SCHEMA,
            ItemKind.TABLE,
            ItemKind.SEQUENCE,
            ItemKind.FUNCTION,
        }
    )

    #: Engine kinds this backend holds but has no name-only catalogue query
    #: for. MariaDB names an index under its table, so a bare index name cannot
    #: be resolved; asking is refused rather than answered.
    ITEM_KINDS_REFUSED = frozenset({ItemKind.INDEX})

    #: Shared object kinds MariaDB does not have at all. ``item_exists``
    #: answers ``False``: there is none, not "cannot tell".
    ITEM_KINDS_ABSENT = frozenset(
        {
            ItemKind.TYPE,
            ItemKind.DOMAIN,
            ItemKind.EXTENSION,
            ItemKind.TABLESPACE,
            ItemKind.PARTITION_FUNCTION,
            ItemKind.PARTITION_SCHEME,
            ItemKind.FULLTEXT_CATALOG,
        }
    )

    @property
    def default_schema(self) -> str:
        """Return the MariaDB database name from the backend config."""
        if hasattr(self._backend, 'config') and hasattr(self._backend.config, 'database'):
            return self._backend.config.database or ""
        return ""

    def _refuse_item_exists(self, kind: ItemKind) -> None:
        """Refuse a kind this backend cannot resolve from the catalogue.

        The import stays local, as in core's ``_refuse``: ``dialect.exceptions``
        pulls in the dialect package, which imports back into this layer.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )

        kind_name = kind.value if isinstance(kind, ItemKind) else str(kind)
        raise UnsupportedFeatureError(
            self.dialect.name, f"item_exists({kind_name})"
        )

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O
    # ------------------------------------------------------------------ #

    def parse_database_info(self, rows: List[Dict[str, Any]]) -> IntrospectionDatabaseInfo:
        """Turn the schema row into a database record.

        The version comes from :attr:`server_version`, not from the strict
        ``dialect.version`` or a backend private: a parser has no connection
        to ask, and refusing to describe a database until
        ``introspect_and_adapt()`` has run would make the answer depend on a
        step the caller did not need. An unresolved version is reported as
        the literal ``"unknown"`` with ``(0, 0, 0)`` -- distinguishable from
        a server that really is 0.0.0 -- rather than a fabricated default.

        ``encoding`` and ``collation`` are the two columns the statement
        selects. ``table_count`` and ``size_bytes`` are not among them: they
        live in ``information_schema.TABLES``, so they stay ``None`` rather
        than being guessed here.
        """
        version = self.server_version
        db_row = rows[0] if rows else {}

        return IntrospectionDatabaseInfo(
            name=self.default_schema,
            version=".".join(str(part) for part in version) if version else "unknown",
            version_tuple=tuple(version) if version else (0, 0, 0),
            vendor="MariaDB",
            encoding=db_row.get("DEFAULT_CHARACTER_SET_NAME"),
            collation=db_row.get("DEFAULT_COLLATION_NAME"),
        )

    def parse_tables(
        self, rows: List[Dict[str, Any]], schema: Optional[str]
    ) -> List[IntrospectionTableInfo]:
        """Read ``information_schema.TABLES`` rows into table records.

        ``SEQUENCE`` is deliberately absent from the type map below: a
        sequence row never reaches this parser, because the table-list
        statement excludes the spelling (pin: the ``<> 'SEQUENCE'`` condition
        in ``format_table_list_query_statement``), and the family is reported
        by ``list_sequences`` instead. ``TableType`` has no member
        for it either, so a row that somehow arrived would fall through to the
        ``BASE_TABLE`` default rather than be invented as a kind of its own.
        Keeping the fallback is what lets a spelling a later MariaDB release
        adds still appear in the listing instead of failing it.

        The storage slots are filled from the two columns the statement
        reads: ``DATA_LENGTH`` into ``data_size_bytes``, ``INDEX_LENGTH``
        into ``index_size_bytes``, and their sum into ``size_bytes``. A
        server that reports neither column -- a view has no storage and
        reports ``NULL`` -- leaves all three ``None``, because a value the
        catalog did not report is not a zero-byte table (rules §5: an
        engine that cannot answer a slot leaves it ``None``, which is a
        legal answer rather than a gap).
        """
        target_db = schema if schema is not None else self.default_schema
        table_type_map = {
            "BASE TABLE": TableType.BASE_TABLE,
            "VIEW": TableType.VIEW,
            "SYSTEM VIEW": TableType.SYSTEM_TABLE,
        }
        tables = []
        for row in rows:
            t_type = table_type_map.get(row.get("TABLE_TYPE", "BASE TABLE"), TableType.BASE_TABLE)
            data_length = self._as_int(row.get("DATA_LENGTH"))
            index_length = self._as_int(row.get("INDEX_LENGTH"))
            reported = [size for size in (data_length, index_length) if size is not None]
            tables.append(
                IntrospectionTableInfo(
                    name=row["TABLE_NAME"],
                    schema=target_db,
                    table_type=t_type,
                    comment=row.get("TABLE_COMMENT"),
                    row_count=row.get("TABLE_ROWS"),
                    size_bytes=sum(reported) if reported else None,
                    data_size_bytes=data_length,
                    index_size_bytes=index_length,
                    auto_increment=row.get("AUTO_INCREMENT"),
                    create_time=str(row["CREATE_TIME"]) if row.get("CREATE_TIME") else None,
                    update_time=str(row["UPDATE_TIME"]) if row.get("UPDATE_TIME") else None,
                )
            )
        return tables

    def parse_data_type(self, col_type: str) -> Optional[DataType]:
        """Read one catalog type string into a ``DataType``, or ``None``.

        Populating ``IntrospectionColumnInfo.parsed_data_type`` is what makes the schema
        differ compare *values* instead of strings. Core's
        ``SchemaDiffer._columns_equivalent`` reads the field twice: when both
        sides carry a type it compares the objects with ``!=``, and only when
        one side is ``None`` does it fall back to comparing the ``data_type``
        string. Core's ``DataType.parse_data_type_str`` is now a fallback that
        only builds a ``CustomType``; real parsing is this backend's
        introspection parser (``type_parser.MariaDBTypeParser``). MariaDB was
        the only backend that left the field at its ``None`` default, so on this
        backend the whole
        type-identity model was inert and the differ compared the base word
        alone -- blind to ``VARCHAR(100)`` vs ``VARCHAR(200)``, to an ``ENUM``'s
        labels, to ``INT`` vs ``INT UNSIGNED``.

        The reason one bad column must not take the table down: the backend's
        introspection parser ends in ``CustomType``, whose constructor
        *validates* the raw name as a SQL type name and raises
        ``InvalidTypeNameError`` for anything that is
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
            return MariaDBTypeParser(self._backend.dialect).parse(col_type)
        except Exception as exc:  # noqa: BLE001 -- see the docstring
            warnings.warn(
                f"MariaDB reported column type {col_type!r}, which this "
                f"backend's introspection parser could not read ({type(exc).__name__}: "
                f"{exc}). That column's parsed_data_type is left unset, so the "
                f"schema differ will compare its data_type string rather than "
                f"the type object. The rest of the table is unaffected.",
                RuntimeWarning,
                stacklevel=2,
            )
            return None

    def parse_columns(
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
                    parsed_data_type=self.parse_data_type(full_type),
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

    def parse_indexes(
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

    def parse_foreign_keys(
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

    def parse_views(
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

    def parse_view_info(
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

    def parse_triggers(
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
    # MariaDB-only families: partitions, routines and CHECK constraints
    # ------------------------------------------------------------------ #

    def parse_partitions(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[MariaDBPartitionInfo]:
        """Read ``information_schema.PARTITIONS`` rows into partition records.

        The view reports one row per partition, or per (partition,
        subpartition) pair. The statement has already excluded the
        NULL-partition row a non-partitioned table carries, so every row here
        is a real partition and no sentinel is invented.
        """
        return [
            MariaDBPartitionInfo(
                schema=row.get("TABLE_SCHEMA") or schema,
                table_name=row.get("TABLE_NAME") or table_name,
                partition_name=row.get("PARTITION_NAME"),
                subpartition_name=row.get("SUBPARTITION_NAME"),
                partition_method=row.get("PARTITION_METHOD"),
                subpartition_method=row.get("SUBPARTITION_METHOD"),
                partition_expression=row.get("PARTITION_EXPRESSION"),
                subpartition_expression=row.get("SUBPARTITION_EXPRESSION"),
                partition_description=row.get("PARTITION_DESCRIPTION"),
                subpartition_description=row.get("SUBPARTITION_DESCRIPTION"),
                partition_ordinal_position=self._as_int(
                    row.get("PARTITION_ORDINAL_POSITION")
                ),
                subpartition_ordinal_position=self._as_int(
                    row.get("SUBPARTITION_ORDINAL_POSITION")
                ),
                table_rows=self._as_int(row.get("TABLE_ROWS")),
                data_length=self._as_int(row.get("DATA_LENGTH")),
                index_length=self._as_int(row.get("INDEX_LENGTH")),
                partition_comment=row.get("PARTITION_COMMENT"),
            )
            for row in rows
        ]

    def parse_partition_state(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
        include_stats: bool = False,
    ) -> PartitionState:
        """Read ``PARTITIONS`` rows into the neutral partition state.

        One row is a partition, or one of a subpartitioned partition's
        subpartitions. They are folded back onto the top-level partition the
        neutral shape describes: a subpartitioned table answers one
        :class:`PartitionBound` per partition with ``subpartition_count`` set,
        and its overall ``scheme`` is ``COMPOSITE``. The statement's ordinal
        ordering is preserved, so bounds list in the engine's own order.

        ``partition_description`` is the RANGE/LIST boundary. For RANGE it is
        the upper bound and is kept verbatim; for LIST it is the comma-separated
        value list and is split into ``values``. ``MAXVALUE`` (and the
        ``MAXINTEGER`` spelling the catalogue documents) marks the catch-all
        partition. ``SYSTEM_TIME`` partitions use the description for a history
        partition's upper timestamp and the literal ``CURRENT`` for the live
        partition, which is the scheme's default partition.

        ``include_stats`` controls whether the row counters are read. It must
        agree with the statement's projection: when ``False`` the columns are
        not in the rows at all, and every statistic slot stays ``None``.
        """
        groups: Dict[str, List[Dict[str, Any]]] = {}
        order: List[str] = []
        for row in rows:
            name = row.get("PARTITION_NAME")
            if name is None:
                continue
            if name not in groups:
                groups[name] = []
                order.append(name)
            groups[name].append(row)

        if not order:
            return PartitionState()

        first = rows[0]
        first_method = first.get("PARTITION_METHOD") or ""
        first_expression = first.get("PARTITION_EXPRESSION") or ""
        subpartition_method = next(
            (
                row.get("SUBPARTITION_METHOD")
                for row in rows
                if row.get("SUBPARTITION_METHOD")
            ),
            None,
        )
        bounds: List[PartitionBound] = []
        has_default = False
        for name in order:
            group = groups[name]
            representative = next(
                (row for row in group if row.get("SUBPARTITION_NAME") is None),
                group[0],
            )
            top_method = (
                representative.get("PARTITION_METHOD") or first_method
            ).upper()
            description = representative.get("PARTITION_DESCRIPTION")
            upper: Optional[str] = None
            values: Tuple[str, ...] = ()
            is_maxvalue = False
            is_default = False
            if top_method in ("RANGE", "RANGE COLUMNS", "SYSTEM_TIME"):
                upper = description
                token = (description or "").upper()
                is_maxvalue = "MAXVALUE" in token or "MAXINTEGER" in token
                is_default = token in ("CURRENT", "DEFAULT")
            elif top_method in ("LIST", "LIST COLUMNS"):
                values = self._partition_list_values(description)
                is_default = (description or "").upper() == "DEFAULT"

            subpartition_count = (
                len(group)
                if any(row.get("SUBPARTITION_NAME") is not None for row in group)
                else 0
            )
            if include_stats:
                row_count = self._as_int(representative.get("TABLE_ROWS"))
                data_length = self._as_int(representative.get("DATA_LENGTH"))
                index_length = self._as_int(representative.get("INDEX_LENGTH"))
                reported = [
                    size for size in (data_length, index_length) if size is not None
                ]
                size_bytes = sum(reported) if reported else None
            else:
                row_count = None
                size_bytes = None

            bounds.append(
                PartitionBound(
                    name=name,
                    upper=upper,
                    values=values,
                    is_default=is_default,
                    is_maxvalue=is_maxvalue,
                    row_count=row_count,
                    size_bytes=size_bytes,
                    subpartition_count=subpartition_count,
                    tablespace=representative.get("TABLESPACE_NAME") or None,
                )
            )
            if is_default or is_maxvalue:
                has_default = True

        return PartitionState(
            scheme=self._partition_scheme(first_method, subpartition_method),
            key_expression=first_expression,
            key_columns=self._partition_key_columns(first_expression),
            has_default=has_default,
            # AUTO rotation is not a catalogue column; SHOW CREATE TABLE is the
            # only source and this backend does not parse it here.
            auto_extend=False,
            bounds=tuple(bounds),
            raw={
                "schema": schema,
                "table_name": table_name,
                "partition_method": first_method,
                "subpartition_method": subpartition_method,
                "partition_expression": first_expression,
                "subpartition_expression": first.get("SUBPARTITION_EXPRESSION") or "",
            },
        )

    @staticmethod
    def _partition_scheme(
        method: Optional[str], subpartition_method: Optional[str]
    ) -> Optional[PartitionScheme]:
        """Map MariaDB's method tokens onto the neutral scheme.

        ``LINEAR`` variants are the same splitting scheme to a caller, and the
        ``COLUMNS`` variants still split by range or list; the column versus
        expression distinction survives in ``key_columns``. A subpartition
        method makes the table composite. ``SYSTEM_TIME`` is the history
        rotation scheme, whose partitions carry an interval boundary, so it
        maps onto ``INTERVAL``. Any token this backend has not seen maps onto
        ``EXPRESSION`` rather than ``None``: an unrecognised method still means
        the table is partitioned, and ``None`` is reserved for "not
        partitioned".
        """
        if subpartition_method:
            return PartitionScheme.COMPOSITE
        token = (method or "").upper()
        if token in ("RANGE", "RANGE COLUMNS"):
            return PartitionScheme.RANGE
        if token in ("LIST", "LIST COLUMNS"):
            return PartitionScheme.LIST
        if token in ("HASH", "LINEAR HASH"):
            return PartitionScheme.HASH
        if token in ("KEY", "LINEAR KEY"):
            return PartitionScheme.KEY
        if token == "SYSTEM_TIME":
            return PartitionScheme.INTERVAL
        if token:
            return PartitionScheme.EXPRESSION
        return None

    @staticmethod
    def _partition_key_columns(expression: Optional[str]) -> Tuple[str, ...]:
        """Read a column-list partition expression into its column names.

        ``PARTITION_EXPRESSION`` is column names for the ``COLUMNS`` methods and
        an arbitrary expression otherwise (``YEAR(col)``, ``UNIX_TIMESTAMP``).
        Only an expression that is entirely identifier-shaped column tokens is
        answered; anything else returns ``()`` rather than inventing columns
        out of a function call.
        """
        if not expression:
            return ()
        tokens: List[str] = []
        current: List[str] = []
        depth = 0
        for char in expression:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            if char == "," and depth == 0:
                tokens.append("".join(current))
                current = []
            else:
                current.append(char)
        tokens.append("".join(current))

        columns: List[str] = []
        for token in tokens:
            candidate = token.strip().strip("`").strip()
            if not candidate or candidate[0].isdigit():
                return ()
            if not candidate.replace("_", "").replace("$", "").isalnum():
                return ()
            columns.append(candidate)
        return tuple(columns)

    @staticmethod
    def _partition_list_values(description: Optional[str]) -> Tuple[str, ...]:
        """Split a LIST partition's ``PARTITION_DESCRIPTION`` into its values.

        The description is the comma-separated value list the DDL wrote. A
        quoted value may itself contain a comma, so the split tracks the quote
        character rather than using a bare ``str.split``. Surrounding quotes are
        removed because they are the catalogue's quoting, not part of the value.
        """
        if not description:
            return ()
        parts: List[str] = []
        current: List[str] = []
        quote: Optional[str] = None
        for char in description:
            if quote is not None:
                if char == quote:
                    quote = None
                current.append(char)
            elif char in ("'", '"'):
                quote = char
                current.append(char)
            elif char == ",":
                parts.append("".join(current))
                current = []
            else:
                current.append(char)
        parts.append("".join(current))

        values: List[str] = []
        for part in parts:
            value = part.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            values.append(value)
        return tuple(values)

    def parse_routines(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[MariaDBRoutineInfo]:
        """Read joined ``ROUTINES``/``PARAMETERS`` rows into routine records.

        One row per (routine, parameter) pair arrives from the statement, so
        the parameters are grouped back onto the routine they belong to. The
        grouping key is (schema, name, kind): a procedure and a function may
        share a name, and grouping by name alone would merge their arguments.

        A function's return value is reported by ``PARAMETERS`` at ordinal 0
        and is not an argument. Those rows are skipped here; the return type
        itself comes from ``ROUTINES.DTD_IDENTIFIER``.
        """
        builders: Dict[tuple, Dict[str, Any]] = {}
        for row in rows:
            routine_schema = row.get("ROUTINE_SCHEMA") or schema
            routine_name = row.get("ROUTINE_NAME", "")
            kind = (row.get("ROUTINE_TYPE") or "").upper()
            key = (routine_schema, routine_name, kind)

            builder = builders.get(key)
            if builder is None:
                builder = self._routine_builder(
                    row, routine_schema, routine_name, kind
                )
                builders[key] = builder

            ordinal = self._as_int(row.get("PARAMETER_ORDINAL_POSITION"))
            if ordinal is None or ordinal <= 0:
                continue
            builder["parameters"].append(
                MariaDBRoutineParameterInfo(
                    ordinal_position=ordinal,
                    mode=row.get("PARAMETER_MODE"),
                    name=row.get("PARAMETER_NAME"),
                    data_type=row.get("PARAMETER_DATA_TYPE")
                    or row.get("DATA_TYPE"),
                    data_type_full=row.get("PARAMETER_DTD_IDENTIFIER")
                    or row.get("DTD_IDENTIFIER"),
                )
            )

        return [self._routine_from_builder(builder) for builder in builders.values()]

    def _routine_builder(
        self,
        row: Dict[str, Any],
        schema: str,
        name: str,
        kind: str,
    ) -> Dict[str, Any]:
        """Collect the routine-level slots from the first row of a group."""
        return {
            "schema": schema,
            "name": name,
            "kind": kind,
            "return_type": self._routine_return_type(row, kind),
            "language": row.get("EXTERNAL_LANGUAGE") or row.get("ROUTINE_BODY"),
            "deterministic": self._as_yes_no(row.get("IS_DETERMINISTIC")),
            "sql_data_access": row.get("SQL_DATA_ACCESS"),
            "security_type": row.get("SECURITY_TYPE"),
            "comment": row.get("ROUTINE_COMMENT"),
            "definer": row.get("DEFINER"),
            "created": (
                str(row["CREATED"]) if row.get("CREATED") is not None else None
            ),
            "last_altered": (
                str(row["LAST_ALTERED"])
                if row.get("LAST_ALTERED") is not None
                else None
            ),
            "parameters": [],
        }

    @staticmethod
    def _routine_return_type(row: Dict[str, Any], kind: str) -> Optional[str]:
        """Return a function's declared return type; procedures have none."""
        if kind != "FUNCTION":
            return None
        return (
            row.get("ROUTINE_DTD_IDENTIFIER")
            or row.get("DTD_IDENTIFIER")
            or row.get("ROUTINE_DATA_TYPE")
            or row.get("DATA_TYPE")
            or None
        )

    @staticmethod
    def _routine_from_builder(builder: Dict[str, Any]) -> MariaDBRoutineInfo:
        """Freeze one grouped builder into a result record."""
        return MariaDBRoutineInfo(
            schema=builder["schema"],
            name=builder["name"],
            kind=builder["kind"],
            return_type=builder["return_type"],
            parameters=tuple(builder["parameters"]),
            language=builder["language"],
            deterministic=builder["deterministic"],
            sql_data_access=builder["sql_data_access"],
            security_type=builder["security_type"],
            comment=builder["comment"],
            definer=builder["definer"],
            created=builder["created"],
            last_altered=builder["last_altered"],
        )

    def parse_routine_info(
        self,
        rows: List[Dict[str, Any]],
        name: str,
        schema: str,
        kind: Optional[str] = None,
    ) -> Optional[MariaDBRoutineInfo]:
        """Pick one routine out of the joined rows, or ``None``.

        ``kind`` narrows when a procedure and a function share the name. Left
        out, the first match in the statement's (kind, name) order is
        returned; the statement already narrowed to the name, so this is not
        a guess among unrelated routines.
        """
        for routine in self.parse_routines(rows, schema):
            if routine.name != name:
                continue
            if kind is not None and routine.kind != kind.upper():
                continue
            return routine
        return None

    def parse_constraints(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[MariaDBConstraintInfo]:
        """Read joined ``TABLE_CONSTRAINTS``/``CHECK_CONSTRAINTS`` rows.

        The statement filters ``CONSTRAINT_TYPE = 'CHECK'``; the type is still
        carried on the record so a future widening does not change the shape.
        """
        return [
            MariaDBConstraintInfo(
                schema=row.get("CONSTRAINT_SCHEMA") or schema,
                table_name=row.get("TABLE_NAME") or table_name,
                name=row.get("CONSTRAINT_NAME", ""),
                constraint_type=row.get("CONSTRAINT_TYPE") or "CHECK",
                check_clause=row.get("CHECK_CLAUSE"),
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
    def _as_yes_no(value: Any) -> Optional[bool]:
        """Read a catalogue boolean, keeping "not reported" as ``None``.

        MariaDB is inconsistent across views: ``CYCLE_OPTION`` is ``'1'`` /
        ``'0'``, while ``IS_DETERMINISTIC`` is ``'YES'`` / ``'NO'``. Both
        spell the same fact, so one reader accepts both and anything else the
        server may add later.
        """
        if value is None:
            return None
        return str(value).strip().lower() in ("1", "y", "yes", "true")

    @staticmethod
    def _as_cycle(value: Any) -> Optional[bool]:
        """Read ``CYCLE_OPTION``; MariaDB spells it ``'1'`` / ``'0'``."""
        return MariaDBIntrospectorMixin._as_yes_no(value)

    def parse_sequence_row(self, row: Dict[str, Any], schema: str) -> SequenceInfo:
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

    def parse_sequences(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[SequenceInfo]:
        return [self.parse_sequence_row(row, schema) for row in rows]

    def parse_sequence_info(
        self, rows: List[Dict[str, Any]], name: str, schema: str
    ) -> Optional[SequenceInfo]:
        if not rows:
            return None
        return self.parse_sequence_row(rows[0], schema)

    def parse_table_options(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[TableOptionsInfo]:
        return [self.parse_table_options_row(row, schema) for row in rows]

    @staticmethod
    def parse_table_options_row(
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

    def parse_table_options_info(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> Optional[TableOptionsInfo]:
        if not rows:
            return None
        return self.parse_table_options_row(rows[0], schema)

    def parse_ddl_statements(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[DDLStatement]:
        """Project ``SHOW CREATE TABLE`` rows into the engine's own DDL.

        ``SHOW CREATE`` names its result columns after the object --
        ``Table`` and ``Create Table`` -- rather than after the concept, so
        the spellings core's generic reader looks for (``ddl``, ``sql``,
        ``definition``) are absent from the row and the table the engine had
        just described would be answered as having no DDL at all. This is
        the same override MySQL's introspector carries, for the same reason:
        the engine's own column name is the wiring fact here, not a spelling
        the parser should have to know about.

        ``native`` is True because the text is MariaDB's retrieval of what
        it holds, never an assembly pass over the catalogue. Only the TABLE
        flavour is read because only it is formatted; see the dialect's
        ``format_ddl_statement_query_statement``.
        """
        found: List[DDLStatement] = []
        for row in rows or []:
            # Both spellings are read because the driver is not consistent
            # about which one it keeps, and the column carries a space either
            # way. ``ShowCreateTableResult`` reads the same two, and
            # ``ShowIntrospector.parse_create_table`` is where a caller sees
            # the identical row.
            ddl = row.get("Create Table", row.get("CREATE TABLE", ""))
            if not ddl:
                continue
            found.append(
                DDLStatement(
                    schema=schema,
                    object_type="TABLE",
                    object_name=str(
                        row.get("Table", row.get("TABLE", ""))
                    ),
                    ddl=str(ddl),
                    native=True,
                )
            )
        return found

    # ------------------------------------------------------------------ #
    # MariaDB-only families: neutral object state
    # ------------------------------------------------------------------ #

    def parse_table_state(
        self,
        options: TableOptionsInfo,
        schema: str,
        partitioning: Optional[PartitionState],
    ) -> TableState:
        """Project a ``TABLES`` row and its partition state onto ``TableState``.

        ``TABLE_TYPE`` distinguishes a base table from a view, a sequence and a
        system-versioned table. A system-versioned table stays a regular table
        (its rows are still readable and writable) and records the trait that
        makes its hidden history storage noticeable.

        ``charset`` is not a column of ``TABLES``; the table reports only its
        collation, and MariaDB names every reported collation with its charset
        as the leading prefix (verified across the catalogue on 11.8), so the
        charset is read from that prefix rather than left unset.
        """
        table_type = (options.table_type or "").upper()
        kind, traits = self._table_kind(table_type)
        if partitioning is not None and partitioning.scheme is not None:
            traits = traits + ("partitioned",)
        storage = StorageOptionsState(
            engine=options.engine,
            charset=self._charset_from_collation(options.collation),
            collation=options.collation,
            raw={
                "row_format": options.row_format,
                "auto_increment": options.auto_increment,
                "create_options": options.create_options,
            },
        )
        return TableState(
            name=options.name,
            schema=schema,
            kind=kind,
            traits=traits,
            storage=storage,
            comment=options.comment,
            partitioning=partitioning,
            raw={
                "table_type": options.table_type,
                "create_options": options.create_options,
            },
        )

    @staticmethod
    def _table_kind(table_type: str) -> Tuple[str, Tuple[str, ...]]:
        """Map a ``TABLES.TABLE_TYPE`` onto ``TableState``'s kind and traits."""
        if table_type == "SYSTEM VERSIONED":
            return "regular", ("system_versioned",)
        mapping = {
            "BASE TABLE": "regular",
            "VIEW": "view",
            "SEQUENCE": "sequence",
            "TEMPORARY": "temporary",
            "SYSTEM VIEW": "system",
        }
        return mapping.get(table_type, table_type.lower() or "regular"), ()

    @staticmethod
    def _charset_from_collation(collation: Optional[str]) -> Optional[str]:
        """Read the charset out of a MariaDB collation name.

        MariaDB reports a table's collation, not its charset. Every collation
        the catalogue reports is named ``<charset>_<rest>`` (the 11.8 catalogue
        has no exception), so the leading token is the charset. ``None``
        collation -- a view or sequence that has none -- leaves it ``None``.
        """
        if not collation:
            return None
        return collation.split("_", 1)[0]

    def parse_derived_objects(
        self, options: TableOptionsInfo
    ) -> List[DerivedObjectState]:
        """Name the objects MariaDB created for a table's declaration.

        A ``SYSTEM VERSIONED`` table keeps its history in the same physical
        table (the hidden ``ROW_START``/``ROW_END`` columns), unlike SQL Server's
        separate history table. The neutral shape still has to say that the
        history exists, so it is reported as a ``history_table`` derived object
        under the conventional companion name, with ``raw["materialized"] =
        False`` recording that MariaDB does not publish a second table to alter
        or drop.

        A non-versioned table created nothing indirectly, so the answer is an
        empty list.
        """
        if (options.table_type or "").upper() != "SYSTEM VERSIONED":
            return []
        return [
            DerivedObjectState(
                kind="history_table",
                name=f"{options.name}_history",
                owned_by=options.name,
                raw={
                    "storage": "inline",
                    "materialized": False,
                    "table_type": options.table_type,
                },
            )
        ]

    @staticmethod
    def parse_index_states(
        indexes: List[IndexInfo], table_name: str, schema: str
    ) -> List[IndexState]:
        """Project ``IndexInfo`` records onto ``IndexState``.

        MariaDB has no partial indexes, so ``predicate`` stays ``None``, and it
        has no invisible or unusable index state in its catalogue, so the two
        flags keep the neutral defaults. Only the primary index names the
        constraint it backs; a unique index may be the constraint itself or an
        index a caller created, and the catalogue does not distinguish the two.
        """
        return [
            IndexState(
                name=index.name,
                table=table_name,
                schema=schema,
                unique=index.is_unique,
                method=index.index_type.value,
                predicate=index.filter_condition,
                visible=True,
                usable=True,
                backs_constraint="PRIMARY" if index.is_primary else None,
                raw={
                    "is_primary": index.is_primary,
                    "columns": tuple(column.name for column in index.columns),
                    "comment": index.comment,
                    "size_bytes": index.size_bytes,
                },
            )
            for index in indexes
        ]

    @staticmethod
    def parse_constraint_states(
        indexes: List[IndexInfo],
        foreign_keys: List[IntrospectionForeignKeyInfo],
        checks: List[MariaDBConstraintInfo],
        table_name: str,
        schema: str,
    ) -> List[ConstraintState]:
        """Project MariaDB's three constraint-bearing families onto one list.

        ``TABLE_CONSTRAINTS`` is not read directly: PRIMARY KEY and UNIQUE are
        the indexes ``STATISTICS`` reports, FOREIGN KEY is the referential
        family, and CHECK is the joined ``TABLE_CONSTRAINTS`` /
        ``CHECK_CONSTRAINTS`` read. Every state is validated and enforced;
        MariaDB has no ``NOT VALID``, ``[NOT] ENFORCED`` or deferrable
        constraint, so those flags are not a guess about the row but a fact
        about the engine.
        """
        states: List[ConstraintState] = []
        for index in indexes:
            if index.is_primary:
                states.append(
                    ConstraintState(
                        name=index.name,
                        table=table_name,
                        kind="PRIMARY KEY",
                        schema=schema,
                        backing_index=index.name,
                        raw={"columns": tuple(column.name for column in index.columns)},
                    )
                )
            elif index.is_unique:
                states.append(
                    ConstraintState(
                        name=index.name,
                        table=table_name,
                        kind="UNIQUE",
                        schema=schema,
                        backing_index=index.name,
                        raw={"columns": tuple(column.name for column in index.columns)},
                    )
                )
        for foreign_key in foreign_keys:
            states.append(
                ConstraintState(
                    name=foreign_key.name,
                    table=table_name,
                    kind="FOREIGN KEY",
                    schema=schema,
                    raw={
                        "columns": tuple(foreign_key.columns),
                        "referenced_table": foreign_key.referenced_table,
                        "referenced_columns": tuple(foreign_key.referenced_columns),
                        "on_update": foreign_key.on_update.value,
                        "on_delete": foreign_key.on_delete.value,
                    },
                )
            )
        for check in checks:
            states.append(
                ConstraintState(
                    name=check.name,
                    table=table_name,
                    kind="CHECK",
                    schema=schema,
                    raw={
                        "constraint_type": check.constraint_type,
                        "check_clause": check.check_clause,
                    },
                )
            )
        return states

    @staticmethod
    def parse_sequence_states(sequences: List[SequenceInfo]) -> List[SequenceState]:
        """Project MariaDB ``SequenceInfo`` records onto ``SequenceState``.

        A MariaDB sequence is not owned by a column -- it is its own relation --
        so ``owned_by`` stays ``None``. The fields core's shape asks for are
        carried directly, and the remaining declared facts ride in ``raw``.
        """
        return [
            SequenceState(
                name=sequence.name,
                schema=sequence.schema,
                owned_by=None,
                start=sequence.start_value,
                increment=sequence.increment,
                raw={
                    "minimum_value": sequence.minimum_value,
                    "maximum_value": sequence.maximum_value,
                    "cycle": sequence.cycle,
                    "cache_size": sequence.cache_size,
                    "data_type": sequence.data_type,
                },
            )
            for sequence in sequences
        ]

    # ------------------------------------------------------------------ #
    # Statement factories — one node per question, rendered by the dialect
    # ------------------------------------------------------------------ #

    def target_schema(self, schema: Optional[str]) -> str:
        """Return the schema to read, defaulting to this backend's own."""
        return schema if schema is not None else self.default_schema

    def sequence_target_schema(self, schema: Optional[str]) -> str:
        """Return the schema to read, defaulting to this backend's own.

        Kept as the sequence family's spelling of :meth:`target_schema`; both
        resolve the same way, and every new family uses the generic name.
        """
        return self.target_schema(schema)

    def sequence_list_statement(
        self, *, schema: Optional[str]
    ) -> "MariaDBSequenceQuery":
        """Return the statement that lists the sequences in *schema*."""
        from ..expression.introspection import MariaDBSequenceQuery

        return MariaDBSequenceQuery(self.dialect, self.sequence_target_schema(schema))

    def sequence_info_statement(
        self, *, name: str, schema: Optional[str]
    ) -> "MariaDBSequenceQuery":
        """Return the statement that asks for one sequence by name."""
        from ..expression.introspection import MariaDBSequenceQuery

        return MariaDBSequenceQuery(
            self.dialect, self.sequence_target_schema(schema), name=name
        )

    def table_options_statement(
        self, *, table_name: Optional[str], schema: Optional[str]
    ) -> "MariaDBTableOptionsQuery":
        """Return the statement that reads table options, optionally one table's."""
        from ..expression.introspection import MariaDBTableOptionsQuery

        return MariaDBTableOptionsQuery(
            self.dialect, self.sequence_target_schema(schema), table_name=table_name
        )

    def partition_statement(
        self,
        *,
        table_name: str,
        schema: Optional[str],
        include_stats: bool = False,
    ) -> "MariaDBPartitionQuery":
        """Return the statement that lists one table's partitions.

        ``include_stats`` travels with the statement because it changes the
        projection, not only the parser: a caller that does not want the
        counters should not read them.
        """
        from ..expression.introspection import MariaDBPartitionQuery

        return MariaDBPartitionQuery(
            self.dialect,
            self.target_schema(schema),
            table_name,
            include_stats=include_stats,
        )

    def routine_statement(
        self,
        *,
        schema: Optional[str],
        name: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> "MariaDBRoutineQuery":
        """Return the statement that reads routines, optionally one by name."""
        from ..expression.introspection import MariaDBRoutineQuery

        return MariaDBRoutineQuery(
            self.dialect, self.target_schema(schema), name=name, kind=kind
        )

    def constraint_statement(
        self, *, table_name: str, schema: Optional[str]
    ) -> "MariaDBConstraintQuery":
        """Return the statement that lists one table's CHECK constraints."""
        from ..expression.introspection import MariaDBConstraintQuery

        return MariaDBConstraintQuery(
            self.dialect, self.target_schema(schema), table_name
        )


class MariaDBIntrospector(MariaDBIntrospectorMixin, AbstractIntrospector):
    """Synchronous introspector for MariaDB backends.

    In addition to the standard AbstractIntrospector interface, exposes the
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
        executor: IntrospectorExecutor,
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)
        self._show_instance: Optional[ShowIntrospector] = None
        self._status_instance: Optional[MariaDBStatusIntrospector] = None

    @property
    def show(self) -> ShowIntrospector:
        """MariaDB-specific SHOW sub-introspector (lazily created)."""
        if self._show_instance is None:
            self._show_instance = ShowIntrospector(self._backend, self._executor)
        return self._show_instance

    @property
    def status(self) -> MariaDBStatusIntrospector:
        """MariaDB server status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = MariaDBStatusIntrospector(self._backend)
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

        if not self.dialect.version_at_least(SEQUENCES_SINCE):
            result: List[SequenceInfo] = []
        else:
            sql, params = self.sequence_list_statement(schema=schema).to_sql()
            result = self.parse_sequences(
                self._executor.execute(sql, params),
                self.sequence_target_schema(schema),
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

        if not self.dialect.version_at_least(SEQUENCES_SINCE):
            return None
        sql, params = self.sequence_info_statement(name=name, schema=schema).to_sql()
        result = self.parse_sequence_info(
            self._executor.execute(sql, params),
            name,
            self.sequence_target_schema(schema),
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

        sql, params = self.table_options_statement(
            table_name=None, schema=schema
        ).to_sql()
        result = self.parse_table_options(
            self._executor.execute(sql, params),
            self.sequence_target_schema(schema),
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

        sql, params = self.table_options_statement(
            table_name=table_name, schema=schema
        ).to_sql()
        result = self.parse_table_options_info(
            self._executor.execute(sql, params),
            table_name,
            self.sequence_target_schema(schema),
        )
        if result is not None:
            self._cache.set(key, result)
        return result

    # ------------------------------------------------------------------ #
    # Neutral object state and the MariaDB families behind it
    # ------------------------------------------------------------------ #

    def get_partition_state(
        self,
        table_name: str,
        schema: Optional[str] = None,
        include_stats: bool = False,
    ) -> Optional[PartitionState]:
        """Return the table's neutral partition state.

        A non-partitioned table answers ``PartitionState()``, whose ``scheme``
        is ``None`` -- the neutral spelling of "not partitioned". This method
        deliberately returns that object rather than ``None``: ``None`` on the
        method would leave a caller to distinguish "not partitioned" from "the
        backend could not answer", which the state object already says.

        ``include_stats`` changes the statement as well as the parsed result;
        ``False`` does not project the row counters at all. The two answers are
        cached apart because they are two questions.
        """
        key = self._cache.key(
            IntrospectionScope.PARTITION,
            table_name,
            schema=schema,
            extra=f"mariadb:partition-state:stats={int(include_stats)}",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.partition_statement(
            table_name=table_name, schema=schema, include_stats=include_stats
        ).to_sql()
        result = self.parse_partition_state(
            self._executor.execute(sql, params),
            table_name,
            self.target_schema(schema),
            include_stats=include_stats,
        )
        self._cache.set(key, result)
        return result

    def get_table_state(
        self, table_name: str, schema: Optional[str] = None
    ) -> TableState:
        """Read the table's kind, storage options, comment and partition state."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name,
            schema=schema,
            extra="mariadb:table-state",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        options = self.get_table_options(table_name, schema)
        if options is None:
            raise ObjectNotFoundError("Table", table_name, schema)
        partitioning = self.get_partition_state(table_name, schema)
        result = self.parse_table_state(
            options, self.target_schema(schema), partitioning
        )
        self._cache.set(key, result)
        return result

    def list_index_states(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[IndexState]:
        """Read every index on the table through the neutral shape."""
        key = self._cache.key(
            IntrospectionScope.INDEX,
            table_name,
            schema=schema,
            extra="mariadb:index-states",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self.parse_index_states(
            self.list_indexes(table_name, schema),
            table_name,
            self.target_schema(schema),
        )
        self._cache.set(key, result)
        return result

    def list_constraint_states(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ConstraintState]:
        """Read every constraint on the table, across its three families."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name,
            schema=schema,
            extra="mariadb:constraint-states",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self.parse_constraint_states(
            self.list_indexes(table_name, schema),
            self.list_foreign_keys(table_name, schema),
            self.list_constraints(table_name, schema),
            table_name,
            self.target_schema(schema),
        )
        self._cache.set(key, result)
        return result

    def list_sequence_states(
        self, schema: Optional[str] = None
    ) -> List[SequenceState]:
        """Read the sequences this schema holds through the neutral shape."""
        key = self._cache.key(
            IntrospectionScope.SEQUENCE,
            schema=schema,
            extra="mariadb:sequence-states",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self.parse_sequence_states(self.list_sequences(schema))
        self._cache.set(key, result)
        return result

    def list_schemas(self) -> List[str]:
        """Read the database names the server exposes.

        MariaDB has exactly one namespace level and calls it a database, so its
        schema list is its database list; ``SHOW DATABASES`` is the catalogue
        read that already exists for it.
        """
        key = self._cache.key(
            IntrospectionScope.SCHEMA, extra="mariadb:schemas"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = [database.name for database in self.show.databases()]
        self._cache.set(key, result)
        return result

    def list_derived_objects(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[DerivedObjectState]:
        """Read the objects MariaDB created for the table's declaration."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name,
            schema=schema,
            extra="mariadb:derived-objects",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        options = self.get_table_options(table_name, schema)
        result = self.parse_derived_objects(options) if options is not None else []
        self._cache.set(key, result)
        return result

    def item_exists(
        self,
        kind: ItemKind,
        name: str,
        schema: Optional[str] = None,
    ) -> bool:
        """Whether one of the shared objects MariaDB holds exists.

        Core states one rule for every kind: answer when the engine holds the
        object and a catalogue query exists, refuse when the engine holds the
        kind but this backend has no query for it, and ``False`` when the
        engine has no objects of the kind at all. ``ITEM_KINDS_QUERIED``,
        ``ITEM_KINDS_REFUSED`` and ``ITEM_KINDS_ABSENT`` declare which kinds
        fall where; a kind added to :class:`ItemKind` later is refused, so an
        unimplemented query cannot hide as absence.
        """
        if kind in self.ITEM_KINDS_ABSENT:
            return False
        if kind not in self.ITEM_KINDS_QUERIED:
            self._refuse_item_exists(kind)

        if kind is ItemKind.SCHEMA:
            return name in self.list_schemas()
        if kind is ItemKind.TABLE:
            options = self.get_table_options(name, schema)
            if options is None:
                return False
            return (options.table_type or "").upper() in (
                "BASE TABLE",
                "SYSTEM VERSIONED",
                "TEMPORARY",
            )
        if kind is ItemKind.SEQUENCE:
            return self.get_sequence_info(name, schema) is not None
        if kind is ItemKind.FUNCTION:
            return (
                self.get_routine_info(name, kind="FUNCTION", schema=schema)
                is not None
            )

        # A queried kind without a branch above is the same implementation gap.
        self._refuse_item_exists(kind)

    def list_routines(
        self, schema: Optional[str] = None
    ) -> List[MariaDBRoutineInfo]:
        """List the stored procedures and functions in *schema*.

        One query covers both kinds: ``ROUTINES`` names each routine and the
        join to ``PARAMETERS`` carries the arguments. The cache entry is
        schema-scoped with the ``mariadb:routines`` namespace.
        """
        key = self._cache.key(
            IntrospectionScope.SCHEMA, schema=schema, extra="mariadb:routines"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.routine_statement(schema=schema).to_sql()
        result = self.parse_routines(
            self._executor.execute(sql, params),
            self.target_schema(schema),
        )
        self._cache.set(key, result)
        return result

    def get_routine_info(
        self,
        name: str,
        kind: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Optional[MariaDBRoutineInfo]:
        """Return the named routine, or ``None`` when it does not exist.

        ``kind`` (``PROCEDURE`` or ``FUNCTION``) disambiguates a name used by
        both. A miss is not cached, so a routine created after the first
        lookup is visible to the next one.
        """
        key = self._cache.key(
            IntrospectionScope.SCHEMA, name, schema=schema, extra="mariadb:routines"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.routine_statement(
            schema=schema, name=name, kind=kind
        ).to_sql()
        result = self.parse_routine_info(
            self._executor.execute(sql, params),
            name,
            self.target_schema(schema),
            kind=kind,
        )
        if result is not None:
            self._cache.set(key, result)
        return result

    def list_constraints(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[MariaDBConstraintInfo]:
        """List the CHECK constraints of one table.

        Servers before 10.2.1 have no ``CHECK_CONSTRAINTS`` view and did not
        enforce CHECK constraints, so the answer there is an empty list and no
        query is sent. The cache entry is written either way, so asking twice
        costs nothing.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, table_name, schema=schema, extra="mariadb:constraints"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        if not self.dialect.supports_constraint_introspection():
            result: List[MariaDBConstraintInfo] = []
        else:
            sql, params = self.constraint_statement(
                table_name=table_name, schema=schema
            ).to_sql()
            result = self.parse_constraints(
                self._executor.execute(sql, params),
                table_name,
                self.target_schema(schema),
            )
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

        if not self.dialect.version_at_least(SEQUENCES_SINCE):
            result: List[SequenceInfo] = []
        else:
            sql, params = self.sequence_list_statement(schema=schema).to_sql()
            result = self.parse_sequences(
                await self._executor.execute(sql, params),
                self.sequence_target_schema(schema),
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

        if not self.dialect.version_at_least(SEQUENCES_SINCE):
            return None
        sql, params = self.sequence_info_statement(name=name, schema=schema).to_sql()
        result = self.parse_sequence_info(
            await self._executor.execute(sql, params),
            name,
            self.sequence_target_schema(schema),
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

        sql, params = self.table_options_statement(
            table_name=None, schema=schema
        ).to_sql()
        result = self.parse_table_options(
            await self._executor.execute(sql, params),
            self.sequence_target_schema(schema),
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

        sql, params = self.table_options_statement(
            table_name=table_name, schema=schema
        ).to_sql()
        result = self.parse_table_options_info(
            await self._executor.execute(sql, params),
            table_name,
            self.sequence_target_schema(schema),
        )
        if result is not None:
            self._cache.set(key, result)
        return result

    # ------------------------------------------------------------------ #
    # Neutral object state (async twins) and the MariaDB families behind it
    # ------------------------------------------------------------------ #

    async def get_partition_state(
        self,
        table_name: str,
        schema: Optional[str] = None,
        include_stats: bool = False,
    ) -> Optional[PartitionState]:
        """Return the table's neutral partition state; ``scheme`` is ``None``
        when the table is not partitioned. See the synchronous twin."""
        key = self._cache.key(
            IntrospectionScope.PARTITION,
            table_name,
            schema=schema,
            extra=f"mariadb:partition-state:stats={int(include_stats)}",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.partition_statement(
            table_name=table_name, schema=schema, include_stats=include_stats
        ).to_sql()
        result = self.parse_partition_state(
            await self._executor.execute(sql, params),
            table_name,
            self.target_schema(schema),
            include_stats=include_stats,
        )
        self._cache.set(key, result)
        return result

    async def get_table_state(
        self, table_name: str, schema: Optional[str] = None
    ) -> TableState:
        """Read the table's kind, storage options, comment and partition state."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name,
            schema=schema,
            extra="mariadb:table-state",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        options = await self.get_table_options(table_name, schema)
        if options is None:
            raise ObjectNotFoundError("Table", table_name, schema)
        partitioning = await self.get_partition_state(table_name, schema)
        result = self.parse_table_state(
            options, self.target_schema(schema), partitioning
        )
        self._cache.set(key, result)
        return result

    async def list_index_states(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[IndexState]:
        """Read every index on the table through the neutral shape."""
        key = self._cache.key(
            IntrospectionScope.INDEX,
            table_name,
            schema=schema,
            extra="mariadb:index-states",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self.parse_index_states(
            await self.list_indexes(table_name, schema),
            table_name,
            self.target_schema(schema),
        )
        self._cache.set(key, result)
        return result

    async def list_constraint_states(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ConstraintState]:
        """Read every constraint on the table, across its three families."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name,
            schema=schema,
            extra="mariadb:constraint-states",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self.parse_constraint_states(
            await self.list_indexes(table_name, schema),
            await self.list_foreign_keys(table_name, schema),
            await self.list_constraints(table_name, schema),
            table_name,
            self.target_schema(schema),
        )
        self._cache.set(key, result)
        return result

    async def list_sequence_states(
        self, schema: Optional[str] = None
    ) -> List[SequenceState]:
        """Read the sequences this schema holds through the neutral shape."""
        key = self._cache.key(
            IntrospectionScope.SEQUENCE,
            schema=schema,
            extra="mariadb:sequence-states",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self.parse_sequence_states(await self.list_sequences(schema))
        self._cache.set(key, result)
        return result

    async def list_schemas(self) -> List[str]:
        """Read the database names the server exposes."""
        key = self._cache.key(IntrospectionScope.SCHEMA, extra="mariadb:schemas")
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = [database.name for database in await self.show.databases()]
        self._cache.set(key, result)
        return result

    async def list_derived_objects(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[DerivedObjectState]:
        """Read the objects MariaDB created for the table's declaration."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name,
            schema=schema,
            extra="mariadb:derived-objects",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        options = await self.get_table_options(table_name, schema)
        result = self.parse_derived_objects(options) if options is not None else []
        self._cache.set(key, result)
        return result

    async def item_exists(
        self,
        kind: ItemKind,
        name: str,
        schema: Optional[str] = None,
    ) -> bool:
        """Whether one of the shared objects MariaDB holds exists.

        Same three-case rule as the synchronous twin: the kinds in
        ``ITEM_KINDS_ABSENT`` answer ``False``, the kinds in
        ``ITEM_KINDS_QUERIED`` are read from the catalogue, and every other
        kind -- the refused set above all -- is refused rather than answered.
        """
        if kind in self.ITEM_KINDS_ABSENT:
            return False
        if kind not in self.ITEM_KINDS_QUERIED:
            self._refuse_item_exists(kind)

        if kind is ItemKind.SCHEMA:
            return name in await self.list_schemas()
        if kind is ItemKind.TABLE:
            options = await self.get_table_options(name, schema)
            if options is None:
                return False
            return (options.table_type or "").upper() in (
                "BASE TABLE",
                "SYSTEM VERSIONED",
                "TEMPORARY",
            )
        if kind is ItemKind.SEQUENCE:
            return await self.get_sequence_info(name, schema) is not None
        if kind is ItemKind.FUNCTION:
            return (
                await self.get_routine_info(name, kind="FUNCTION", schema=schema)
                is not None
            )

        # A queried kind without a branch above is the same implementation gap.
        self._refuse_item_exists(kind)

    async def list_routines(
        self, schema: Optional[str] = None
    ) -> List[MariaDBRoutineInfo]:
        """List the stored procedures and functions in *schema*."""
        key = self._cache.key(
            IntrospectionScope.SCHEMA, schema=schema, extra="mariadb:routines"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.routine_statement(schema=schema).to_sql()
        result = self.parse_routines(
            await self._executor.execute(sql, params),
            self.target_schema(schema),
        )
        self._cache.set(key, result)
        return result

    async def get_routine_info(
        self,
        name: str,
        kind: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Optional[MariaDBRoutineInfo]:
        """Return the named routine, or ``None`` when it does not exist."""
        key = self._cache.key(
            IntrospectionScope.SCHEMA, name, schema=schema, extra="mariadb:routines"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.routine_statement(
            schema=schema, name=name, kind=kind
        ).to_sql()
        result = self.parse_routine_info(
            await self._executor.execute(sql, params),
            name,
            self.target_schema(schema),
            kind=kind,
        )
        if result is not None:
            self._cache.set(key, result)
        return result

    async def list_constraints(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[MariaDBConstraintInfo]:
        """List the CHECK constraints of one table.

        Servers before 10.2.1 have no ``CHECK_CONSTRAINTS`` view and did not
        enforce CHECK constraints, so the answer there is an empty list and no
        query is sent.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, table_name, schema=schema, extra="mariadb:constraints"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        if not self.dialect.supports_constraint_introspection():
            result: List[MariaDBConstraintInfo] = []
        else:
            sql, params = self.constraint_statement(
                table_name=table_name, schema=schema
            ).to_sql()
            result = self.parse_constraints(
                await self._executor.execute(sql, params),
                table_name,
                self.target_schema(schema),
            )
        self._cache.set(key, result)
        return result
