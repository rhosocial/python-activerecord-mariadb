# src/rhosocial/activerecord/backend/impl/mariadb/expression/show.py
"""
MariaDB SHOW command expression classes.

This module defines expression classes for MariaDB SHOW commands.
Each expression class collects parameters and delegates SQL generation
to the dialect's format_show_* methods.

MariaDB SHOW commands are fully compatible with MySQL SHOW commands.

Expression classes inherit from BaseExpression and implement to_sql(),
following the expression-dialect pattern used throughout the codebase.

Key design:
- Expressions collect parameters (table_name, schema, options)
- Expressions hold a dialect reference
- to_sql() delegates to dialect.format_show_* methods
- Dialect handles actual SQL generation
"""

from typing import Any, Dict, Optional, TYPE_CHECKING, Union

from rhosocial.activerecord.backend.expression.bases import BaseExpression, SQLQueryAndParams
from rhosocial.activerecord.backend.expression.objects import (
    RelationObject,
    Table,
    Trigger,
    View,
)

if TYPE_CHECKING:
    from ..dialect import MariaDBDialect


class ShowExpression(BaseExpression):
    """Base class for MariaDB SHOW command expressions.

    All MariaDB SHOW expressions inherit from this class and provide
    fluent API for setting parameters.
    """

    def __init__(self, dialect: "MariaDBDialect", *, schema: Optional[str] = None):
        super().__init__(dialect)
        self._schema = schema

    def schema(self, name: str) -> "ShowExpression":
        """Set the schema/database name.

        Args:
            name: Schema or database name.

        Returns:
            Self for method chaining.
        """
        self._schema = name
        return self

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL. Subclasses must implement this method."""
        raise NotImplementedError("Subclasses must implement to_sql() method")


class ShowRelationExpression(ShowExpression):
    """Base for the SHOW commands that name one relation.

    ``SHOW CREATE TABLE``, ``SHOW CREATE VIEW``, ``SHOW COLUMNS`` and
    ``SHOW INDEX`` all name a single relation, and a relation is one
    concept: it lives in a namespace and has a name inside it. Treating
    the table and the view as two separate things here duplicated the
    same identity four times over and left nowhere for the database to
    live, which is why a ``SHOW COLUMNS FROM app.users`` could not be
    written without hand-building the qualified name.

    The relation is therefore one attribute, :attr:`relation`, and the
    ``schema()`` setter above folds the database into it. A bare string
    is accepted as shorthand for an unqualified relation; a
    ``(database, name)`` tuple is refused, because an ordered pair cannot
    say which part is which.

    Each concrete statement keeps its own dialect formatter: what differs
    between them is the verb and the options, not the name.
    """

    #: The relation kind a bare name is read as. ``ShowCreateTableExpression``
    #: and the table-shaped statements leave this as :class:`Table`;
    #: ``ShowCreateViewExpression`` narrows it to :class:`View`. Both are
    #: relations, so both render through the same qualified-name path.
    relation_kind: type = Table

    def __init__(self, dialect: "MariaDBDialect", relation: Union[RelationObject, str]):
        super().__init__(dialect)
        self._relation: RelationObject = self._as_relation(relation)

    def _as_relation(self, relation: Union[RelationObject, str]) -> RelationObject:
        """Return *relation* as a relation object of this statement's kind.

        Raises:
            TypeError: *relation* is neither a relation object nor a
                string.
        """
        if isinstance(relation, RelationObject):
            return relation
        if isinstance(relation, str):
            return self.relation_kind(self._dialect, relation)
        if isinstance(relation, tuple):
            raise TypeError(
                "SHOW targets are schema objects, not (database, name) "
                f"tuples: pass {self.relation_kind.__name__}({relation[-1]!r}, "
                f"catalog_name={relation[0]!r}) instead of {relation!r}"
            )
        raise TypeError(
            f"relation must be a {self.relation_kind.__name__} or a name string, "
            f"got {type(relation).__name__}"
        )

    def schema(self, name: str) -> "ShowRelationExpression":
        """Set the database the relation lives in."""
        super().schema(name)
        self._relation.catalog_name = name
        return self

    @property
    def relation(self) -> RelationObject:
        """The relation this statement names, database included."""
        return self._relation


class ShowCreateTableExpression(ShowRelationExpression):
    """Expression for SHOW CREATE TABLE command."""

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_create_table(self)


class ShowCreateViewExpression(ShowRelationExpression):
    """Expression for SHOW CREATE VIEW command."""

    #: A view is a relation; naming it as one is what lets the same
    #: qualified-name renderer serve both SHOW CREATE forms.
    relation_kind = View

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_create_view(self)


class ShowColumnsExpression(ShowRelationExpression):
    """Expression for SHOW [FULL] COLUMNS command."""

    def __init__(self, dialect: "MariaDBDialect", relation: Union[RelationObject, str],
                 *, full: bool = False, like_pattern: Optional[str] = None):
        super().__init__(dialect, relation)
        self._full = full
        self._like_pattern = like_pattern

    def full(self) -> "ShowColumnsExpression":
        """Request full column information."""
        self._full = True
        return self

    def like(self, pattern: str) -> "ShowColumnsExpression":
        """Filter columns by pattern."""
        self._like_pattern = pattern
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_columns(self)


class ShowIndexExpression(ShowRelationExpression):
    """Expression for SHOW INDEX command."""

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_index(self)


class ShowTablesExpression(ShowExpression):
    """Expression for SHOW [FULL] TABLES command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, full: bool = False, like_pattern: Optional[str] = None):
        super().__init__(dialect)
        self._full = full
        self._like_pattern = like_pattern

    def full(self) -> "ShowTablesExpression":
        """Request full table information including table type."""
        self._full = True
        return self

    def like(self, pattern: str) -> "ShowTablesExpression":
        """Filter tables by pattern."""
        self._like_pattern = pattern
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_tables(self)


class ShowDatabasesExpression(ShowExpression):
    """Expression for SHOW DATABASES command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None):
        super().__init__(dialect)
        self._like_pattern = like_pattern

    def like(self, pattern: str) -> "ShowDatabasesExpression":
        """Filter databases by pattern."""
        self._like_pattern = pattern
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_databases(self)


class ShowTableStatusExpression(ShowExpression):
    """Expression for SHOW TABLE STATUS command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None):
        super().__init__(dialect)
        self._like_pattern = like_pattern

    def like(self, pattern: str) -> "ShowTableStatusExpression":
        """Filter tables by pattern."""
        self._like_pattern = pattern
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_table_status(self)


class ShowTriggersExpression(ShowExpression):
    """Expression for SHOW TRIGGERS command.

    ``table_name`` here is a **LIKE pattern**, not a relation reference:
    MariaDB's ``SHOW TRIGGERS`` filters on the name it prints, not on a
    resolved object. It is therefore kept as a plain string and never
    qualified -- a trigger's database comes from ``schema()`` above,
    which is the ``FROM`` clause.
    """

    def __init__(self, dialect: "MariaDBDialect",
                 *, table_name: Optional[str] = None):
        super().__init__(dialect)
        self._table_name = table_name

    def for_table(self, table_name: str) -> "ShowTriggersExpression":
        """Filter triggers by table name pattern."""
        self._table_name = table_name
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_triggers(self)


class ShowCreateTriggerExpression(ShowExpression):
    """Expression for SHOW CREATE TRIGGER command."""

    def __init__(self, dialect: "MariaDBDialect", trigger: Union[Trigger, str]):
        super().__init__(dialect)
        self._trigger: Trigger = self._as_trigger(trigger)

    def _as_trigger(self, trigger: Union[Trigger, str]) -> Trigger:
        """Return *trigger* as a :class:`Trigger`.

        Raises:
            TypeError: *trigger* is neither a trigger object nor a string.
        """
        if isinstance(trigger, Trigger):
            return trigger
        if isinstance(trigger, str):
            return Trigger(self._dialect, trigger)
        if isinstance(trigger, tuple):
            raise TypeError(
                "a trigger name is a schema object, not a (database, name) "
                f"tuple: pass Trigger({trigger[-1]!r}, "
                f"catalog_name={trigger[0]!r}) instead of {trigger!r}"
            )
        raise TypeError(
            f"trigger must be a Trigger or a name string, "
            f"got {type(trigger).__name__}"
        )

    def schema(self, name: str) -> "ShowCreateTriggerExpression":
        """Set the database the trigger lives in."""
        super().schema(name)
        self._trigger.catalog_name = name
        return self

    @property
    def trigger(self) -> Trigger:
        """The trigger this statement names, database included."""
        return self._trigger

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_create_trigger(self)


class ShowVariablesExpression(ShowExpression):
    """Expression for SHOW VARIABLES command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None, session: bool = True):
        super().__init__(dialect)
        self._like_pattern = like_pattern
        self._session = session

    def like(self, pattern: str) -> "ShowVariablesExpression":
        """Filter variables by pattern."""
        self._like_pattern = pattern
        return self

    def global_vars(self) -> "ShowVariablesExpression":
        """Show global variables instead of session variables."""
        self._session = False
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_variables(self)


class ShowStatusExpression(ShowExpression):
    """Expression for SHOW STATUS command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None, session: bool = True):
        super().__init__(dialect)
        self._like_pattern = like_pattern
        self._session = session

    def like(self, pattern: str) -> "ShowStatusExpression":
        """Filter status by pattern."""
        self._like_pattern = pattern
        return self

    def global_status(self) -> "ShowStatusExpression":
        """Show global status instead of session status."""
        self._session = False
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_status(self)


class ShowProcessListExpression(ShowExpression):
    """Expression for SHOW PROCESSLIST command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, full: bool = False):
        super().__init__(dialect)
        self._full = full

    def full(self) -> "ShowProcessListExpression":
        """Show full process list."""
        self._full = True
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_processlist(self)


class ShowWarningsExpression(ShowExpression):
    """Expression for SHOW WARNINGS command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, limit: Optional[int] = None):
        super().__init__(dialect)
        self._limit = limit

    def limit(self, count: int) -> "ShowWarningsExpression":
        """Limit the number of warnings returned."""
        self._limit = count
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_warnings(self)


class ShowErrorsExpression(ShowExpression):
    """Expression for SHOW ERRORS command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, limit: Optional[int] = None):
        super().__init__(dialect)
        self._limit = limit

    def limit(self, count: int) -> "ShowErrorsExpression":
        """Limit the number of errors returned."""
        self._limit = count
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_errors(self)


class ShowEnginesExpression(ShowExpression):
    """Expression for SHOW ENGINES command."""

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_engines(self)


class ShowCharsetExpression(ShowExpression):
    """Expression for SHOW CHARACTER SET command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None):
        super().__init__(dialect)
        self._like_pattern = like_pattern

    def like(self, pattern: str) -> "ShowCharsetExpression":
        """Filter character sets by pattern."""
        self._like_pattern = pattern
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_charset(self)


class ShowCollationExpression(ShowExpression):
    """Expression for SHOW COLLATION command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None):
        super().__init__(dialect)
        self._like_pattern = like_pattern

    def like(self, pattern: str) -> "ShowCollationExpression":
        """Filter collations by pattern."""
        self._like_pattern = pattern
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_collation(self)


class ShowGrantsExpression(ShowExpression):
    """Expression for SHOW GRANTS command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, user: Optional[str] = None, host: Optional[str] = None):
        super().__init__(dialect)
        self._user = user
        self._host = host

    def for_user(self, user: str, host: Optional[str] = None) -> "ShowGrantsExpression":
        """Show grants for a specific user."""
        self._user = user
        self._host = host
        return self

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_grants(self)


class ShowPluginsExpression(ShowExpression):
    """Expression for SHOW PLUGINS command."""

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_plugins(self)
