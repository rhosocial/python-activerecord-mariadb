# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl/alter_table.py
"""MariaDB ALTER TABLE statement-level qualifiers and index rename.

MariaDB 10.5+ supports statement-level ``ALTER TABLE IF EXISTS`` so that a
missing table does not raise an error, and ``ALTER TABLE ... WAIT n |
NOWAIT`` to set the metadata lock wait timeout (10.3+).

MariaDB 10.5.3+ supports renaming an index with ``ALTER TABLE
tbl_name RENAME INDEX old_index_name TO new_index_name``.
"""

from typing import Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from ..backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
        AlterTableExpression,
    )
    from rhosocial.activerecord.backend.impl.mariadb.expression.rename_index import (
        MariaDBRenameIndexExpression,
    )


class MariaDBAlterTableMixin:
    """MariaDB ALTER TABLE statement-level options.

    MariaDB-specific extensions over the generic ALTER TABLE form:
    - Statement-level ``IF EXISTS`` (MariaDB 10.5+)
    - ``WAIT n | NOWAIT`` lock wait timeout (MariaDB 10.3+)
    - ``RENAME INDEX`` (MariaDB 10.5.3+)
    """

    def supports_alter_table_if_exists(self) -> bool:
        """Whether statement-level ALTER TABLE IF EXISTS is supported.

        MariaDB 10.5+ supports ``ALTER TABLE IF EXISTS tbl_name ...`` so a
        missing table does not raise an error.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RENAME_TABLE_IF_EXISTS']

    def supports_alter_table_wait(self) -> bool:
        """Whether ALTER TABLE WAIT n | NOWAIT is supported.

        MariaDB 10.3+ allows setting a metadata lock wait timeout.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RENAME_TABLE_WAIT']

    def supports_rename_index(self) -> bool:
        """Whether ALTER TABLE ... RENAME INDEX is supported.

        MariaDB 10.5.3+ supports renaming an index via ALTER TABLE.

        Returns:
            True if MariaDB version >= 10.5.3.
        """
        return self.version >= (10, 5, 3)

    def format_alter_table_statement(
        self, expr: "AlterTableExpression"
    ) -> Tuple[str, tuple]:
        """Format a MariaDB ``ALTER TABLE ...`` statement.

        Injects the MariaDB-specific statement-level qualifiers ``IF EXISTS``
        (10.5+) and ``WAIT n | NOWAIT`` (10.3+) based on ``dialect_options``,
        then falls back to the generic action rendering.
        """
        options = expr.dialect_options

        head = "ALTER TABLE"
        if options.get("if_exists"):
            if not self.supports_alter_table_if_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER TABLE IF EXISTS",
                    "Statement-level IF EXISTS requires MariaDB 10.5 or later."
                )
            head += " IF EXISTS"

        table_part = f"{head} {self.format_identifier(expr.table)}"

        if options.get("nowait"):
            wait = "NOWAIT"
        elif options.get("wait") is not None:
            wait = f"WAIT {int(options['wait'])}"
        else:
            wait = None
        if wait is not None:
            if not self.supports_alter_table_wait():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER TABLE WAIT/NOWAIT",
                    "WAIT/NOWAIT lock wait timeout requires MariaDB 10.3 or later."
                )
            table_part += f" {wait}"

        all_params = []
        parts = [table_part]
        action_parts = []
        for action in expr.actions:
            action_part, action_params = action.to_sql()
            action_parts.append(action_part)
            all_params.extend(action_params)
        if action_parts:
            parts.append(" " + ", ".join(action_parts))
        return " ".join(parts), tuple(all_params)

    def format_rename_index_statement(
        self,
        expr: "MariaDBRenameIndexExpression",
    ) -> Tuple[str, tuple]:
        """Format MariaDB ``ALTER TABLE ... RENAME INDEX``."""
        expr.validate(strict=self.strict_validation)

        if not self.supports_rename_index():
            raise UnsupportedFeatureError(
                self.name,
                "RENAME INDEX",
                "ALTER TABLE ... RENAME INDEX requires MariaDB 10.5.3 or later."
            )

        return (
            "ALTER TABLE "
            f"{self.format_identifier(expr.table)} RENAME INDEX "
            f"{self.format_identifier(expr.old_index_name)} TO "
            f"{self.format_identifier(expr.new_index_name)}",
            ()
        )