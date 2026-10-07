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
        """Whether ``TRUNCATE`` is supported.

        Measured True on all 19 configured servers (10.2.44 ... 13.1.1):
        ``TRUNCATE TABLE t`` and ``TRUNCATE t`` are both accepted everywhere;
        the sentinel ``TRUNCATE TABLE t BOGUS`` is rejected with errno 1064.
        Core's ``format_truncate_statement`` consults this probe and this
        override honours it too, so a subclass that flips the probe to False
        gets a refusal by name instead of rendered SQL.
        """
        return True

    def supports_truncate_table_keyword(self) -> bool:
        return True

    def supports_truncate_restart_identity(self) -> bool:
        """Whether ``RESTART IDENTITY`` / ``CONTINUE IDENTITY`` is supported.

        Measured False on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc: every version
        rejects ``TRUNCATE TABLE t RESTART IDENTITY`` and ``... CONTINUE
        IDENTITY`` with errno 1064, sentinel rejected. A successful MariaDB
        ``TRUNCATE`` always resets the counter, so there is no identity clause
        to request.
        """
        return False

    def supports_truncate_cascade(self) -> bool:
        """Whether ``CASCADE`` is supported.

        Measured False on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc: every version
        rejects ``TRUNCATE TABLE t CASCADE`` with errno 1064, sentinel
        rejected.
        """
        return False

    def supports_truncate_restrict(self) -> bool:
        """Whether ``RESTRICT`` is supported.

        Measured False on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc: every version
        rejects ``TRUNCATE TABLE t RESTRICT`` with errno 1064, sentinel
        rejected.
        """
        return False

    def supports_truncate_wait(self) -> bool:
        """Whether WAIT n | NOWAIT lock wait option is supported.

        MariaDB 10.3+ allows setting a lock wait timeout on TRUNCATE.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['TRUNCATE_WAIT']

    def format_truncate_statement(self, expr: "TruncateExpression") -> Tuple[str, tuple]:
        """Format MariaDB ``TRUNCATE [TABLE] tbl_name [WAIT n | NOWAIT]``.

        Each two-spelling modifier carries one parameter per spelling --
        ``restart_identity`` / ``continue_identity``, ``cascade`` /
        ``restrict`` -- and an unset pair renders nothing. The parameter
        selects the spelling; the modifier's probe answers whether MariaDB
        accepts it at all, and an explicit spelling whose probe is False is
        refused by name rather than dropped. All four spellings are measured
        rejected (see the probes above), so both pairs refuse; a subclass that
        declares a probe True renders the spelling it declared.

        Raises:
            TypeError: ``expr.table`` is not a Table.
            UnsupportedFeatureError: If the dialect does not support the
                requested identity or dependent-table behavior.
        """
        from rhosocial.activerecord.backend.expression.objects import Table

        if not isinstance(expr.table, Table):
            raise TypeError(
                f"TruncateExpression.table must be a Table, "
                f"got {type(expr.table).__name__}"
            )
        if not self.supports_truncate():
            raise UnsupportedFeatureError(
                self.name,
                "TRUNCATE",
                f"{self.name} does not support TRUNCATE.",
            )
        identity = ""
        if expr.restart_identity or expr.continue_identity:
            if not self.supports_truncate_restart_identity():
                raise UnsupportedFeatureError(
                    self.name,
                    "TRUNCATE RESTART IDENTITY"
                    if expr.restart_identity
                    else "TRUNCATE CONTINUE IDENTITY",
                    suggestion="MariaDB TRUNCATE always resets AUTO_INCREMENT; drop the option.",
                )
            identity = (
                " RESTART IDENTITY" if expr.restart_identity else " CONTINUE IDENTITY"
            )
        behavior = ""
        if expr.cascade or expr.restrict:
            if expr.cascade and not self.supports_truncate_cascade():
                raise UnsupportedFeatureError(
                    self.name,
                    "TRUNCATE CASCADE",
                    suggestion="MariaDB does not support CASCADE on TRUNCATE.",
                )
            if expr.restrict and not self.supports_truncate_restrict():
                raise UnsupportedFeatureError(
                    self.name,
                    "TRUNCATE RESTRICT",
                    suggestion="MariaDB does not support RESTRICT on TRUNCATE.",
                )
            behavior = " CASCADE" if expr.cascade else " RESTRICT"

        # TRUNCATE can address a table in another database, and that database is
        # a catalog slot on the object the statement holds rather than a
        # hand-built `db`.`tbl` string.
        table_sql, _ = expr.table.to_sql()
        sql = f"TRUNCATE TABLE {table_sql}{identity}{behavior}"

        wait = None
        if getattr(expr, "nowait", False):
            wait = "NOWAIT"
        elif getattr(expr, "wait", None) is not None:
            wait = f"WAIT {int(expr.wait)}"
        if wait is not None:
            if not self.supports_truncate_wait():
                raise UnsupportedFeatureError(
                    self.name,
                    "TRUNCATE ... WAIT/NOWAIT",
                    suggestion="WAIT/NOWAIT lock wait timeout requires MariaDB 10.3 or later.",
                )
            sql += f" {wait}"
        return sql, ()