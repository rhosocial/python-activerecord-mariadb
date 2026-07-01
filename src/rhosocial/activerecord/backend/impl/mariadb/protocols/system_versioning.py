# src/rhosocial/activerecord/backend/impl/mariadb/protocols/system_versioning.py
"""MariaDB System-Versioned Tables protocol."""

from typing import Any, Protocol, Tuple, runtime_checkable


@runtime_checkable
class MariaDBSystemVersioningSupport(Protocol):
    """MariaDB System-Versioned Tables protocol.

    Feature Source: MariaDB 10.3+ (not available in MySQL)

    MariaDB System-Versioning features:
    - FOR SYSTEM_TIME AS OF: Query historical data
    - FOR SYSTEM_TIME BETWEEN: Query data between timestamps
    - FOR SYSTEM_TIME FROM...TO: Query data in range
    - WITH SYSTEM VERSIONING: Create versioned table
    - WITHOUT SYSTEM VERSIONING: Disable versioning

    Official Documentation:
    - https://mariadb.com/kb/en/system-versioned-tables/

    Version Requirements:
    - MariaDB 10.3+
    """

    def supports_system_versioning(self) -> bool:
        """Whether system-versioned tables are supported.

        MariaDB 10.3+ supports system-versioned tables.
        """
        ...

    def format_system_time_as_of(
        self,
        timestamp: Any
    ) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME AS OF clause.

        Args:
            timestamp: Point in time to query

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_system_time_between(
        self,
        start: Any,
        end: Any
    ) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME BETWEEN clause.

        Args:
            start: Start timestamp
            end: End timestamp

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
