# src/rhosocial/activerecord/backend/impl/mariadb/protocols/returning.py
"""MariaDB RETURNING clause protocol."""

from typing import Protocol, runtime_checkable


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

