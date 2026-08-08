# src/rhosocial/activerecord/backend/impl/mariadb/mixins/truncate.py
from typing import TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
        TruncateExpression,
    )


class MariaDBTruncateMixin:
    """MariaDB TRUNCATE TABLE support.

    MariaDB syntax is ``TRUNCATE [TABLE] tbl_name [WAIT n | NOWAIT]``.
    Unlike PostgreSQL, MariaDB does not support RESTART IDENTITY or
    CASCADE, and a successful TRUNCATE always resets AUTO_INCREMENT
    counters.

    ``WAIT n | NOWAIT`` sets the metadata lock wait timeout and is
    available since MariaDB 10.3.
    """

    def supports_truncate(self) -> bool:
        return True

    def supports_truncate_table_keyword(self) -> bool:
        return True

    def supports_truncate_restart_identity(self) -> bool:
        return False

    def supports_truncate_cascade(self) -> bool:
        return False

    def supports_truncate_wait(self) -> bool:
        """Whether WAIT n | NOWAIT lock wait option is supported.

        MariaDB 10.3+ allows setting a lock wait timeout on TRUNCATE.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['TRUNCATE_WAIT']

    def format_truncate_statement(self, expr: "TruncateExpression") -> Tuple[str, tuple]:
        """Format MariaDB ``TRUNCATE [TABLE] tbl_name [WAIT n | NOWAIT]``."""
        if expr.restart_identity:
            raise UnsupportedFeatureError(
                self.name,
                "TRUNCATE ... RESTART IDENTITY",
                suggestion="MariaDB TRUNCATE always resets AUTO_INCREMENT; drop the option.",
            )
        if expr.cascade:
            raise UnsupportedFeatureError(
                self.name,
                "TRUNCATE ... CASCADE",
                suggestion="MariaDB does not support CASCADE on TRUNCATE.",
            )

        sql = f"TRUNCATE TABLE {self.format_identifier(expr.table_name)}"

        options = expr.dialect_options
        wait = None
        if options.get("nowait"):
            wait = "NOWAIT"
        elif options.get("wait") is not None:
            wait = f"WAIT {int(options['wait'])}"
        if wait is not None:
            if not self.supports_truncate_wait():
                raise UnsupportedFeatureError(
                    self.name,
                    "TRUNCATE ... WAIT/NOWAIT",
                    suggestion="WAIT/NOWAIT lock wait timeout requires MariaDB 10.3 or later.",
                )
            sql += f" {wait}"
        return sql, ()