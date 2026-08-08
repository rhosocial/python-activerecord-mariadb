# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl/maintenance.py
"""MariaDB table maintenance statement mixin.

MariaDB supports the standard table maintenance statements ANALYZE, CHECK,
CHECKSUM, OPTIMIZE and REPAIR TABLE, with MariaDB-specific extensions such as
ANALYZE TABLE ... PERSISTENT FOR persistent statistics.
"""
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mariadb.expression.maintenance import (
        MariaDBTableMaintenanceExpression,
    )


class MariaDBMaintenanceMixin:
    """MariaDB table maintenance statement support.

    MariaDB syntax:

        ANALYZE [NO_WRITE_TO_BINLOG | LOCAL] TABLE tbl [, tbl] ...
            [PERSISTENT FOR { ALL | COLUMNS ... | INDEXES ... }]
        CHECK TABLE tbl [, tbl] ...
            [FOR UPGRADE] [QUICK] [FAST] [MEDIUM] [EXTENDED] [CHANGED]
        CHECKSUM TABLE tbl [, tbl] ... [QUICK | EXTENDED]
        OPTIMIZE [NO_WRITE_TO_BINLOG | LOCAL] TABLE tbl [, tbl] ...
        REPAIR [NO_WRITE_TO_BINLOG | LOCAL] TABLE tbl [, tbl] ...
            [QUICK] [EXTENDED] [USE_FRM]
    """

    def supports_analyze_table(self) -> bool:
        return True

    def supports_check_table(self) -> bool:
        return True

    def supports_checksum_table(self) -> bool:
        return True

    def supports_optimize_table(self) -> bool:
        return True

    def supports_repair_table(self) -> bool:
        return True

    def supports_analyze_table_persistent(self) -> bool:
        """Whether ANALYZE TABLE ... PERSISTENT FOR is supported.

        MariaDB 10.5+ supports engine-independent persistent statistics.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= (10, 5, 0)

    def format_table_maintenance_statement(
        self,
        expr: "MariaDBTableMaintenanceExpression",
    ) -> Tuple[str, tuple]:
        """Format a MariaDB table maintenance statement."""
        expr.validate(strict=self.strict_validation)

        options = expr.dialect_options
        operation = expr.operation.value
        tables = ", ".join(self.format_identifier(t) for t in expr.table_names)

        parts = [operation]

        if options.get("no_write_to_binlog") or options.get("local"):
            parts.append("NO_WRITE_TO_BINLOG")

        parts.append("TABLE")
        parts.append(tables)

        if operation == "ANALYZE":
            persistent = options.get("persistent")
            if persistent is not None:
                if not self.supports_analyze_table_persistent():
                    raise self._unsupported(
                        "ANALYZE TABLE ... PERSISTENT FOR",
                        "Persistent statistics require MariaDB 10.5 or later.",
                    )
                target = self._persistent_target(persistent)
                parts.append(f"PERSISTENT FOR {target}")
        elif operation == "CHECK":
            for mode in options.get("check_mode", ()):
                parts.append(mode)
        elif operation == "CHECKSUM":
            mode = options.get("checksum_mode")
            if mode is not None:
                parts.append(str(mode).upper())
        elif operation == "REPAIR":
            for mode in options.get("repair_mode", ()):
                parts.append(mode)

        return " ".join(parts), ()

    def _unsupported(self, feature: str, suggestion: str):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        return UnsupportedFeatureError(self.name, feature, suggestion)

    def _persistent_target(self, persistent) -> str:
        """Render the PERSISTENT FOR target clause."""
        if persistent is True or persistent == "all":
            return "ALL"
        if isinstance(persistent, dict):
            target = []
            if "columns" in persistent:
                cols = ", ".join(
                    self.format_identifier(c) for c in persistent["columns"]
                )
                target.append(f"COLUMNS ({cols})")
            if "indexes" in persistent:
                idx = ", ".join(
                    self.format_identifier(i) for i in persistent["indexes"]
                )
                target.append(f"INDEXES ({idx})")
            if not target:
                raise ValueError("persistent dict must contain 'columns' or 'indexes'")
            return " ".join(target)
        raise ValueError(
            "persistent must be True/'all' or a dict with 'columns'/'indexes'"
        )