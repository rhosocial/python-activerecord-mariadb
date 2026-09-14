# src/rhosocial/activerecord/backend/impl/mariadb/mixins/set_type.py
"""MariaDB SET type mixin.

MariaDB SET type features:
- String object with zero or more values from predefined list
- Stored as integer (bit flags) internally
- Maximum 64 members
- Supports FIND_IN_SET, LIKE operations
- Automatically sorted on storage
"""
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.impl.mariadb.expression.set_type import (
        MariaDBSetLiteralExpression,
        MariaDBFindInSetExpression,
        MariaDBSetContainsExpression,
    )


class MariaDBSetTypeMixin:
    """MariaDB SET type implementation.

    MariaDB SET type features:
    - String object with zero or more values from predefined list
    - Stored as integer (bit flags) internally
    - Maximum 64 members
    - Supports FIND_IN_SET, LIKE operations
    - Automatically sorted on storage

    Version Requirements:
    - All MariaDB versions
    """

    def supports_set_type(self) -> bool:
        """MariaDB supports SET type in all versions."""
        return True

    def format_set_literal(
        self,
        expr: "MariaDBSetLiteralExpression",
    ) -> Tuple[str, tuple]:
        """Format a :class:`MariaDBSetLiteralExpression` node."""
        values = expr.values
        column_values = expr.column_values

        if len(values) > 64:
            raise ValueError("MariaDB SET type supports maximum 64 members")

        if column_values is not None:
            invalid_values = [v for v in values if v not in column_values]
            if invalid_values:
                raise ValueError(
                    f"Invalid SET values: {invalid_values}. "
                    f"Allowed values: {column_values}"
                )

        if not values:
            sql = "'"
            if expr.alias:
                sql = f"{sql} AS {self.format_identifier(expr.alias)}"
            return sql, ()

        sorted_values = sorted(values)
        literal = ','.join(sorted_values)
        sql = "%s"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, (literal,)

    def format_find_in_set(
        self,
        expr: "MariaDBFindInSetExpression",
    ) -> Tuple[str, tuple]:
        """Format a :class:`MariaDBFindInSetExpression` node."""
        sql = f"FIND_IN_SET(%s, {self.format_identifier(expr.set_column)}) > 0"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, (expr.value,)

    def format_set_contains(
        self,
        expr: "MariaDBSetContainsExpression",
    ) -> Tuple[str, tuple]:
        """Format a :class:`MariaDBSetContainsExpression` node."""
        conditions = []
        params: List[str] = []

        for value in expr.values:
            conditions.append(f"FIND_IN_SET(%s, {self.format_identifier(expr.column)}) > 0")
            params.append(value)

        sql = " AND ".join(conditions)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(params)


__all__ = ['MariaDBSetTypeMixin']