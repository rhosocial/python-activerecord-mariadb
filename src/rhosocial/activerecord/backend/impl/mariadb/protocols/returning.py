# src/rhosocial/activerecord/backend/impl/mariadb/protocols/returning.py
"""MariaDB RETURNING clause protocol."""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class MariaDBReturningSupport(Protocol):
    """MariaDB RETURNING clause protocol.

    Feature Source: MariaDB 10.5+ (not available in MySQL)

    MariaDB RETURNING features:
    - RETURNING *: Return all columns
    - RETURNING col1, col2: Return specific columns
    - RETURNING expr AS alias: Return expressions with aliases

    Official Documentation:
    - https://mariadb.com/kb/en/insert-on-duplicate/

    Version Requirements:
    - MariaDB 10.5.0+
    """

    def supports_returning(self) -> bool:
        """Whether RETURNING clause is supported.

        MariaDB 10.5+ supports RETURNING for INSERT, DELETE, REPLACE.
        """
        ...

    def supports_returning_expression(self) -> bool:
        """Whether expressions are supported in RETURNING.

        MariaDB 10.5+ supports expressions and aliases in RETURNING.
        """
        ...

    def format_returning_clause(
        self,
        columns: Optional[List[str]] = None,
        expressions: Optional[List[Dict[str, Any]]] = None,
        aliases: Optional[Dict[str, str]] = None
    ) -> Tuple[str, tuple]:
        """Format RETURNING clause for MariaDB.

        Args:
            columns: Column names to return
            expressions: Expressions with optional aliases
            aliases: Column/expression to alias mappings

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
