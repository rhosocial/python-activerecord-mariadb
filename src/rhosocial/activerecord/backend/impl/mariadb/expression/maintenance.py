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
from typing import List, Optional, TYPE_CHECKING

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
        table_names: Tables the operation targets.
        no_write_to_binlog: Suppress binary logging (ANALYZE, OPTIMIZE,
            REPAIR). When True renders NO_WRITE_TO_BINLOG.
        local: Synonym for ``no_write_to_binlog``.
        persistent: Persistent statistics: ``'all'`` | a dict with
            ``columns``/``indexes`` (ANALYZE only).
        check_mode: CHECK flags, a list among ``FOR UPGRADE``, ``QUICK``,
            ``FAST``, ``MEDIUM``, ``EXTENDED``, ``CHANGED``.
        checksum_mode: CHECKSUM mode, ``'quick'`` or ``'extended'``.
        repair_mode: REPAIR flags to append (``'QUICK'``/``'EXTENDED'``/
            ``'USE_FRM'``).
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        operation: "TableMaintenanceOperation",
        table_names: List[str],
        *,
        no_write_to_binlog: bool = False,
        local: bool = False,
        persistent=None,
        check_mode: Optional[List[str]] = None,
        checksum_mode: Optional[str] = None,
        repair_mode: Optional[List[str]] = None,
    ):
        super().__init__(dialect)
        self.operation = operation
        self.table_names: List[str] = list(table_names)
        self.no_write_to_binlog = no_write_to_binlog
        self.local = local
        self.persistent = persistent
        self.check_mode = check_mode
        self.checksum_mode = checksum_mode
        self.repair_mode = repair_mode

    def validate(self, strict: bool = True) -> None:
        """Validate the operation and table name list."""
        if not strict:
            return
        if not isinstance(self.operation, TableMaintenanceOperation):
            raise TypeError("operation must be a TableMaintenanceOperation")
        if not self.table_names:
            raise ValueError("Table maintenance requires at least one table name")
        for name in self.table_names:
            if not isinstance(name, str):
                raise TypeError("Table names must be strings")

    def to_sql(self):
        """Generate SQL by delegating to the dialect."""
        return self.dialect.format_table_maintenance_statement(self)