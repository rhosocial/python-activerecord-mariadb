# src/rhosocial/activerecord/backend/impl/mariadb/protocols/cte.py
"""MariaDB Common Table Expression (CTE) protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MariaDBCTESupport(Protocol):
    """MariaDB Common Table Expression (CTE) protocol.

    Feature Source: MariaDB 10.2+ (MySQL 8.0+)

    MariaDB CTE features:
    - WITH clause: Define CTEs
    - Recursive CTEs: WITH RECURSIVE
    - Multiple CTEs: Comma-separated

    Official Documentation:
    - https://mariadb.com/kb/en/common-table-expressions/

    Version Requirements:
    - MariaDB 10.2+
    """

    def supports_cte(self) -> bool:
        """Whether CTEs (WITH clause) are supported.

        MariaDB 10.2+ supports CTEs.
        """
        ...

    def supports_recursive_cte(self) -> bool:
        """Whether recursive CTEs are supported.

        MariaDB 10.2+ supports recursive CTEs.
        """
        ...
