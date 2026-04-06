# src/rhosocial/activerecord/backend/impl/mariadb/show/expressions.py
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

from typing import Any, Dict, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ...dialect import MariaDBDialect


class ShowExpression(BaseExpression):
    """Base class for MariaDB SHOW command expressions.

    All MariaDB SHOW expressions inherit from this class and provide
    fluent API for setting parameters.
    """

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._schema: Optional[str] = None

    def schema(self, name: str) -> "ShowExpression":
        """Set the schema/database name.

        Args:
            name: Schema or database name.

        Returns:
            Self for method chaining.
        """
        self._schema = name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters.

        Returns:
            Dictionary containing all parameters.
        """
        params: Dict[str, Any] = {}
        if self._schema is not None:
            params["schema"] = self._schema
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL. Subclasses must implement this method."""
        raise NotImplementedError("Subclasses must implement to_sql() method")


class ShowCreateTableExpression(ShowExpression):
    """Expression for SHOW CREATE TABLE command."""

    def __init__(self, dialect: "MariaDBDialect", table_name: str):
        super().__init__(dialect)
        self._table_name = table_name

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_create_table(self)


class ShowCreateViewExpression(ShowExpression):
    """Expression for SHOW CREATE VIEW command."""

    def __init__(self, dialect: "MariaDBDialect", view_name: str):
        super().__init__(dialect)
        self._view_name = view_name

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        params["view_name"] = self._view_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_create_view(self)


class ShowColumnsExpression(ShowExpression):
    """Expression for SHOW [FULL] COLUMNS command."""

    def __init__(self, dialect: "MariaDBDialect", table_name: str):
        super().__init__(dialect)
        self._table_name = table_name
        self._full = False
        self._like_pattern: Optional[str] = None

    def full(self) -> "ShowColumnsExpression":
        """Request full column information."""
        self._full = True
        return self

    def like(self, pattern: str) -> "ShowColumnsExpression":
        """Filter columns by pattern."""
        self._like_pattern = pattern
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        params["table_name"] = self._table_name
        params["full"] = self._full
        if self._like_pattern is not None:
            params["like_pattern"] = self._like_pattern
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_columns(self)


class ShowIndexExpression(ShowExpression):
    """Expression for SHOW INDEX command."""

    def __init__(self, dialect: "MariaDBDialect", table_name: str):
        super().__init__(dialect)
        self._table_name = table_name

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_index(self)


class ShowTablesExpression(ShowExpression):
    """Expression for SHOW [FULL] TABLES command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._full = False
        self._like_pattern: Optional[str] = None

    def full(self) -> "ShowTablesExpression":
        """Request full table information including table type."""
        self._full = True
        return self

    def like(self, pattern: str) -> "ShowTablesExpression":
        """Filter tables by pattern."""
        self._like_pattern = pattern
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        params["full"] = self._full
        if self._like_pattern is not None:
            params["like_pattern"] = self._like_pattern
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_tables(self)


class ShowDatabasesExpression(ShowExpression):
    """Expression for SHOW DATABASES command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._like_pattern: Optional[str] = None

    def like(self, pattern: str) -> "ShowDatabasesExpression":
        """Filter databases by pattern."""
        self._like_pattern = pattern
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        if self._like_pattern is not None:
            params["like_pattern"] = self._like_pattern
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_databases(self)


class ShowTableStatusExpression(ShowExpression):
    """Expression for SHOW TABLE STATUS command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._like_pattern: Optional[str] = None

    def like(self, pattern: str) -> "ShowTableStatusExpression":
        """Filter tables by pattern."""
        self._like_pattern = pattern
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        if self._like_pattern is not None:
            params["like_pattern"] = self._like_pattern
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_table_status(self)


class ShowTriggersExpression(ShowExpression):
    """Expression for SHOW TRIGGERS command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._table_name: Optional[str] = None

    def for_table(self, table_name: str) -> "ShowTriggersExpression":
        """Filter triggers for a specific table."""
        self._table_name = table_name
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        if self._table_name is not None:
            params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_triggers(self)


class ShowCreateTriggerExpression(ShowExpression):
    """Expression for SHOW CREATE TRIGGER command."""

    def __init__(self, dialect: "MariaDBDialect", trigger_name: str):
        super().__init__(dialect)
        self._trigger_name = trigger_name

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        params["trigger_name"] = self._trigger_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_create_trigger(self)


class ShowVariablesExpression(ShowExpression):
    """Expression for SHOW VARIABLES command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._like_pattern: Optional[str] = None
        self._session = True

    def like(self, pattern: str) -> "ShowVariablesExpression":
        """Filter variables by pattern."""
        self._like_pattern = pattern
        return self

    def global_vars(self) -> "ShowVariablesExpression":
        """Show global variables instead of session variables."""
        self._session = False
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        params["session"] = self._session
        if self._like_pattern is not None:
            params["like_pattern"] = self._like_pattern
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_variables(self)


class ShowStatusExpression(ShowExpression):
    """Expression for SHOW STATUS command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._like_pattern: Optional[str] = None
        self._session = True

    def like(self, pattern: str) -> "ShowStatusExpression":
        """Filter status by pattern."""
        self._like_pattern = pattern
        return self

    def global_status(self) -> "ShowStatusExpression":
        """Show global status instead of session status."""
        self._session = False
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        params["session"] = self._session
        if self._like_pattern is not None:
            params["like_pattern"] = self._like_pattern
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_status(self)


class ShowProcessListExpression(ShowExpression):
    """Expression for SHOW PROCESSLIST command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._full = False

    def full(self) -> "ShowProcessListExpression":
        """Show full process list."""
        self._full = True
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        params["full"] = self._full
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_processlist(self)


class ShowWarningsExpression(ShowExpression):
    """Expression for SHOW WARNINGS command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._limit: Optional[int] = None

    def limit(self, count: int) -> "ShowWarningsExpression":
        """Limit the number of warnings returned."""
        self._limit = count
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        if self._limit is not None:
            params["limit"] = self._limit
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_warnings(self)


class ShowErrorsExpression(ShowExpression):
    """Expression for SHOW ERRORS command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._limit: Optional[int] = None

    def limit(self, count: int) -> "ShowErrorsExpression":
        """Limit the number of errors returned."""
        self._limit = count
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        if self._limit is not None:
            params["limit"] = self._limit
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_errors(self)


class ShowEnginesExpression(ShowExpression):
    """Expression for SHOW ENGINES command."""

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_engines(self)


class ShowCharsetExpression(ShowExpression):
    """Expression for SHOW CHARACTER SET command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._like_pattern: Optional[str] = None

    def like(self, pattern: str) -> "ShowCharsetExpression":
        """Filter character sets by pattern."""
        self._like_pattern = pattern
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        if self._like_pattern is not None:
            params["like_pattern"] = self._like_pattern
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_charset(self)


class ShowCollationExpression(ShowExpression):
    """Expression for SHOW COLLATION command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._like_pattern: Optional[str] = None

    def like(self, pattern: str) -> "ShowCollationExpression":
        """Filter collations by pattern."""
        self._like_pattern = pattern
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        if self._like_pattern is not None:
            params["like_pattern"] = self._like_pattern
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_collation(self)


class ShowGrantsExpression(ShowExpression):
    """Expression for SHOW GRANTS command."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)
        self._user: Optional[str] = None
        self._host: Optional[str] = None

    def for_user(self, user: str, host: Optional[str] = None) -> "ShowGrantsExpression":
        """Show grants for a specific user."""
        self._user = user
        self._host = host
        return self

    def get_params(self) -> Dict[str, Any]:
        params = super().get_params()
        if self._user is not None:
            params["user"] = self._user
        if self._host is not None:
            params["host"] = self._host
        return params

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_grants(self)


class ShowPluginsExpression(ShowExpression):
    """Expression for SHOW PLUGINS command."""

    def to_sql(self) -> SQLQueryAndParams:
        return self._dialect.format_show_plugins(self)
