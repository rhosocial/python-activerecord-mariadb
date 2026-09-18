# src/rhosocial/activerecord/backend/impl/mariadb/protocols/set_type.py
"""MariaDB SET type protocol."""

from typing import Any, Protocol, Tuple, runtime_checkable


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
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format a SET literal expression.

        Args:
            expr: MariaDBSetLiteralExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_find_in_set(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format a FIND_IN_SET expression.

        Args:
            expr: MariaDBFindInSetExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_set_contains(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format a SET contains check expression.

        Args:
            expr: MariaDBSetContainsExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
