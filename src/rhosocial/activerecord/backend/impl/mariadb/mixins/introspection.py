# src/rhosocial/activerecord/backend/impl/mariadb/mixins/introspection.py
"""MariaDB introspection capability mixin.

This mixin implements the IntrospectionSupport protocol for MariaDB,
providing database metadata introspection via information_schema.

Every query here is a tree of expression nodes: the formatter supplies the
projection, the conditions and the ordering, and :class:`QueryStatement`
renders them. Nothing in this module assembles SQL text clause by clause --
what a query *asks* stays a structure the rest of the framework can inspect,
and the spelling belongs to the formatters it delegates to.
"""
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.introspection.types import IntrospectionScope
    from rhosocial.activerecord.backend.expression.introspection import (
        DatabaseInfoQueryStatement,
        TableListQueryStatement,
        ColumnInfoQueryStatement,
        IndexInfoQueryStatement,
        ForeignKeyQueryStatement,
        ViewListQueryStatement,
        ViewInfoQueryStatement,
        TriggerListQueryStatement,
        ColumnDataProfileQueryStatement,
        ColumnValueSampleQueryStatement,
        JoinCoverageQueryStatement,
        ObjectDependencyQueryStatement,
        DDLStatementQueryStatement,
        RuntimeMetricsQueryStatement,
    )
    from rhosocial.activerecord.backend.expression.sources.relation import NamedRelationRef
    from rhosocial.activerecord.backend.expression.objects import Table
    from rhosocial.activerecord.backend.impl.mariadb.expression.introspection import (
        MariaDBSequenceQuery,
        MariaDBTableOptionsQuery,
    )

#: Schemas owned by the server rather than the user. Excluded from user-facing
#: listings and from disk-usage totals.
#:
#: This is a fixed list rather than a discovery query because
#: ``information_schema.SCHEMATA`` carries no flag distinguishing a system
#: schema from a user schema -- the only reliable discriminator would be a
#: round trip to compare against the server's own bootstrap state. Keeping it
#: in one place (rather than inline at each call site) means a new MariaDB
#: release that adds a system schema needs a change here and nowhere else.
SYSTEM_SCHEMAS = ("information_schema", "performance_schema", "mysql", "sys")

#: The catalogue these queries read. `information_schema` is a *database*
#: on MariaDB like any other, so it belongs in the catalog slot of a schema
#: object rather than being spelled into each query as a literal prefix.
INFORMATION_SCHEMA_DATABASE = "information_schema"

#: MariaDB 10.3 added sequences, and a sequence is a table: it appears in
#: `information_schema.TABLES` with `TABLE_TYPE='SEQUENCE'` from that release on.
SEQUENCES_SINCE = (10, 3)

#: The `information_schema.SEQUENCES` view -- a sequence's start, bounds,
#: increment and cycle -- only exists from 11.7. Measured across the wired
#: servers: 10.2 through 11.4 report `Unknown table 'SEQUENCES' in
#: information_schema`; 11.7 and later answer it. Below 11.7 a sequence is
#: still listable from `TABLES`, and these facts are unknown rather than
#: absent from the server.
SEQUENCE_DETAILS_SINCE = (11, 7)


class MariaDBIntrospectionMixin:
    """MariaDB introspection capability declaration and query formatting.

    Every query here reads ``information_schema``, which on MariaDB is a
    database like any other. Naming it therefore means qualifying a
    relation, and that goes through the one qualified-name renderer via
    :meth:`_information_schema` -- so ``information_schema`` does not
    become a second, hand-spelled way of naming a namespace that the rest
    of the backend spells as a catalog slot.

    This mixin implements the IntrospectionSupport protocol by:
    1. Declaring which introspection features MariaDB supports (supports_* methods)
    2. Formatting SQL queries for introspection (format_*_query methods)

    The format_*_query methods are called by Expression.to_sql() to generate
    database-specific SQL using information_schema.

    Architecture flow:
    Introspector.<family>_statement() [manager factory]
    -> Expression(Dialect).to_sql()
    -> Dialect.format_*_query() [this mixin]
    -> Returns SQL and parameters

    MariaDB supports all introspection features via information_schema,
    which is fully compatible with MySQL's information_schema structure.
    """

    def supports_table_options_introspection(self) -> bool:
        """MariaDB answers for a table's storage options from
        ``information_schema.TABLES`` -- the capability for the
        ``introspect table-options`` family. Named the same as MySQL's
        so the question is answerable identically in both engines."""
        return True

    def supports_table_storage_introspection(self) -> bool:
        """Per-table storage metrics, read from ``information_schema.TABLES``.

        MariaDB's storage is row-plus-index shaped: ``DATA_LENGTH`` and
        ``INDEX_LENGTH`` are reported per table, so the table's footprint
        is answerable as its total (``size_bytes``) and as its split
        (``data_size_bytes`` / ``index_size_bytes``). The probe says the
        family is answerable; what a server that reports neither column
        yields stays ``None`` rather than zero (see
        :meth:`~.MariaDBIntrospectorMixin.parse_tables`).
        """
        return True

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """MariaDB supports introspection via information_schema."""
        return True

    def supports_database_info(self) -> bool:
        """MariaDB supports database info via information_schema.SCHEMATA."""
        return True

    def supports_table_introspection(self) -> bool:
        """MariaDB supports table introspection via information_schema.TABLES."""
        return True

    def supports_column_introspection(self) -> bool:
        """MariaDB supports column introspection via information_schema.COLUMNS."""
        return True

    def supports_index_introspection(self) -> bool:
        """MariaDB supports index introspection via information_schema.STATISTICS."""
        return True

    def supports_foreign_key_introspection(self) -> bool:
        """MariaDB supports foreign key introspection via information_schema."""
        return True

    def supports_view_introspection(self) -> bool:
        """MariaDB supports view introspection via information_schema.VIEWS."""
        return True

    def supports_trigger_introspection(self) -> bool:
        """MariaDB supports trigger introspection via information_schema.TRIGGERS."""
        return True

    def supports_sequence_introspection(self) -> bool:
        """Sequences, read from information_schema.TABLES (MariaDB 10.3+).

        A sequence is a table on MariaDB, so listing one needs nothing newer
        than the release that introduced ``CREATE SEQUENCE``. The numeric
        details in ``information_schema.SEQUENCES`` do need 11.7, but they are
        an enrichment of the same row: the sequence itself is listable from
        10.3 on.
        """
        return self.version_at_least(SEQUENCES_SINCE)

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope
        scopes = [
            IntrospectionScope.DATABASE,
            IntrospectionScope.TABLE,
            IntrospectionScope.COLUMN,
            IntrospectionScope.INDEX,
            IntrospectionScope.FOREIGN_KEY,
            IntrospectionScope.VIEW,
            IntrospectionScope.TRIGGER,
        ]
        if self.supports_sequence_introspection():
            scopes.append(IntrospectionScope.SEQUENCE)
        return scopes

    # ========== Query Formatting ==========

    def _information_schema(self, name: str) -> "Table":
        """Return ``information_schema``.``name`` as a relation object.

        The catalogue is a catalog slot on a schema object rather than a
        literal prefix in a string, so the qualified name renders through
        exactly one place -- the same ``format_table_object`` every other
        relation in this backend goes through.
        """
        from rhosocial.activerecord.backend.expression.objects import Table

        return Table(self, name, catalog_name=INFORMATION_SCHEMA_DATABASE)

    def _relation_ref(self, table: "Table", alias: str) -> "NamedRelationRef":
        """Name *table* inside a FROM/JOIN list under *alias*."""
        from rhosocial.activerecord.backend.expression.sources.relation import (
            NamedRelationRef,
        )

        return NamedRelationRef(self, table, alias=alias)

    def system_schemas_predicate(self):
        """Exclude :data:`SYSTEM_SCHEMAS` from a ``TABLE_SCHEMA`` filter.

        The list travels inline -- it is a statement about this backend's
        catalogue, not caller data, and inlining keeps the parameter tuple
        of every query that uses it exactly as it was.

        Returns:
            A predicate node rendering ``NOT (`TABLE_SCHEMA` IN (...))``.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            InPredicate,
            Literal,
            LogicalPredicate,
        )

        return LogicalPredicate(
            self,
            "NOT",
            InPredicate(
                self, Column(self, "TABLE_SCHEMA"), Literal(self, SYSTEM_SCHEMAS, inline=True)
            ),
        )

    def format_database_info_query_statement(
        self, expr: "DatabaseInfoQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format database information query.

        Query information_schema.SCHEMATA for charset/collation.

        Args:
            expr: Database info expression with schema parameter.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        schema = params.get("schema", "")

        query = QueryStatement(
            self,
            select=[
                Column(self, "DEFAULT_CHARACTER_SET_NAME"),
                Column(self, "DEFAULT_COLLATION_NAME"),
            ],
            from_=self._information_schema("SCHEMATA"),
            where=WhereClause(
                self,
                ComparisonPredicate(
                    self, "eq", Column(self, "SCHEMA_NAME"), Literal(self, schema)
                ),
            ),
        )
        return query.to_sql()

    def format_table_list_query_statement(
        self, expr: "TableListQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format table list query.

        Query information_schema.TABLES for table metadata.

        A sequence is a table on MariaDB 10.3+, so it appears in
        ``information_schema.TABLES`` with ``TABLE_TYPE='SEQUENCE'`` beside the
        base tables and views. It is not an entry in this listing: it has no
        columns and no rows, and this backend reports the family from
        ``list_sequences``. The exclusion is therefore part of what the
        statement means and travels inline, like the system-schema list, rather
        than as a bind parameter -- so the parameter tuple stays ``(schema,)``
        (plus an explicitly requested ``table_type``). The condition is written
        on every version: a server older than 10.3 cannot hold the spelling, so
        it is a no-op there rather than a second statement shape.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
            LogicalPredicate,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        schema = params.get("schema", "")
        include_views = params.get("include_views", True)
        include_system = params.get("include_system", False)
        table_type = params.get("table_type")

        conditions = [
            ComparisonPredicate(self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema)),
            # ``ne`` writes ``<>``: MariaDB's spelling of "not equal", and the
            # one that reads as the set difference this listing means.
            ComparisonPredicate(
                self,
                "ne",
                Column(self, "TABLE_TYPE"),
                Literal(self, "SEQUENCE", inline=True),
            ),
        ]

        if not include_system:
            conditions.append(self.system_schemas_predicate())
        if not include_views:
            conditions.append(
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "TABLE_TYPE"),
                    Literal(self, "BASE TABLE", inline=True),
                )
            )
        if table_type:
            conditions.append(
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_TYPE"), Literal(self, table_type)
                )
            )

        query = QueryStatement(
            self,
            select=[
                Column(self, "TABLE_NAME"),
                Column(self, "TABLE_TYPE"),
                Column(self, "TABLE_COMMENT"),
                Column(self, "TABLE_ROWS"),
                # Data and index bytes are read apart: MariaDB's storage is
                # row-plus-index shaped, so the two narrow slots of
                # ``IntrospectionTableInfo`` are answered rather than summed
                # away here. ``size_bytes`` is their sum, computed in the
                # parser, so a table that reports only one of them does not
                # get the other defaulted to zero.
                Column(self, "DATA_LENGTH"),
                Column(self, "INDEX_LENGTH"),
                Column(self, "AUTO_INCREMENT"),
                Column(self, "CREATE_TIME"),
                Column(self, "UPDATE_TIME"),
            ],
            from_=self._information_schema("TABLES"),
            where=WhereClause(self, LogicalPredicate(self, "AND", *conditions)),
        )
        return query.to_sql()

    def format_column_info_query_statement(
        self, expr: "ColumnInfoQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format column information query.

        Query information_schema.COLUMNS for column metadata, left-joined to
        information_schema.GEOMETRY_COLUMNS for spatial columns.

        The join is what makes a declared spatial reference system visible at
        all. MariaDB does not write ``REF_SYSTEM_ID=<n>`` into ``COLUMN_TYPE``
        or ``SHOW CREATE``: those report the bare ``point``, and the declared
        value exists only in ``GEOMETRY_COLUMNS.SRID`` (measured on 10.2.44
        and 13.1.1; the view's ``G_TABLE_SCHEMA`` / ``G_TABLE_NAME`` /
        ``G_GEOMETRY_COLUMN`` identify the column). A bare spatial column
        reports SRID 0, MariaDB's default coordinate system, so a left join
        without extra filtering is correct and non-spatial columns simply get
        SQL NULL.

        Args:
            expr: Column info expression with table_name and schema.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            JoinClause,
            JoinType,
            Literal,
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema", "")

        join = JoinClause(
            self,
            left_table=self._relation_ref(self._information_schema("COLUMNS"), "c"),
            right_table=self._relation_ref(
                self._information_schema("GEOMETRY_COLUMNS"), "g"
            ),
            join_type=JoinType.LEFT,
            condition=LogicalPredicate(
                self,
                "AND",
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "G_TABLE_SCHEMA", table="g"),
                    Column(self, "TABLE_SCHEMA", table="c"),
                ),
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "G_TABLE_NAME", table="g"),
                    Column(self, "TABLE_NAME", table="c"),
                ),
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "G_GEOMETRY_COLUMN", table="g"),
                    Column(self, "COLUMN_NAME", table="c"),
                ),
            ),
        )

        query = QueryStatement(
            self,
            select=[
                Column(self, "COLUMN_NAME", table="c"),
                Column(self, "ORDINAL_POSITION", table="c"),
                Column(self, "COLUMN_DEFAULT", table="c"),
                Column(self, "IS_NULLABLE", table="c"),
                Column(self, "DATA_TYPE", table="c"),
                Column(self, "CHARACTER_MAXIMUM_LENGTH", table="c"),
                Column(self, "NUMERIC_PRECISION", table="c"),
                Column(self, "NUMERIC_SCALE", table="c"),
                Column(self, "COLUMN_TYPE", table="c"),
                Column(self, "COLUMN_KEY", table="c"),
                Column(self, "EXTRA", table="c"),
                Column(self, "COLUMN_COMMENT", table="c"),
                Column(self, "CHARACTER_SET_NAME", table="c"),
                Column(self, "COLLATION_NAME", table="c"),
                Column(self, "SRID", table="g", alias="SRID"),
            ],
            from_=join,
            where=WhereClause(
                self,
                LogicalPredicate(
                    self,
                    "AND",
                    ComparisonPredicate(
                        self, "eq", Column(self, "TABLE_SCHEMA", table="c"), Literal(self, schema)
                    ),
                    ComparisonPredicate(
                        self,
                        "eq",
                        Column(self, "TABLE_NAME", table="c"),
                        Literal(self, table_name),
                    ),
                ),
            ),
            order_by=OrderByClause(self, [Column(self, "ORDINAL_POSITION", table="c")]),
        )
        return query.to_sql()

    def format_index_info_query_statement(
        self, expr: "IndexInfoQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format index information query.

        Query information_schema.STATISTICS for index metadata.

        Args:
            expr: Index info expression with table_name and schema.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema", "")

        query = QueryStatement(
            self,
            select=[
                Column(self, "INDEX_NAME"),
                Column(self, "NON_UNIQUE"),
                Column(self, "SEQ_IN_INDEX"),
                Column(self, "COLUMN_NAME"),
                Column(self, "INDEX_TYPE"),
                Column(self, "SUB_PART"),
                Column(self, "NULLABLE"),
            ],
            from_=self._information_schema("STATISTICS"),
            where=WhereClause(
                self,
                LogicalPredicate(
                    self,
                    "AND",
                    ComparisonPredicate(
                        self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema)
                    ),
                    ComparisonPredicate(
                        self, "eq", Column(self, "TABLE_NAME"), Literal(self, table_name)
                    ),
                ),
            ),
            order_by=OrderByClause(
                self, [Column(self, "INDEX_NAME"), Column(self, "SEQ_IN_INDEX")]
            ),
        )
        return query.to_sql()

    def format_foreign_key_query_statement(
        self, expr: "ForeignKeyQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format foreign key information query.

        Query information_schema.KEY_COLUMN_USAGE and REFERENTIAL_CONSTRAINTS
        for foreign key metadata.

        Args:
            expr: Foreign key expression with table_name and schema.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            JoinClause,
            Literal,
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema", "")

        join = JoinClause(
            self,
            left_table=self._relation_ref(
                self._information_schema("KEY_COLUMN_USAGE"), "kcu"
            ),
            right_table=self._relation_ref(
                self._information_schema("REFERENTIAL_CONSTRAINTS"), "rc"
            ),
            join_type="JOIN",
            condition=LogicalPredicate(
                self,
                "AND",
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "CONSTRAINT_NAME", table="kcu"),
                    Column(self, "CONSTRAINT_NAME", table="rc"),
                ),
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "CONSTRAINT_SCHEMA", table="kcu"),
                    Column(self, "CONSTRAINT_SCHEMA", table="rc"),
                ),
            ),
        )

        query = QueryStatement(
            self,
            select=[
                Column(self, "CONSTRAINT_NAME", table="kcu"),
                Column(self, "COLUMN_NAME", table="kcu"),
                Column(self, "ORDINAL_POSITION", table="kcu"),
                Column(self, "REFERENCED_TABLE_NAME", table="kcu"),
                Column(self, "REFERENCED_COLUMN_NAME", table="kcu"),
                Column(self, "UPDATE_RULE", table="rc"),
                Column(self, "DELETE_RULE", table="rc"),
            ],
            from_=join,
            where=WhereClause(
                self,
                LogicalPredicate(
                    self,
                    "AND",
                    ComparisonPredicate(
                        self,
                        "eq",
                        Column(self, "TABLE_SCHEMA", table="kcu"),
                        Literal(self, schema),
                    ),
                    ComparisonPredicate(
                        self,
                        "eq",
                        Column(self, "TABLE_NAME", table="kcu"),
                        Literal(self, table_name),
                    ),
                    Column(self, "REFERENCED_TABLE_NAME", table="kcu").is_not_null(),
                ),
            ),
            order_by=OrderByClause(
                self,
                [
                    Column(self, "CONSTRAINT_NAME", table="kcu"),
                    Column(self, "ORDINAL_POSITION", table="kcu"),
                ],
            ),
        )
        return query.to_sql()

    def format_view_list_query_statement(
        self, expr: "ViewListQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format view list query.

        Query information_schema.VIEWS for view metadata.

        Args:
            expr: View list expression with schema and include_system.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        schema = params.get("schema", "")
        include_system = params.get("include_system", False)

        conditions = [
            ComparisonPredicate(self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema))
        ]

        if not include_system:
            conditions.append(self.system_schemas_predicate())

        query = QueryStatement(
            self,
            select=[
                Column(self, "TABLE_NAME"),
                Column(self, "VIEW_DEFINITION"),
                Column(self, "CHECK_OPTION"),
                Column(self, "IS_UPDATABLE"),
            ],
            from_=self._information_schema("VIEWS"),
            where=WhereClause(self, LogicalPredicate(self, "AND", *conditions)),
            order_by=OrderByClause(self, [Column(self, "TABLE_NAME")]),
        )
        return query.to_sql()

    def format_view_info_query_statement(
        self, expr: "ViewInfoQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format single view information query.

        Query information_schema.VIEWS for a specific view.

        Args:
            expr: View info expression with view_name and schema.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
            LogicalPredicate,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        view_name = params.get("view_name", "")
        schema = params.get("schema", "")

        query = QueryStatement(
            self,
            select=[
                Column(self, "TABLE_NAME"),
                Column(self, "VIEW_DEFINITION"),
                Column(self, "CHECK_OPTION"),
                Column(self, "IS_UPDATABLE"),
            ],
            from_=self._information_schema("VIEWS"),
            where=WhereClause(
                self,
                LogicalPredicate(
                    self,
                    "AND",
                    ComparisonPredicate(
                        self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema)
                    ),
                    ComparisonPredicate(
                        self, "eq", Column(self, "TABLE_NAME"), Literal(self, view_name)
                    ),
                ),
            ),
        )
        return query.to_sql()

    def format_trigger_list_query_statement(
        self, expr: "TriggerListQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format trigger list query.

        Query information_schema.TRIGGERS for trigger metadata.

        Args:
            expr: Trigger list expression with schema and table_name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        schema = params.get("schema", "")
        table_name = params.get("table_name")

        conditions = [
            ComparisonPredicate(self, "eq", Column(self, "TRIGGER_SCHEMA"), Literal(self, schema))
        ]

        if table_name:
            conditions.append(
                ComparisonPredicate(
                    self, "eq", Column(self, "EVENT_OBJECT_TABLE"), Literal(self, table_name)
                )
            )

        query = QueryStatement(
            self,
            select=[
                Column(self, "TRIGGER_NAME"),
                Column(self, "EVENT_MANIPULATION"),
                Column(self, "EVENT_OBJECT_TABLE"),
                Column(self, "ACTION_TIMING"),
                Column(self, "ACTION_STATEMENT"),
                Column(self, "CREATED"),
            ],
            from_=self._information_schema("TRIGGERS"),
            where=WhereClause(self, LogicalPredicate(self, "AND", *conditions)),
            order_by=OrderByClause(self, [Column(self, "TRIGGER_NAME")]),
        )
        return query.to_sql()

    def format_mariadb_sequence_query(
        self, expr: "MariaDBSequenceQuery"
    ) -> Tuple[str, tuple]:
        """Format the sequence read.

        The list is ``information_schema.TABLES`` filtered to
        ``TABLE_TYPE='SEQUENCE'``: a sequence is a table, and that row is the
        only thing every sequence-bearing server reports. The numeric facts
        live in ``information_schema.SEQUENCES``, which MariaDB added in 11.7,
        so the join is written only when the server has the view. Below it the
        detail columns are left out of the projection entirely rather than
        projected as NULL: the rows would carry the same ``None`` either way,
        and not naming a relation that does not exist keeps the query runnable.

        Args:
            expr: Sequence expression with the schema and an optional name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            JoinClause,
            JoinType,
            Literal,
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )

        tables = self._relation_ref(self._information_schema("TABLES"), "t")

        conditions = [
            ComparisonPredicate(
                self, "eq", Column(self, "TABLE_SCHEMA", table="t"), Literal(self, expr.schema)
            ),
            ComparisonPredicate(
                self,
                "eq",
                Column(self, "TABLE_TYPE", table="t"),
                Literal(self, "SEQUENCE", inline=True),
            ),
        ]
        if expr.name is not None:
            conditions.append(
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_NAME", table="t"), Literal(self, expr.name)
                )
            )

        select = [Column(self, "TABLE_NAME", table="t")]
        from_: object = tables

        if self.version >= SEQUENCE_DETAILS_SINCE:
            select.extend(
                [
                    Column(self, "DATA_TYPE", table="s"),
                    Column(self, "START_VALUE", table="s"),
                    Column(self, "MINIMUM_VALUE", table="s"),
                    Column(self, "MAXIMUM_VALUE", table="s"),
                    Column(self, "INCREMENT", table="s"),
                    Column(self, "CYCLE_OPTION", table="s"),
                ]
            )
            from_ = JoinClause(
                self,
                left_table=tables,
                right_table=self._relation_ref(self._information_schema("SEQUENCES"), "s"),
                join_type=JoinType.LEFT,
                condition=LogicalPredicate(
                    self,
                    "AND",
                    ComparisonPredicate(
                        self,
                        "eq",
                        Column(self, "SEQUENCE_SCHEMA", table="s"),
                        Column(self, "TABLE_SCHEMA", table="t"),
                    ),
                    ComparisonPredicate(
                        self,
                        "eq",
                        Column(self, "SEQUENCE_NAME", table="s"),
                        Column(self, "TABLE_NAME", table="t"),
                    ),
                ),
            )

        query = QueryStatement(
            self,
            select=select,
            from_=from_,
            where=WhereClause(self, LogicalPredicate(self, "AND", *conditions)),
            order_by=OrderByClause(self, [Column(self, "TABLE_NAME", table="t")]),
        )
        return query.to_sql()

    def format_mariadb_table_options_query(
        self, expr: "MariaDBTableOptionsQuery"
    ) -> Tuple[str, tuple]:
        """Format the table-options read.

        One row per relation in ``information_schema.TABLES``. ``TABLES``
        carries base tables, views and sequences in one list, and the row's
        ``TABLE_TYPE`` says which it is; the caller decides whether that
        matters. Selecting the type as well as the options is what makes the
        answer self-describing rather than requiring the caller to know it.

        Args:
            expr: Table options expression with the schema and an optional name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )

        conditions = [
            ComparisonPredicate(
                self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, expr.schema)
            )
        ]
        if expr.table_name is not None:
            conditions.append(
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "TABLE_NAME"),
                    Literal(self, expr.table_name),
                )
            )

        query = QueryStatement(
            self,
            select=[
                Column(self, "TABLE_NAME"),
                Column(self, "TABLE_TYPE"),
                Column(self, "ENGINE"),
                Column(self, "ROW_FORMAT"),
                Column(self, "TABLE_COLLATION"),
                Column(self, "AUTO_INCREMENT"),
                Column(self, "TABLE_COMMENT"),
                Column(self, "CREATE_OPTIONS"),
            ],
            from_=self._information_schema("TABLES"),
            where=WhereClause(self, LogicalPredicate(self, "AND", *conditions)),
            order_by=OrderByClause(self, [Column(self, "TABLE_NAME")]),
        )
        return query.to_sql()


    # ========== Operational families ==========
    #
    # MariaDB's performance schema is a partial port of MySQL's. It has the
    # instrument catalogue, which answers the runtime family, but it does not
    # register the table I/O summary tables (``table_io_waits_summary_by_table``
    # and ``table_io_waits_summary_by_index_usage``) that MySQL's unused-index,
    # table-counter and index-counter families read. MariaDB's own
    # ``sys`` schema is installed over those tables, but a view over a table
    # the server does not serve cannot answer, so there is no counter to
    # project into any of the three families' slots: what the catalogues do
    # report about an index is its declaration
    # (``information_schema.STATISTICS``) and an estimated cardinality, which
    # describe size and shape, never access.
    #
    # The runtime family is answerable, and its floor is 10.5 -- the release
    # that introduced the performance schema and ``setup_instruments`` with
    # it. The collector is off by default and cannot be enabled at runtime,
    # so on a server started without it the listing is empty even though the
    # probe answers True. An empty answer there is the collector's silence,
    # not "nothing happened", and no row is invented to fill the gap.

    def supports_unused_indexes_detection(self) -> bool:
        """MariaDB registers no per-index access counter, so the probe refuses.

        MySQL answers this family from ``sys.schema_unused_indexes``, a view
        over ``performance_schema.table_io_waits_summary_by_index_usage``.
        MariaDB carries the view's definition in its ported ``sys`` schema
        but does not implement the summary table it selects from: the
        performance schema MariaDB ships registers no table I/O summary at
        all. What is left is ``information_schema.STATISTICS``, which reports
        an index's declaration and an estimated cardinality -- facts about
        what an index is, never about how often the optimiser reached for it.

        So the probe answers False on every release this backend supports
        (10.2 through 13.x, the CI matrix), rather than being gated on a
        floor the way MySQL's is at 5.7: there is no floor at which MariaDB
        starts answering. An answering probe would render a statement naming
        a table the server does not serve (``1146``), turning a
        definition-time question into an execution error; the capability
        refusal is the honest answer. The roundtrip matrix in this repository
        pins ``UnusedIndexesQueryStatement`` as a declared gap with this
        reason.
        """
        return False

    def supports_table_stats(self) -> bool:
        """MariaDB keeps no per-table access counters, so the probe refuses.

        The inquiry covered every release in the matrix and the answer is the
        same shape at each: ``information_schema.TABLES`` carries rows, bytes
        and an estimate of both, and nothing that counts an access; ``ANALYZE
        TABLE`` refreshes optimiser statistics for the *indexes* and
        publishes no per-table use figure; the one MariaDB-specific statistics
        catalogue, ``mysql.column_stats``, is written per column by ``ANALYZE
        TABLE ... PERSISTENT FOR COLUMNS`` and holds min/max/nulls rather than
        I/O. There is no counter to project into the family's slots, and an
        estimate from a different source would be a number the engine never
        measured.

        Reading that catalogue would also need privileges on the ``mysql``
        database, which an application account routinely lacks; see
        :meth:`supports_column_data_profile` for the same privilege audit
        applied to the family it governs.
        """
        return False

    def supports_index_stats(self) -> bool:
        """MariaDB keeps no per-index use counter, so the probe refuses.

        The same missing table as :meth:`supports_unused_indexes_detection`,
        one slot further: "how much is this index used" needs the counter
        "has it ever been used" needs, and MariaDB's performance schema
        registers neither. Estimated cardinality in
        ``information_schema.STATISTICS`` is a property of the data, not a
        measure of the index's use, so projecting it into ``scans`` would put
        a distribution figure in a slot that promises an engine's count of
        operations. The roundtrip matrix in this repository pins
        ``IndexUsageStatsQueryStatement`` as a declared gap with this reason.
        """
        return False

    def supports_runtime_stats(self) -> bool:
        """MariaDB answers runtime measurements from the instrument catalogue.

        ``performance_schema.setup_instruments`` names what is actually being
        counted on this server: one row per instrument, with whether it is
        enabled and whether it is timed. An instrument that is not enabled
        produces no measurement rather than a zero that would read as "idle",
        which is the honest shape for a "what is alive" listing. It is
        instance-wide and carries no schema column, exactly as on MySQL, so
        it is not narrowed by the database the run connected to.

        The performance schema arrived with 10.5, so the probe asks the
        version accessor rather than answering a bare True: below that floor
        the statement would name a relation the server does not serve. The
        collector is off by default and the listing is then empty; no row is
        manufactured to stand in for a measurement the server never took.
        """
        return self.version_at_least((10, 5, 0))

    def format_runtime_metrics_query_statement(
        self, expr: "RuntimeMetricsQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format the runtime listing from the instrument catalogue.

        ``setup_instruments`` names each instrument, whether it is enabled
        and whether it is timed, which is what makes it a "what is alive"
        listing rather than a table of counters: an instrument that is off
        has no measurement behind it. No schema filter -- the catalogue is
        server-wide and carries no schema column, so a filter here would
        refuse a correct query for a nonsensical reason.
        """
        from rhosocial.activerecord.backend.expression import Column, QueryStatement
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
        from rhosocial.activerecord.backend.expression.statements.dql import OrderByClause

        statement = QueryStatement(
            self,
            select=[
                Column(self, "NAME").as_("name"),
                Column(self, "ENABLED").as_("value"),
                Column(self, "TIMED").as_("kind"),
            ],
            from_=NamedRelationRef(
                self,
                Table(
                    self,
                    "setup_instruments",
                    catalog_name="performance_schema",
                ),
            ),
            order_by=OrderByClause(self, [Column(self, "NAME")]),
        )
        return statement.to_sql()


    def supports_object_dependencies(self) -> bool:
        """MariaDB answers the foreign-key dependency graph, and only that.

        ``information_schema.REFERENTIAL_CONSTRAINTS`` holds one row per
        foreign key, which is one edge per constraint -- read on every
        release in the matrix, where the dialect's own constraint tests
        already read its ``DELETE_RULE`` and ``UPDATE_RULE`` (see
        ``dialect.py``). MariaDB records no view-on-table or
        trigger-on-table reference anywhere, so the graph is a real one
        and a partial one, exactly as on MySQL: a caller asking "what
        breaks if I drop this" gets the referential answer and no more.

        The ``TABLE_NAME`` filter is applied in the statement rather than by
        the caller, because the catalogue is database-wide; see
        :meth:`format_object_dependency_query_statement`.
        """
        return True

    def supports_ddl_extraction(self) -> bool:
        """MariaDB answers natively: ``SHOW CREATE TABLE``.

        Unlike PostgreSQL, the engine hands back the DDL it holds, so
        ``DDLStatement.native`` is True and the text is MariaDB's own
        rather than an assembly that would read as authoritative.
        """
        return True

    def supports_ddl_extraction_native(self) -> bool:
        """True -- ``SHOW CREATE`` is MariaDB's own retrieval, not an assembly."""
        return True

    def format_object_dependency_query_statement(
        self, expr: "ObjectDependencyQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format the foreign-key dependency graph from the constraint catalogue.

        One row per foreign key, projected onto the slots core's parser
        reads: the table the constraint belongs to is the *dependent* side,
        the table its key points at is the *referenced* one, and
        ``DELETE_RULE`` is what breaking the edge does. Which side a
        table is on is decided by which column of
        ``REFERENTIAL_CONSTRAINTS`` it is read from, not by the caller's
        question -- "what breaks if I drop orders" and "what does orders
        need" are two readings of the same rows.

        The schema filter narrows to the schema the constraint lives in,
        because the catalogue is database-wide and a caller asking about
        one database should not have to post-filter it. ``object_name``
        narrows to the edges that table carries, which is the question the
        parameter exists for; omitted, the whole graph is answered.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
            LogicalPredicate,
            QueryStatement,
            WhereClause,
        )
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
        from rhosocial.activerecord.backend.expression.statements.dql import OrderByClause

        params = expr.get_params()
        schema = params.get("schema", "")
        object_name = params.get("object_name")

        conditions = [
            ComparisonPredicate(
                self,
                "eq",
                Column(self, "CONSTRAINT_SCHEMA"),
                Literal(self, schema),
            )
        ]
        if object_name:
            conditions.append(
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_NAME"), Literal(self, object_name)
                )
            )

        statement = QueryStatement(
            self,
            select=[
                Column(self, "CONSTRAINT_SCHEMA"),
                Column(self, "CONSTRAINT_NAME"),
                Column(self, "TABLE_NAME").as_("dependent"),
                Column(self, "REFERENCED_TABLE_NAME").as_("referenced"),
                Column(self, "DELETE_RULE").as_("action"),
            ],
            from_=NamedRelationRef(
                self,
                Table(
                    self,
                    "REFERENTIAL_CONSTRAINTS",
                    catalog_name=INFORMATION_SCHEMA_DATABASE,
                ),
            ),
            where=WhereClause(self, LogicalPredicate(self, "AND", *conditions)),
            order_by=OrderByClause(self, [Column(self, "CONSTRAINT_NAME")]),
        )
        return statement.to_sql()

    def format_ddl_statement_query_statement(
        self, expr: "DDLStatementQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format ``SHOW CREATE TABLE`` -- the engine's own text.

        The engine's result column is literally named ``Create Table``, so
        there is nothing to assemble: this is a read, not a reconstruction,
        which is why ``native`` is True here and False on PostgreSQL. The
        introspector reads that column under its own name -- see
        ``MariaDBIntrospectorMixin.parse_ddl_statements`` -- because core's
        generic projection looks for the spellings a catalogue uses and a
        ``SHOW`` answer has none of them.

        Only TABLE is rendered. The engine also answers for VIEW,
        PROCEDURE, FUNCTION, TRIGGER and SEQUENCE through their own
        ``SHOW CREATE`` statements, and each names a different result
        column; mapping them means five more shapes, which is a question
        about which ones callers actually ask. A caller naming one of the
        others is refused rather than handed the table answer.

        The schema is carried when the caller named one. Left empty, the
        relation is unqualified and MariaDB resolves it in the database the
        run connected to -- which is the one namespace level this engine
        has, and the same answer the unqualified name would get from a
        hand-typed ``SHOW CREATE TABLE users``.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.impl.mariadb.expression.show import (
            ShowCreateTableStatement,
        )

        params = expr.get_params()
        object_name = params.get("object_name", "")
        object_type = (params.get("object_type") or "TABLE").upper()
        if object_type != "TABLE":
            raise UnsupportedFeatureError(
                dialect_name="MariaDB",
                feature_name="DDL retrieval for {0!r} objects".format(object_type),
                suggestion=(
                    "MariaDB answers natively for TABLE; VIEW, PROCEDURE, "
                    "FUNCTION, TRIGGER and SEQUENCE each use a different SHOW "
                    "CREATE statement and result column, and are not mapped yet."
                ),
            )
        schema = params.get("schema")

        return ShowCreateTableStatement(
            self, Table(self, object_name, catalog_name=schema or None)
        ).to_sql()

    # ========== Data Profiles (row-shaped answers) ==========

    def supports_column_data_profile(self) -> bool:
        """MariaDB answers a column data profile by aggregating the rows.

        MariaDB is the one MySQL-family engine with a per-column statistics
        catalogue of its own -- ``mysql.column_stats``, written by ``ANALYZE
        TABLE ... PERSISTENT FOR COLUMNS`` -- and it was measured rather than
        assumed. Its layout is ``db_name``, ``table_name``, ``column_name``,
        ``min_value``, ``max_value`` (both ``varbinary(255)``),
        ``nulls_ratio`` (``decimal(12,4)``), ``avg_length``, ``avg_frequency``,
        ``hist_size``, ``hist_type`` and ``histogram``. Read against the five
        figures core promises, that is one usable field out of five:

        * ``nulls_ratio`` is the null fraction, already a ratio. It is
          *approximate*, and the table records no collection time, so the
          family's rule that an estimate carries its vintage cannot be met for
          it: the honest label would be ``UNKNOWN``, never ``ESTIMATE``.
        * ``min_value``/``max_value`` hold the value in the column's *internal
          encoding*, not in a form SQL can read back. Strings happen to be
          their bytes, but an ``INT`` is a packed integer, a ``DATETIME`` is a
          packed long, and a ``DECIMAL`` is its binary decimal -- decoding
          those is per-type work in the client, not a cast the engine can do,
          so both endpoints stay ``None`` rather than being reported as
          mojibake.
        * There is no distinct count. ``avg_frequency`` is the average number
          of rows sharing a value, so a count is only reachable by dividing
          the table's row count by it -- a quotient of two estimates from two
          different tables, in a slot that promises a count.
        * ``histogram``/``hist_type`` are the optimiser's bucket encoding, a
          distribution core does not model and does not want half of.

        Two further facts decide the matter. The table is **empty** until an
        operator asks for statistics -- so a catalogue-only answer is "not
        measured" on every fresh server, which is correct but useless, and a
        zero-filled profile there would be worse than useless. And reading it
        needs ``SELECT`` on the ``mysql`` database, which an application
        account routinely does not have; a profile that failed on privileges
        where the aggregate would have answered would be a regression dressed
        as an optimisation. A row whose four other figures came from the rows
        while its fraction came from the catalogue would have to be labelled
        with one source it does not deserve.

        So every figure comes from the same place, exactly as on MySQL: one
        ``UNION ALL`` arm per column, each arm a full scan of the table, and
        the provenance ``aggregate`` -- which is a word this engine has earned
        rather than inherited. The empty catalogue is then not a special case
        at all: there is nothing to read, so nothing can be mistaken for a
        measurement.
        """
        return True

    def supports_column_value_sample(self) -> bool:
        """MariaDB answers a value listing by aggregating with a limit.

        ``mysql.column_stats`` keeps a histogram, not a value list: the buckets
        are the optimiser's own encoding and the set of values it retained is
        not recoverable from them. So the answer is a ``GROUP BY`` over the
        column plus a sort of the groups -- the same order as the profile
        itself, which is why the two are separate probes rather than one call
        that would make the cheap half pay for the dear one.
        """
        return True

    def supports_join_coverage(self) -> bool:
        """MariaDB answers overlap by counting distinct values on both sides.

        Exact, and paid for with two scans of each column: one for the
        overlap, one for the denominator. ``COUNT(DISTINCT col)`` is the
        engine's own spelling for the second half, so no separate ``SELECT
        DISTINCT`` pass is needed for it. Answering ``True`` is right because
        the probe asks whether the engine *can* answer, not whether it can
        answer cheaply -- the cost belongs in the docstring, not in a False
        that would claim MariaDB cannot measure its own rows.
        """
        return True

    def _user_relation(self, table_name: str, alias: str, schema: "Optional[str]"):
        """A user table as a FROM source, quoted by the dialect.

        The opposite of :meth:`_information_schema`: this relation is whatever
        its owner declared -- mixed case, a space, a reserved word -- so the
        name and the database are left to the dialect's identifier renderer.
        MariaDB's one namespace level is the database, which rides the catalog
        slot (see ``mixins/namespace.py``); naming it in ``schema_name`` would
        be refused rather than silently dropped.
        """
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.expression.sources import (
            NamedRelationRef,
        )

        return NamedRelationRef(
            self,
            Table(self, table_name, catalog_name=schema or None),
            alias=alias,
        )

    def _profile_label(self, text: "Optional[str]", alias: str):
        """A constant label as a named select-list entry.

        ``Literal`` is deliberately unaliasable -- a value has nothing to name
        (see :class:`~...expression.core.Literal`) -- so the constant is cast
        to text, which is the smallest node in the tree that produces a named
        result. The cast is not there for its type: it is there so the label
        can be called ``column_name`` or ``source``, which is what the parser
        reads. ``None`` is the same node carrying SQL NULL, which is how the
        empty profile says "the column name is absent" without inventing one.

        The cast target is ``CHAR`` rather than a length-bounded string type
        because MariaDB's ``CAST`` accepts ``CHAR`` bare and a label has no
        width to declare.
        """
        from rhosocial.activerecord.backend.expression.core import (
            CastExpression,
            Literal,
        )
        from rhosocial.activerecord.backend.expression.types.string import CharType

        return CastExpression(self, Literal(self, text, inline=True), CharType(self), alias=alias)

    def _profile_arm(self, table_name: str, schema: "Optional[str]", column_name: str):
        """One column's arm of the profile, as a node.

        The seven entries are the family's contract: the column's own name,
        the null count, the distinct count, the two endpoints, the row count
        the parser divides by, and the provenance. The null count is a ``SUM``
        over a ``CASE`` so an empty table answers NULL rather than a
        fabricated zero; the distinct count is ``COUNT(DISTINCT ...)``; the
        endpoints are the engine's own ``MIN``/``MAX``; and ``COUNT(*)`` rides
        the same scan as the divisor, so an arm reads its table once.

        ``COUNT(*)`` and the null count share a scan because they are two
        halves of one fraction: the parser divides one by the other, and
        reading the same table twice to get them would double the cost of the
        cheapest part of the answer.
        """
        from rhosocial.activerecord.backend.expression import (
            CaseExpression,
            Column,
            CountFunction,
            FunctionCall,
            IsNullPredicate,
            Literal,
            QueryStatement,
            RowCountWildcard,
            SumFunction,
        )
        from rhosocial.activerecord.backend.expression.objects import Table

        return QueryStatement(
            self,
            select=[
                self._profile_label(column_name, "column_name"),
                SumFunction(
                    self,
                    CaseExpression(
                        self,
                        cases=[
                            (
                                IsNullPredicate(self, Column(self, column_name)),
                                Literal(self, 1, inline=True),
                            )
                        ],
                        else_result=Literal(self, 0, inline=True),
                    ),
                ).as_("null_count"),
                CountFunction(self, Column(self, column_name), distinct=True).as_("distinct_count"),
                FunctionCall(self, "MIN", Column(self, column_name)).as_("min_value"),
                FunctionCall(self, "MAX", Column(self, column_name)).as_("max_value"),
                CountFunction(self, RowCountWildcard(self)).as_("row_count"),
                self._profile_label("aggregate", "source"),
            ],
            from_=Table(self, table_name, catalog_name=schema or None),
        )

    def format_column_data_profile_query_statement(
        self, expr: "ColumnDataProfileQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a per-column profile by aggregating the rows themselves.

        The engine's statistics catalogue was audited and refused -- see
        :meth:`supports_column_data_profile` for what it does and does not
        carry -- so every figure here is counted, and the row says so: the
        ``aggregate`` label is projected *into* each row rather than stamped
        onto the result afterwards, so a consumer comparing a MariaDB profile
        with a PostgreSQL estimate can tell the two apart without knowing
        which engine it asked. Sorting them out afterwards is the one thing
        the label must not require.

        One arm per column, over the column list the expression carries: SQL
        cannot pivot ``SUM(CASE WHEN col IS NULL ...)`` across columns it was
        never told about, so an aggregating dialect genuinely needs that list
        where a catalogue-based one does not.

        The compound question is one node rather than a join of rendered text.
        Every arm is a real :class:`~...expression.statements.dql.QueryStatement`
        -- the renderer owns its projection, its identifiers and its relation --
        and the arms are handed to a
        :class:`~...expression.statements.dql.SetOperationStatement` as its
        ``parts``. A column list known only at run time has no operand in the
        tree, which is why this is the *statement* shape and not the binary
        ``SetOperation`` source: folding N arms into two nested binary nodes
        would describe a tree nobody wrote. The node joins the parts with the
        dialect's own operator word and concatenates their parameters in arm
        order itself, so the returned tuple is the one this method once built
        by hand. Nothing here is text.

        ``null_count`` rather than a fraction: dividing by a row count that
        may legitimately be zero belongs in the parser, not in a SQL
        expression that would then have to guard against it. That is also what
        keeps an empty table from answering ``0.0`` -- ``SUM`` over no rows is
        NULL, so the fraction is not derived at all.

        An empty column list answers with no rows. That case cannot arise from
        a real table -- MariaDB requires at least one column -- but the branch
        has to render, so it is a statement that selects no rows rather than a
        special-case string.

        One consequence of the union is worth reading before the figures are:
        MariaDB resolves *one* result type per column position across every
        arm, so ``min_value`` -- which carries ``code``'s text in one arm and
        ``amount``'s decimal in another -- arrives as text, ``'1.00'`` rather
        than a number. The values are exact; only the Python type is the
        union's. One query per column would keep each type, at the price of a
        round trip per column, which is the loop this family exists to avoid.
        """
        from rhosocial.activerecord.backend.expression import (
            ComparisonPredicate,
            Literal,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        schema = params.get("schema")

        arms = [self._profile_arm(params.get("table_name"), schema, name) for name in expr.columns]

        if not arms:
            return QueryStatement(
                self,
                select=[self._profile_label(None, "column_name")],
                where=WhereClause(
                    self,
                    ComparisonPredicate(
                        self,
                        "eq",
                        Literal(self, 0, inline=True),
                        Literal(self, 1, inline=True),
                    ),
                ),
            ).to_sql()

        # The arms are real QueryStatement nodes, so the compound question is
        # one node rather than a join of rendered strings: the operator word is
        # the dialect's, and the projection, identifiers and bind parameters of
        # every arm stay with the renderer that owns them.
        from rhosocial.activerecord.backend.expression.query_sources import (
            SetOperationKind,
        )
        from rhosocial.activerecord.backend.expression.statements import (
            SetOperationStatement,
        )

        return SetOperationStatement(self, op=SetOperationKind.UNION_ALL, parts=arms).to_sql()

    def format_column_value_sample_query_statement(
        self, expr: "ColumnValueSampleQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a most-frequent-values listing with a grouped scan.

        Nothing usable is precomputed in MariaDB -- the catalogue keeps
        histogram buckets, not the values in them -- so this costs a ``GROUP
        BY`` over the column plus a sort of the groups: the same order as the
        profile itself, which is why the two are separate probes rather than
        one call that would make the cheap half pay for the dear one.

        ``ORDER BY COUNT(*) DESC`` is what makes the answer "the most frequent
        values" rather than "the first values"; ties break by the value so two
        runs of the same query agree. The ``LIMIT`` is a bind parameter, as it
        is everywhere else in this dialect: keeping it bound means the
        caller's integer is never spliced into statement text, and MariaDB
        accepts it once the placeholder reaches it as a number.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            CountFunction,
            GroupByHavingClause,
            LimitOffsetClause,
            OrderByClause,
            QueryStatement,
            RowCountWildcard,
        )
        from rhosocial.activerecord.backend.expression.objects import Table

        relation = Table(self, expr.table_name, catalog_name=expr.schema or None)
        column = Column(self, expr.column_name)

        return QueryStatement(
            self,
            select=[
                column.as_("value"),
                CountFunction(self, RowCountWildcard(self)).as_("count"),
            ],
            from_=relation,
            group_by_having=GroupByHavingClause(self, group_by=[Column(self, expr.column_name)]),
            order_by=OrderByClause(
                self,
                expressions=[
                    (CountFunction(self, RowCountWildcard(self)), "DESC"),
                    (Column(self, expr.column_name), "ASC"),
                ],
            ),
            limit_offset=LimitOffsetClause(self, limit=int(expr.limit)),
        ).to_sql()

    def _coverage_fraction(self, column, source, other_column, other_source):
        """One side of the overlap: the share of *column* the other side holds.

        The numerator counts the *distinct* values of *column* that also occur
        in *other_column*, as a ``COUNT(*)`` over a derived table of those
        distinct values; the denominator counts *column*'s distinct non-NULL
        values. Distinct on both sides is what makes the figure a coverage of
        values rather than of rows -- a key repeated a thousand times that
        matches once would otherwise read as well covered.

        ``IS NOT NULL`` is written on both halves rather than relied upon. In
        the numerator it is load-bearing: a DISTINCT treats a NULL as one
        value, so counting it would credit the tested side with a match it
        does not have. In the divisor ``COUNT(DISTINCT ...)`` skips NULLs on
        its own, but the statement says so explicitly, because the share is of
        the values that could join and that is the fact being measured.
        ``NULLIF(..., 0)`` then makes a column with no value at all answer
        NULL rather than 0, which the parser reads as "no fraction": the
        difference between "nothing matched" and "nothing to match" survives
        to the caller.

        There is no ``* 1.0`` here, unlike PostgreSQL's version of this
        method: MariaDB's ``/`` over two integer counts already answers a
        fractional DECIMAL, so multiplying first would add noise and change
        nothing. The division is kept as a plain node division because that is
        the spelling both engines of this family agree on.
        """
        from rhosocial.activerecord.backend.expression import (
            FunctionCall,
            InPredicate,
            Literal,
            LogicalPredicate,
            QueryStatement,
            RowCountWildcard,
            SelectModifier,
            Subquery,
            WhereClause,
        )
        from rhosocial.activerecord.backend.expression.functions import (
            CountFunction,
        )
        from rhosocial.activerecord.backend.expression.sources import (
            DerivedTableSource,
        )

        overlap = QueryStatement(
            self,
            select=[column],
            from_=source,
            where=WhereClause(
                self,
                LogicalPredicate(
                    self,
                    "AND",
                    column.is_not_null(),
                    InPredicate(
                        self,
                        column,
                        Subquery(
                            self,
                            QueryStatement(
                                self,
                                select=[other_column],
                                from_=other_source,
                                where=WhereClause(self, other_column.is_not_null()),
                            ),
                        ),
                    ),
                ),
            ),
            select_modifier=SelectModifier.DISTINCT,
        )
        covered = Subquery(
            self,
            QueryStatement(
                self,
                select=[CountFunction(self, RowCountWildcard(self))],
                from_=DerivedTableSource(self, overlap, alias="covered"),
            ),
        )
        total = Subquery(
            self,
            QueryStatement(
                self,
                select=[
                    FunctionCall(
                        self,
                        "NULLIF",
                        CountFunction(self, column, distinct=True),
                        Literal(self, 0, inline=True),
                    )
                ],
                from_=source,
                where=WhereClause(self, column.is_not_null()),
            ),
        )
        return covered / total

    def format_join_coverage_query_statement(
        self, expr: "JoinCoverageQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a two-sided measurement of two columns' value domains.

        Unlike every other statement in this module, this one names two user
        tables rather than one catalogue relation: the question is a relation
        between two objects, so both sides are carried explicitly and their
        identifiers are the dialect's to quote (see :meth:`_user_relation`).
        The aliases ``l`` and ``r`` are what keep the two columns apart in the
        rendered statement, and they are quoted like every other identifier.

        The row carries both fractions because neither is meaningful alone. A
        left share of 1.0 beside a right share of 0.2 says every tested value
        exists on the other side while most of that other domain is
        unaccounted for; a single similarity score would average the two and
        describe neither. A caller deciding whether a join is worth writing
        needs to know which direction is incomplete.

        Both figures are counted over *distinct* values, with NULLs excluded
        from the numerators and the denominators alike -- a NULL is not a value
        that could ever join, so it belongs in neither half of the fraction.
        The denominators are ``NULLIF``-guarded so a column with nothing to
        match answers NULL, which the parser reports as "no measurement"
        instead of a zero overlap that would read as a real answer. See
        :meth:`_coverage_fraction` for both rules in place.

        The cost is the two sides read for their distinct domains plus an
        intersection of the two -- a double scan, and the reason the probe
        belongs behind an explicit call rather than in any automatic pass.

        Collations are not reconciled. MariaDB compares the two columns under
        whichever collation applies, so values the database would treat as
        equal may be counted as distinct here, and the fractions are a *lower*
        bound across mismatched collations -- never an upper one.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            QueryStatement,
        )

        params = expr.get_params()
        schema = params.get("schema")

        left_source = self._user_relation(params.get("left_table"), "l", schema)
        right_source = self._user_relation(params.get("right_table"), "r", schema)
        left_column = Column(self, params.get("left_column"), table="l")
        right_column = Column(self, params.get("right_column"), table="r")

        return QueryStatement(
            self,
            select=[
                self._coverage_fraction(left_column, left_source, right_column, right_source).as_(
                    "left_coverage"
                ),
                self._coverage_fraction(right_column, right_source, left_column, left_source).as_(
                    "right_coverage"
                ),
            ],
        ).to_sql()


__all__ = [
    'MariaDBIntrospectionMixin',
    'SYSTEM_SCHEMAS',
    'INFORMATION_SCHEMA_DATABASE',
    'SEQUENCES_SINCE',
    'SEQUENCE_DETAILS_SINCE',
]