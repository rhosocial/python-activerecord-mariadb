# src/rhosocial/activerecord/backend/impl/mariadb/protocols/set_operation.py
"""MariaDB INTERSECT/EXCEPT protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MariaDBIntersectExceptSupport(Protocol):
    """MariaDB INTERSECT/EXCEPT protocol.

    Feature Source: MariaDB 10.3+ (MySQL 8.0.31+ also supports)

    MariaDB INTERSECT/EXCEPT features:
    - INTERSECT: Return rows in both result sets
    - INTERSECT ALL: Include duplicates
    - EXCEPT: Return rows in first but not second
    - EXCEPT ALL: Include duplicates

    Official Documentation:
    - https://mariadb.com/kb/en/intersect/
    - https://mariadb.com/kb/en/except/

    Version Requirements:
    - MariaDB 10.3+ (native support)
    """

    def supports_intersect(self) -> bool:
        """Whether INTERSECT is supported.

        MariaDB 10.3+ supports INTERSECT.
        """
        ...

    def supports_except(self) -> bool:
        """Whether EXCEPT is supported.

        MariaDB 10.3+ supports EXCEPT.
        """
        ...

    def supports_intersect_all(self) -> bool:
        """Whether INTERSECT ALL is supported.

        MariaDB 10.3+ supports INTERSECT ALL.
        """
        ...

    def supports_except_all(self) -> bool:
        """Whether EXCEPT ALL is supported.

        MariaDB 10.3+ supports EXCEPT ALL.
        """
        ...
