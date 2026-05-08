# src/rhosocial/activerecord/backend/impl/mariadb/mixins/set_type.py
"""MariaDB SET type mixin.

MariaDB SET type features:
- String object with zero or more values from predefined list
- Stored as integer (bit flags) internally
- Maximum 64 members
- Supports FIND_IN_SET, LIKE operations
- Automatically sorted on storage
"""
from typing import List, Optional, Tuple


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
        values: List[str],
        column_values: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format SET literal value.

        Args:
            values: Values to include in the SET
            column_values: Allowed values for the column (for validation)

        Returns:
            Tuple of (SQL string, parameters tuple)

        Raises:
            ValueError: If values exceed 64 members or contain invalid values
        """
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
            return "'", ()

        sorted_values = sorted(values)
        literal = ','.join(sorted_values)
        return "%s", (literal,)

    def format_find_in_set(
        self,
        value: str,
        set_column: str
    ) -> Tuple[str, tuple]:
        """Format FIND_IN_SET function.

        Args:
            value: Value to find
            set_column: SET column name

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return f"FIND_IN_SET(%s, {self.format_identifier(set_column)}) > 0", (value,)

    def format_set_contains(
        self,
        column: str,
        values: List[str]
    ) -> Tuple[str, tuple]:
        """Format SET contains check.

        Checks if all values are present in the SET column.

        Args:
            column: SET column name
            values: Values to check for

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        conditions = []
        params: List[str] = []

        for value in values:
            conditions.append(f"FIND_IN_SET(%s, {self.format_identifier(column)}) > 0")
            params.append(value)

        return " AND ".join(conditions), tuple(params)


__all__ = ['MariaDBSetTypeMixin']