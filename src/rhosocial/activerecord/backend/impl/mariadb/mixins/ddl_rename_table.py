# src/rhosocial/activerecord/backend/impl/mariadb/mixins/rename_table.py
"""MariaDB RENAME TABLE mixin.

MariaDB supports atomic multi-table renames with extensions over the
MySQL form:

    RENAME TABLE[S] [IF EXISTS] tbl_name [WAIT n | NOWAIT]
      TO new_tbl_name [, tbl_name2 TO new_tbl_name2] ...
"""
from typing import Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mariadb.expression.rename_table import (
        MariaDBRenameTableExpression,
    )


class MariaDBRenameTableMixin:
    """MariaDB RENAME TABLE support.

    MariaDB supports atomic multi-table renames:

        RENAME TABLE t1 TO t2 [, t3 TO t4, ...]

    MariaDB-specific extensions:
    - ``TABLE`` or ``TABLES`` keyword (no semantic difference)
    - Statement-level ``IF EXISTS`` (MariaDB 10.5+)
    - ``WAIT n | NOWAIT`` lock wait timeout (MariaDB 10.3+)
    """

    def supports_rename_table(self) -> bool:
        return True

    def supports_multi_table_rename(self) -> bool:
        return True

    def supports_rename_table_if_exists(self) -> bool:
        """Whether statement-level IF EXISTS is supported.

        MariaDB 10.5+ supports ``RENAME TABLE IF EXISTS`` so that a
        missing source table does not raise an error.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RENAME_TABLE_IF_EXISTS']

    def supports_rename_table_wait(self) -> bool:
        """Whether WAIT n | NOWAIT lock wait option is supported.

        MariaDB 10.3+ allows setting a lock wait timeout per statement.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RENAME_TABLE_WAIT']

    def format_rename_table_statement(
        self,
        expr: "MariaDBRenameTableExpression",
    ) -> Tuple[str, tuple]:
        """Format a MariaDB ``RENAME TABLE ...`` statement."""
        expr.validate(strict=self.strict_validation)

        options = expr.dialect_options

        if options.get('if_exists'):
            if not self.supports_rename_table_if_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "RENAME TABLE IF EXISTS",
                    "Statement-level IF EXISTS requires MariaDB 10.5 or later."
                )
            head = "RENAME TABLE IF EXISTS"
        else:
            head = "RENAME TABLE"

        wait = None
        if options.get("nowait"):
            wait = "NOWAIT"
        elif options.get("wait") is not None:
            wait = f"WAIT {int(options['wait'])}"
        if wait is not None and not self.supports_rename_table_wait():
            raise UnsupportedFeatureError(
                self.name,
                "RENAME TABLE WAIT/NOWAIT",
                "WAIT/NOWAIT lock wait timeout requires MariaDB 10.3 or later."
            )

        pairs = []
        for old_name, new_name in expr.renames:
            pair = f"{self.format_identifier(old_name)} TO {self.format_identifier(new_name)}"
            pairs.append(pair)

        if wait is not None:
            first_old, first_new = pairs[0].split(" TO ", 1)
            pairs[0] = f"{first_old} {wait} TO {first_new}"

        parts = [head]
        parts.append(", ".join(pairs))
        return " ".join(parts), ()