# src/rhosocial/activerecord/backend/impl/mariadb/expression/status.py
"""MariaDB server-status expressions.

The status introspector used to hold the catalog SQL itself: plain string
literals for ``SELECT VERSION()``, ``mysql.user``, the storage totals and the
database listing, plus an f-string per ``SHOW ... LIKE '...'``. A SQL string is
a formatting artefact, so it belongs to the dialect formatter rather than to the
layer that executes the query (expression-dialect §16.2): the node collects the
parameters, the formatter writes the text, and the introspector only constructs
and executes.

Each node carries only the parameters its query needs, and every parameter is
given at construction -- there is no fluent builder, so the artifact is the
constructor call and nothing else.
"""

from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MariaDBSystemVariableExpression",
    "MariaDBVersionQuery",
    "MariaDBStorageSizeQuery",
    "MariaDBDatabaseListQuery",
    "MariaDBUserListQuery",
    "MariaDBSessionInfoQuery",
]


class MariaDBSystemVariableExpression(BaseExpression):
    """A server system variable, read as the ``@@name`` value.

    ``@@hostname`` is not a column and not a function call: it is a reference to
    a run-time parameter, which MariaDB spells with the ``@@`` sigil. The sigil
    is the dialect's spelling, so it lives in the formatter; the node carries
    the variable's name.

    The name is validated at construction. MariaDB's variable names are
    identifiers, so a name carrying a quote, a space or a stray ``@`` fails
    here, at the caller, instead of being spliced into a statement.

    Example:
        >>> MariaDBSystemVariableExpression(d, "have_ssl", alias="have_ssl").to_sql()
        ('@@have_ssl AS `have_ssl`', ())
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        if not isinstance(name, str) or not name or not all(
            part.isidentifier() for part in name.replace("@@", "").split(".")
        ):
            raise ValueError(
                "a system variable name is an identifier (optionally dotted), "
                f"got {name!r}"
            )
        self.name = name
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mariadb_system_variable_expression"


class MariaDBVersionQuery(BaseExpression):
    """``SELECT VERSION()`` -- the server version string, and nothing else."""

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mariadb_version_query"


class MariaDBStorageSizeQuery(BaseExpression):
    """The summed data and index bytes of every user schema.

    The system schemas are excluded, because their size is the server's own
    bookkeeping rather than the caller's data.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mariadb_storage_size_query"


class MariaDBDatabaseListQuery(BaseExpression):
    """Every schema with its byte size and its table/view counts."""

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mariadb_database_list_query"


class MariaDBUserListQuery(BaseExpression):
    """The accounts MariaDB knows, with the superuser flag."""

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mariadb_user_list_query"


class MariaDBSessionInfoQuery(BaseExpression):
    """The facts about the current session: user, database, host, TLS.

    Four values, four different shapes -- a function, a function, a system
    variable, a system variable -- which is why the query is a node rather than
    a string with four spellings baked into it.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mariadb_session_info_query"
