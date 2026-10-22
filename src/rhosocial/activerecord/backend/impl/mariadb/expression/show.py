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
- Expressions collect every parameter at construction; there is no fluent
  builder, so an instance is complete the moment ``get_params()`` reads it
  back (the artifact is the constructor call, nothing else).
- Expressions hold a dialect reference
- to_sql() delegates to dialect.format_show_* methods
- Dialect handles actual SQL generation
"""

from typing import Optional, TYPE_CHECKING, Union

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

    All MariaDB SHOW expressions inherit from this class. Parameters are
    declared by each ``__init__`` -- that signature is the wire contract, so
    a parameter is always passed where the node is built rather than filled
    in afterwards.
    """

    def __init__(self, dialect: "MariaDBDialect", *, schema: Optional[str] = None):
        super().__init__(dialect)
        # Stored under the parameter's own name so get_params() reads it
        # without a detour.
        self.schema = schema

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
    database travels inside it -- :class:`~...objects.relation.Table` and
    :class:`~...objects.relation.View` carry ``catalog_name``. A bare string
    is accepted as shorthand for an unqualified relation; a
    ``(database, name)`` tuple is refused, because an ordered pair cannot
    say which part is which.

    Each concrete statement keeps its own dialect formatter: what differs
    between them is the verb and the options, not the name.
    """

    #: The relation kind a bare name is read as. ``ShowCreateTableStatement``
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

    @property
    def relation(self) -> RelationObject:
        """The relation this statement names, database included."""
        return self._relation


class ShowCreateTableStatement(ShowRelationExpression):
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
        # Both stored under their parameter names, and both given at
        # construction: a column list is fully described by its target, its
        # verbosity and its pattern.
        self.full = full
        self.like_pattern = like_pattern

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_columns(self)


class ShowIndexExpression(ShowRelationExpression):
    """Expression for SHOW INDEX command."""

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_index(self)


class ShowTablesExpression(ShowExpression):
    """Expression for SHOW [FULL] TABLES command.

    ``schema`` is declared on this class, not only on the base, because
    ``get_params()`` reads the class's own ``__init__`` signature: a
    qualifier stored by the base alone would be invisible to the
    serializer and the ``FROM`` clause would fall out of the artifact.
    """

    def __init__(self, dialect: "MariaDBDialect",
                 *, schema: Optional[str] = None,
                 full: bool = False, like_pattern: Optional[str] = None):
        super().__init__(dialect, schema=schema)
        self.full = full
        self.like_pattern = like_pattern

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_tables(self)


class ShowDatabasesExpression(ShowExpression):
    """Expression for SHOW DATABASES command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None):
        super().__init__(dialect)
        self.like_pattern = like_pattern

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_databases(self)


class ShowTableStatusExpression(ShowExpression):
    """Expression for SHOW TABLE STATUS command.

    ``schema`` is declared here for the same reason as on
    :class:`ShowTablesExpression`: the ``FROM`` qualifier has to be a
    parameter of the class the serializer reads.
    """

    def __init__(self, dialect: "MariaDBDialect",
                 *, schema: Optional[str] = None,
                 like_pattern: Optional[str] = None):
        super().__init__(dialect, schema=schema)
        self.like_pattern = like_pattern

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_table_status(self)


class ShowTriggersExpression(ShowExpression):
    """Expression for SHOW TRIGGERS command.

    ``table_name`` here is a **LIKE pattern**, not a relation reference:
    MariaDB's ``SHOW TRIGGERS`` filters on the name it prints, not on a
    resolved object. It is therefore kept as a plain string and never
    qualified -- the database comes from ``schema``, which is the ``FROM``
    clause and is declared on this class for the same reason as on
    :class:`ShowTablesExpression`.
    """

    def __init__(self, dialect: "MariaDBDialect",
                 *, schema: Optional[str] = None,
                 table_name: Optional[str] = None):
        super().__init__(dialect, schema=schema)
        self.table_name = table_name

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

    @property
    def trigger(self) -> Trigger:
        """The trigger this statement names, database included."""
        return self._trigger

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_create_trigger(self)


class ShowVariablesExpression(ShowExpression):
    """Expression for SHOW [GLOBAL] VARIABLES command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None, session: bool = True):
        super().__init__(dialect)
        self.like_pattern = like_pattern
        self.session = session

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_variables(self)


class ShowStatusExpression(ShowExpression):
    """Expression for SHOW [GLOBAL] STATUS command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None, session: bool = True):
        super().__init__(dialect)
        self.like_pattern = like_pattern
        self.session = session

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_status(self)


class ShowProcessListExpression(ShowExpression):
    """Expression for SHOW [FULL] PROCESSLIST command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, full: bool = False):
        super().__init__(dialect)
        self.full = full

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_processlist(self)


class ShowWarningsExpression(ShowExpression):
    """Expression for SHOW WARNINGS command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, limit: Optional[int] = None):
        super().__init__(dialect)
        self.limit = limit

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_warnings(self)


class ShowErrorsExpression(ShowExpression):
    """Expression for SHOW ERRORS command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, limit: Optional[int] = None):
        super().__init__(dialect)
        self.limit = limit

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
        self.like_pattern = like_pattern

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_charset(self)


class ShowCollationExpression(ShowExpression):
    """Expression for SHOW COLLATION command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, like_pattern: Optional[str] = None):
        super().__init__(dialect)
        self.like_pattern = like_pattern

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_collation(self)


class ShowGrantsExpression(ShowExpression):
    """Expression for SHOW GRANTS command."""

    def __init__(self, dialect: "MariaDBDialect",
                 *, user: Optional[str] = None, host: Optional[str] = None):
        super().__init__(dialect)
        self.user = user
        self.host = host

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_grants(self)


class ShowPluginsExpression(ShowExpression):
    """Expression for SHOW PLUGINS command."""

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_plugins(self)


__all__ = [
    "ShowExpression",
    "ShowRelationExpression",
    "ShowCreateTableStatement",
    "ShowCreateViewExpression",
    "ShowColumnsExpression",
    "ShowIndexExpression",
    "ShowTablesExpression",
    "ShowDatabasesExpression",
    "ShowTableStatusExpression",
    "ShowTriggersExpression",
    "ShowCreateTriggerExpression",
    "ShowVariablesExpression",
    "ShowStatusExpression",
    "ShowProcessListExpression",
    "ShowWarningsExpression",
    "ShowErrorsExpression",
    "ShowEnginesExpression",
    "ShowCharsetExpression",
    "ShowCollationExpression",
    "ShowGrantsExpression",
    "ShowPluginsExpression",
]
