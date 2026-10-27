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
from typing import List, Tuple, TYPE_CHECKING

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
            ComparisonPredicate(self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema))
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
                Column(self, "DATA_LENGTH"),
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


__all__ = [
    'MariaDBIntrospectionMixin',
    'SYSTEM_SCHEMAS',
    'INFORMATION_SCHEMA_DATABASE',
    'SEQUENCES_SINCE',
    'SEQUENCE_DETAILS_SINCE',
]
