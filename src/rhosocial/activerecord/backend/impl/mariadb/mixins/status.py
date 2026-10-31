# src/rhosocial/activerecord/backend/impl/mariadb/mixins/status.py
"""MariaDB server-status SQL generation.

The formatters the :mod:`..expression.status` nodes delegate to. Every query is
a tree of core expression nodes -- projections, a join, a where clause, an
ordering -- so what the query *asks* is a structure; only the spellings MariaDB
owns (the ``@@`` sigil, the catalogue's own relation names) are written here.
"""

from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.status import (
        MariaDBDatabaseListQuery,
        MariaDBSessionInfoQuery,
        MariaDBStorageSizeQuery,
        MariaDBSystemVariableExpression,
        MariaDBUserListQuery,
        MariaDBVersionQuery,
    )


class MariaDBStatusDialectMixin:
    """Formatters for the MariaDB server-status expression nodes."""

    # ------------------------------------------------------------------ #
    # The catalogue readers
    # ------------------------------------------------------------------ #

    def _catalog_relation(self, name: str, catalog: str):
        """Return ``catalog``.``name`` as a relation object."""
        from rhosocial.activerecord.backend.expression.objects import Table

        return Table(self, name, catalog_name=catalog)

    def _user_schema_filter(self):
        """Exclude the server's own schemas from a ``TABLE_SCHEMA`` filter."""
        from rhosocial.activerecord.backend.expression import (
            Column,
            InPredicate,
            Literal,
            LogicalPredicate,
        )

        from .introspection import SYSTEM_SCHEMAS

        return LogicalPredicate(
            self,
            "NOT",
            InPredicate(
                self, Column(self, "TABLE_SCHEMA"), Literal(self, SYSTEM_SCHEMAS, inline=True)
            ),
        )

    # ------------------------------------------------------------------ #
    # The formatters
    # ------------------------------------------------------------------ #

    def format_mariadb_system_variable_expression(
        self, expr: "MariaDBSystemVariableExpression"
    ) -> Tuple[str, tuple]:
        """Render a server system variable reference: ``@@name``.

        The ``@@`` sigil is MariaDB's spelling of "read a run-time parameter",
        and it belongs to the dialect rather than to the node. The name was
        validated as an identifier at construction, so it is written as
        received.
        """
        sql = f"@@{expr.name}"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_mariadb_version_query(
        self, expr: "MariaDBVersionQuery"
    ) -> Tuple[str, tuple]:
        """Render ``SELECT VERSION()``.

        No ``FROM``: this query reads no relation, it asks the engine a
        question.
        """
        from rhosocial.activerecord.backend.expression import (
            FunctionCall,
            QueryStatement,
        )

        return QueryStatement(
            self, select=[FunctionCall(self, "VERSION")]
        ).to_sql()

    def format_mariadb_storage_size_query(
        self, expr: "MariaDBStorageSizeQuery"
    ) -> Tuple[str, tuple]:
        """Render the summed data and index bytes of every user schema."""
        from rhosocial.activerecord.backend.expression import (
            Column,
            QueryStatement,
            SumFunction,
            WhereClause,
        )

        from .introspection import INFORMATION_SCHEMA_DATABASE

        query = QueryStatement(
            self,
            select=[
                SumFunction(self, Column(self, "data_length")).as_("data_bytes"),
                SumFunction(self, Column(self, "index_length")).as_("index_bytes"),
            ],
            from_=self._catalog_relation("TABLES", INFORMATION_SCHEMA_DATABASE),
            where=WhereClause(self, self._user_schema_filter()),
        )
        return query.to_sql()

    def format_mariadb_database_list_query(
        self, expr: "MariaDBDatabaseListQuery"
    ) -> Tuple[str, tuple]:
        """Render every schema with its byte size and table/view counts.

        The ``COUNT(CASE WHEN ... THEN 1 END)`` shape is how one grouped read
        counts rows of two kinds at once; the ``1`` is SQL text, not caller
        data, so it goes inline.
        """
        from rhosocial.activerecord.backend.expression import (
            ArithmeticOperation,
            CaseExpression,
            Column,
            ComparisonPredicate,
            CountFunction,
            GroupByHavingClause,
            JoinClause,
            JoinType,
            Literal,
            NamedRelationRef,
            OrderByClause,
            QueryStatement,
            SumFunction,
        )

        from .introspection import INFORMATION_SCHEMA_DATABASE

        def count_of(table_type: str, alias: str):
            return CountFunction(
                self,
                CaseExpression(
                    self,
                    cases=[
                        (
                            ComparisonPredicate(
                                self,
                                "eq",
                                Column(self, "table_type", table="t"),
                                Literal(self, table_type, inline=True),
                            ),
                            Literal(self, 1, inline=True),
                        )
                    ],
                ),
            ).as_(alias)

        join = JoinClause(
            self,
            left_table=NamedRelationRef(
                self,
                self._catalog_relation("SCHEMATA", INFORMATION_SCHEMA_DATABASE),
                alias="s",
            ),
            right_table=NamedRelationRef(
                self,
                self._catalog_relation("TABLES", INFORMATION_SCHEMA_DATABASE),
                alias="t",
            ),
            join_type=JoinType.LEFT,
            condition=ComparisonPredicate(
                self,
                "eq",
                Column(self, "schema_name", table="s"),
                Column(self, "table_schema", table="t"),
            ),
        )

        query = QueryStatement(
            self,
            select=[
                Column(self, "schema_name", table="s"),
                SumFunction(
                    self,
                    ArithmeticOperation(
                        self,
                        "add",
                        Column(self, "data_length", table="t"),
                        Column(self, "index_length", table="t"),
                    ),
                ).as_("size_bytes"),
                count_of("BASE TABLE", "table_count"),
                count_of("VIEW", "view_count"),
            ],
            from_=join,
            group_by_having=GroupByHavingClause(
                self, group_by=[Column(self, "schema_name", table="s")]
            ),
            order_by=OrderByClause(self, [Column(self, "schema_name", table="s")]),
        )
        return query.to_sql()

    def format_mariadb_user_list_query(
        self, expr: "MariaDBUserListQuery"
    ) -> Tuple[str, tuple]:
        """Render the accounts MariaDB knows, with the superuser flag.

        ``mysql`` is a database like any other and is named through the catalog
        slot, not by spelling a dotted prefix into a projection.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            OrderByClause,
            QueryStatement,
        )

        query = QueryStatement(
            self,
            select=[
                Column(self, "user"),
                Column(self, "host"),
                Column(self, "Super_priv"),
            ],
            from_=self._catalog_relation("user", "mysql"),
            order_by=OrderByClause(self, [Column(self, "user")]),
        )
        return query.to_sql()

    def format_mariadb_session_info_query(
        self, expr: "MariaDBSessionInfoQuery"
    ) -> Tuple[str, tuple]:
        """Render the facts about the current session.

        Four values of three shapes -- two function calls, two run-time
        parameters -- each rendered by its own node.
        """
        from rhosocial.activerecord.backend.expression import (
            FunctionCall,
            QueryStatement,
        )

        from ..expression.status import MariaDBSystemVariableExpression

        query = QueryStatement(
            self,
            select=[
                FunctionCall(self, "CURRENT_USER", alias="cur_user"),
                FunctionCall(self, "DATABASE", alias="cur_db"),
                MariaDBSystemVariableExpression(self, "hostname", alias="host"),
                MariaDBSystemVariableExpression(self, "have_ssl", alias="have_ssl"),
            ],
        )
        return query.to_sql()


__all__ = ["MariaDBStatusDialectMixin"]
