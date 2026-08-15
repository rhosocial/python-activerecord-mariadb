# src/rhosocial/activerecord/backend/impl/mariadb/protocols/set_type.py
"""MariaDB SET type protocol."""

from typing import List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class MariaDBSetTypeSupport(Protocol):
    """MariaDB SET type protocol.

    Feature Source: MariaDB native (not SQL standard)

    MariaDB SET features:
    - String object with zero or more values from predefined list
    - Stored as integer (bit flags) internally
    - Maximum 64 members
    - Supports FIND_IN_SET, LIKE operations
    - Automatically sorted on storage

    Official Documentation:
    - SET Type: https://mariadb.com/kb/en/set-data-type/

    Version Requirements:
    - All MariaDB versions
    """

    def supports_set_type(self) -> bool:
        """Whether SET type is supported."""
        ...

    def format_set_literal(
        self,
        values: List[str],
        column_values: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format SET type literal.

        Args:
            values: Allowed values for the SET type
            column_values: Values being inserted/compared

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_find_in_set(
        self,
        value: str,
        set_column: str
    ) -> Tuple[str, tuple]:
        """Format FIND_IN_SET function call.

        Args:
            value: Value to search for
            set_column: SET column or expression to search in

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_set_contains(
        self,
        column: str,
        values: List[str]
    ) -> Tuple[str, tuple]:
        """Format SET contains check expression.

        Args:
            column: SET column name
            values: Values to check for containment

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
