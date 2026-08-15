# src/rhosocial/activerecord/backend/impl/mariadb/mixins/system_versioning.py
"""MariaDB System-Versioned Tables mixin.

MariaDB 10.3+ supports system-versioned tables for temporal data tracking.
This is a MariaDB-specific feature not available in MySQL.
"""
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression import bases


class MariaDBSystemVersioningMixin:
    """MariaDB System-Versioned Tables support mixin.

    MariaDB 10.3+ supports system-versioned tables that automatically
    keep historical versions of rows.

    Features:
    - WITH SYSTEM VERSIONING: Create versioned table
    - FOR SYSTEM_TIME AS OF: Query historical data at a point in time
    - FOR SYSTEM_TIME BETWEEN: Query data between timestamps
    - FOR SYSTEM_TIME FROM...TO: Query data in a range
    - FOR SYSTEM_TIME ALL: Query all historical data
    - WITHOUT SYSTEM VERSIONING: Query current data only

    Official Documentation:
    - https://mariadb.com/kb/en/system-versioned-tables/

    Version Requirements:
    - MariaDB 10.3+

    Example:
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name VARCHAR(100)
        ) WITH SYSTEM VERSIONING;

        SELECT * FROM users FOR SYSTEM_TIME AS OF TIMESTAMP '2024-01-01 00:00:00';
    """

    def supports_system_versioning(self) -> bool:
        """Whether system-versioned tables are supported.

        MariaDB 10.3+ supports system-versioned tables.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['SYSTEM_VERSIONING']

    def supports_temporal_tables(self) -> bool:
        """Whether temporal tables are supported.

        This is an alias for supports_system_versioning() to match
        the generic protocol.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.supports_system_versioning()

    def format_system_versioning_clause(
        self,
        table_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, tuple]:
        """Format WITH SYSTEM VERSIONING clause for CREATE TABLE.

        Syntax:
            WITH SYSTEM VERSIONING
            [WITH SYSTEM VERSIONING ON {DELETE|UPDATE} {EQUAL|BEFORE}]

        Args:
            table_options: Optional dict with:
                - 'versioning_on_delete': 'EQUAL' or 'BEFORE'
                - 'versioning_on_update': 'EQUAL' or 'BEFORE'

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if not self.supports_system_versioning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "System-Versioned Tables",
                "System-versioned tables require MariaDB 10.3 or later."
            )

        parts = ["WITH SYSTEM VERSIONING"]

        if table_options:
            on_delete = table_options.get('versioning_on_delete')
            on_update = table_options.get('versioning_on_update')

            on_parts = []
            if on_delete:
                on_parts.append(f"ON DELETE {on_delete.upper()}")
            if on_update:
                on_parts.append(f"ON UPDATE {on_update.upper()}")

            if on_parts:
                parts.append("WITH SYSTEM VERSIONING " + " ".join(on_parts))

        return " ".join(parts), ()

    def format_for_system_time_as_of(
        self,
        timestamp: Any
    ) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME AS OF clause.

        Queries the table as it was at the specified timestamp.

        Args:
            timestamp: Point in time to query. Can be:
                - datetime object
                - timestamp string
                - expression

        Returns:
            Tuple of (SQL string, parameters tuple).

        Example:
            >>> dialect.format_for_system_time_as_of('2024-01-01 00:00:00')
            ("FOR SYSTEM_TIME AS OF '2024-01-01 00:00:00'", ())
        """
        if not self.supports_system_versioning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "FOR SYSTEM_TIME AS OF",
                "System-versioned tables require MariaDB 10.3 or later."
            )

        if hasattr(timestamp, 'to_sql'):
            ts_sql, ts_params = timestamp.to_sql()
            return f"FOR SYSTEM_TIME AS OF {ts_sql}", ts_params

        if hasattr(timestamp, 'isoformat'):
            timestamp = timestamp.isoformat()

        return f"FOR SYSTEM_TIME AS OF '{timestamp}'", ()

    def format_for_system_time_between(
        self,
        start: Any,
        end: Any
    ) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME BETWEEN clause.

        Queries rows that were visible at any point between two timestamps.

        Args:
            start: Start timestamp.
            end: End timestamp.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if not self.supports_system_versioning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "FOR SYSTEM_TIME BETWEEN",
                "System-versioned tables require MariaDB 10.3 or later."
            )

        all_params = []

        def format_ts(ts):
            if hasattr(ts, 'to_sql'):
                ts_sql, ts_params = ts.to_sql()
                all_params.extend(ts_params)
                return ts_sql
            if hasattr(ts, 'isoformat'):
                ts = ts.isoformat()
            return f"'{ts}'"

        start_sql = format_ts(start)
        end_sql = format_ts(end)

        return f"FOR SYSTEM_TIME BETWEEN {start_sql} AND {end_sql}", tuple(all_params)

    def format_for_system_time_from_to(
        self,
        start: Any,
        end: Any
    ) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME FROM...TO clause.

        Queries rows that were visible during a time range, but not at
        the exact boundaries.

        Args:
            start: Start timestamp (exclusive).
            end: End timestamp (exclusive).

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if not self.supports_system_versioning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "FOR SYSTEM_TIME FROM...TO",
                "System-versioned tables require MariaDB 10.3 or later."
            )

        all_params = []

        def format_ts(ts):
            if hasattr(ts, 'to_sql'):
                ts_sql, ts_params = ts.to_sql()
                all_params.extend(ts_params)
                return ts_sql
            if hasattr(ts, 'isoformat'):
                ts = ts.isoformat()
            return f"'{ts}'"

        start_sql = format_ts(start)
        end_sql = format_ts(end)

        return f"FOR SYSTEM_TIME FROM {start_sql} TO {end_sql}", tuple(all_params)

    def format_for_system_time_all(self) -> Tuple[str, tuple]:
        """Format FOR SYSTEM_TIME ALL clause.

        Queries all historical rows including current and deleted rows.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if not self.supports_system_versioning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "FOR SYSTEM_TIME ALL",
                "System-versioned tables require MariaDB 10.3 or later."
            )

        return "FOR SYSTEM_TIME ALL", ()

    def format_without_system_versioning(self) -> Tuple[str, tuple]:
        """Format WITHOUT SYSTEM VERSIONING clause.

        Queries only current data, excluding historical rows.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return "WITHOUT SYSTEM VERSIONING", ()


__all__ = ['MariaDBSystemVersioningMixin']
