# src/rhosocial/activerecord/backend/impl/mariadb/expression/maintenance.py
"""MariaDB table maintenance statement expressions.

MariaDB supports the standard table maintenance statements:

    ANALYZE [NO_WRITE_TO_BINLOG | LOCAL] TABLE tbl_name [, tbl_name] ...
        [PERSISTENT FOR { ALL | COLUMNS ... | INDEXES ... }]

    CHECK TABLE tbl_name [, tbl_name] ...
        [FOR UPGRADE] [QUICK] [FAST] [MEDIUM] [EXTENDED] [CHANGED]

    CHECKSUM TABLE tbl_name [, tbl_name] ... [QUICK | EXTENDED]

    OPTIMIZE [NO_WRITE_TO_BINLOG | LOCAL] TABLE tbl_name [, tbl_name] ...

    REPAIR [NO_WRITE_TO_BINLOG | LOCAL] TABLE tbl_name [, tbl_name] ...
        [QUICK] [EXTENDED] [USE_FRM]
"""

from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class TableMaintenanceOperation(Enum):
    """Table maintenance operation for MariaDB."""

    ANALYZE = "ANALYZE"
    CHECK = "CHECK"
    CHECKSUM = "CHECKSUM"
    OPTIMIZE = "OPTIMIZE"
    REPAIR = "REPAIR"


class MariaDBTableMaintenanceExpression(BaseExpression):
    """Represent a MariaDB table maintenance statement.

    Attributes:
        operation: The maintenance operation to run.
        tables: Tables the operation targets.
        dialect_options: MariaDB-specific options:
            - 'no_write_to_binlog': Suppress binary logging (ANALYZE, OPTIMIZE,
              REPAIR). When True renders NO_WRITE_TO_BINLOG.
            - 'local': Synonym for NO_WRITE_TO_BINLOG.
            - 'persistent': Persistent statistics: 'all' | 'columns' | 'indexes'
              (ANALYZE only)
            - 'check_mode': CHECK flags, a list among FOR UPGRADE, QUICK, FAST,
              MEDIUM, EXTENDED, CHANGED.
            - 'checksum_mode': CHECKSUM mode, 'quick' or 'extended'.
            - 'repair_mode': REPAIR flags to append ('QUICK'/'EXTENDED'/'USE_FRM').
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        operation: "TableMaintenanceOperation",
        tables: List[str],
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.operation = operation
        self.tables: List[str] = list(tables)
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        """Validate the operation and table name list."""
        if not strict:
            return
        if not isinstance(self.operation, TableMaintenanceOperation):
            raise TypeError("operation must be a TableMaintenanceOperation")
        if not self.tables:
            raise ValueError("Table maintenance requires at least one table name")
        for name in self.tables:
            if not isinstance(name, str):
                raise TypeError("Table names must be strings")

    def to_sql(self):
        """Generate SQL by delegating to the dialect."""
        return self.dialect.format_table_maintenance_statement(self)