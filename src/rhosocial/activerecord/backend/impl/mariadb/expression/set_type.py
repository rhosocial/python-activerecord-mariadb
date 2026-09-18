# src/rhosocial/activerecord/backend/impl/mariadb/expression/set_type.py
"""MariaDB SET type expression classes.

This module provides expression classes for MariaDB SET type operations:
- MariaDBSetLiteralExpression: SET literal value
- MariaDBFindInSetExpression: FIND_IN_SET function
- MariaDBSetContainsExpression: SET contains check
"""

from typing import TYPE_CHECKING, List, Optional

from rhosocial.activerecord.backend.expression.bases import SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBSetLiteralExpression(
    AliasableMixin,
    ComparisonMixin,
    SQLValueExpression,
):
    """MariaDB SET literal value expression.

    Generates a SET literal value for INSERT/UPDATE statements.

    Example:
        >>> expr = MariaDBSetLiteralExpression(dialect, ['read', 'write'])
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        values: List[str],
        column_values: Optional[List[str]] = None,
        *,
        alias: Optional[str] = None,
    ):
        """Initialize SET literal expression.

        Args:
            dialect: SQL dialect
            values: Values to include in the SET
            column_values: Allowed values for the column (for validation)
        """
        super().__init__(dialect)
        self.values = values
        self.column_values = column_values
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_set_literal"


class MariaDBFindInSetExpression(
    AliasableMixin,
    ComparisonMixin,
    SQLValueExpression,
):
    """MariaDB FIND_IN_SET function expression.

    Generates FIND_IN_SET(value, set_column) > 0 syntax.

    Example:
        >>> expr = MariaDBFindInSetExpression(dialect, 'read', 'permissions')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: str,
        set_column: str,
        *,
        alias: Optional[str] = None,
    ):
        """Initialize FIND_IN_SET expression.

        Args:
            dialect: SQL dialect
            value: Value to find
            set_column: SET column name
        """
        super().__init__(dialect)
        self.value = value
        self.set_column = set_column
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_find_in_set"


class MariaDBSetContainsExpression(
    AliasableMixin,
    ComparisonMixin,
    SQLValueExpression,
):
    """MariaDB SET contains check expression.

    Checks if all values are present in the SET column.

    Example:
        >>> expr = MariaDBSetContainsExpression(dialect, 'permissions', ['read', 'write'])
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column: str,
        values: List[str],
        *,
        alias: Optional[str] = None,
    ):
        """Initialize SET contains expression.

        Args:
            dialect: SQL dialect
            column: SET column name
            values: Values to check for
        """
        super().__init__(dialect)
        self.column = column
        self.values = values
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_set_contains"


__all__ = [
    "MariaDBSetLiteralExpression",
    "MariaDBFindInSetExpression",
    "MariaDBSetContainsExpression",
]
