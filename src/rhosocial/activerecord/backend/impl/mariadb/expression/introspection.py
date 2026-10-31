# src/rhosocial/activerecord/backend/impl/mariadb/expression/introspection.py
"""MariaDB introspection expressions.

Two catalogue reads the cross-backend introspection model has no statement
for: sequences and table options. Both read ``information_schema``. As with
the status nodes, the node carries the parameters and the dialect formatter
writes the text (expression-dialect §16.2), so what the query asks stays a
structure and only MariaDB's spelling lives in the formatter.
"""

from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MariaDBSequenceQuery",
    "MariaDBTableOptionsQuery",
]


class MariaDBSequenceQuery(BaseExpression):
    """The sequences in one schema, optionally narrowed to one name.

    ``name=None`` asks for the list; a name asks the same question about one
    sequence. Both shapes read ``information_schema.TABLES`` filtered to
    ``TABLE_TYPE='SEQUENCE'`` -- a sequence is a table on MariaDB. The
    formatter adds ``information_schema.SEQUENCES`` to the read only when the
    server has that view (11.7+), because the view is the only place the
    numeric facts live.

    The schema is required and is the schema to read, not "the default one":
    resolving the default is the introspector's job, and letting the node
    decide would give the same question two answers.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: str,
        name: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.schema = schema
        self.name = name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mariadb_sequence_query"


class MariaDBTableOptionsQuery(BaseExpression):
    """The storage options of every relation in one schema, or of one.

    One row per entry in ``information_schema.TABLES``: base tables, views and
    sequences alike, each carrying the options the server reports for it. The
    caller filters by ``table_type`` when it wants only base tables; filtering
    here would hide the relation's real type from a caller asking about it by
    name.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: str,
        table_name: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.schema = schema
        self.table_name = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mariadb_table_options_query"
