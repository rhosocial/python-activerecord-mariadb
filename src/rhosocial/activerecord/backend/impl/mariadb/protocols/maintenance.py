# src/rhosocial/activerecord/backend/impl/mariadb/protocols/maintenance.py
"""MariaDB table maintenance protocol."""

from typing import TYPE_CHECKING, Protocol, Tuple, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mariadb.expression.maintenance import (
        MariaDBTableMaintenanceExpression,
    )


@runtime_checkable
class MariaDBMaintenanceSupport(Protocol):
    """MariaDB table maintenance support protocol.

    Feature Source: Native support (all versions)

    MariaDB supports ANALYZE, CHECK, CHECKSUM, OPTIMIZE and REPAIR TABLE
    statements, with MariaDB-specific extensions such as ANALYZE TABLE ...
    PERSISTENT FOR (MariaDB 10.5+).

    Official Documentation:
    - ANALYZE TABLE: https://mariadb.com/kb/en/analyze-table/
    - CHECK TABLE: https://mariadb.com/kb/en/check-table/
    - CHECKSUM TABLE: https://mariadb.com/kb/en/checksum-table/
    - OPTIMIZE TABLE: https://mariadb.com/kb/en/optimize-table/
    - REPAIR TABLE: https://mariadb.com/kb/en/repair-table/
    """

    def supports_analyze_table(self) -> bool:
        """Whether ANALYZE TABLE is supported."""
        ...

    def supports_check_table(self) -> bool:
        """Whether CHECK TABLE is supported."""
        ...

    def supports_checksum_table(self) -> bool:
        """Whether CHECKSUM TABLE is supported."""
        ...

    def supports_optimize_table(self) -> bool:
        """Whether OPTIMIZE TABLE is supported."""
        ...

    def supports_repair_table(self) -> bool:
        """Whether REPAIR TABLE is supported."""
        ...

    def supports_analyze_table_persistent(self) -> bool:
        """Whether ANALYZE TABLE ... PERSISTENT FOR is supported (10.5+)."""
        ...

    def format_table_maintenance_statement(
        self,
        expr: "MariaDBTableMaintenanceExpression",
    ) -> Tuple[str, tuple]:
        """Format a MariaDB table maintenance statement.

        dialect_options:
            - 'no_write_to_binlog' / 'local': Render NO_WRITE_TO_BINLOG
            - 'persistent': 'all' or {'columns': [...], 'indexes': [...]}
              (ANALYZE only, MariaDB 10.5+)
            - 'check_mode': e.g. ['QUICK', 'EXTENDED'] (CHECK)
            - 'checksum_mode': 'QUICK' | 'EXTENDED' (CHECKSUM)
            - 'repair_mode': e.g. ['QUICK'] (REPAIR)
        """
        ...