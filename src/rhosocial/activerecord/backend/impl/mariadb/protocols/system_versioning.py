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

    def format_for_system_time_as_of(
        self,
        timestamp: Any
    ) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME AS OF clause.

        Named with the ``for_`` prefix because that is what
        :class:`~...mixins.system_versioning.MariaDBSystemVersioningMixin`
        implements and what its callers use. This protocol used to declare
        ``format_system_time_as_of`` instead: no mixin implemented that name, no
        expression dispatched to it, and because a protocol is satisfied by its
        own ellipsis bodies it answered the lookup with ``None`` -- a formatter
        that could not render anything, sitting in the dialect's base list
        waiting for an expression to name it.

        Args:
            timestamp: Point in time to query

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_for_system_time_between(
        self,
        start: Any,
        end: Any
    ) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME BETWEEN clause.

        Named to match the mixin, for the reason given on
        :meth:`format_for_system_time_as_of`.

        Args:
            start: Start timestamp
            end: End timestamp

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
