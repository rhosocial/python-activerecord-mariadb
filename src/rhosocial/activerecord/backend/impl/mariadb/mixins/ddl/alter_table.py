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
        AlterTableStatement,
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
        self, expr: "AlterTableStatement"
    ) -> Tuple[str, tuple]:
        """Format a MariaDB ``ALTER TABLE ...`` statement.

        Injects the MariaDB-specific statement-level qualifiers ``IF EXISTS``
        (10.5+) and ``WAIT n | NOWAIT`` (10.3+) from the typed fields of
        ``MariaDBAlterTableExpression``, then falls back to the generic action
        rendering.

        Raises:
            TypeError: ``expr.table`` is not a Table, or an entry of
                ``expr.actions`` is not an AlterTableAction. A view or an index
                would otherwise be named as if it were the table being altered.
        """
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
            AlterTableAction,
        )
        from rhosocial.activerecord.backend.impl.mariadb.expression.alter_table import (
            MariaDBAlterTableExpression,
        )

        if not isinstance(expr.table, Table):
            raise TypeError(
                f"AlterTableStatement.table must be a Table, "
                f"got {type(expr.table).__name__}"
            )
        head = "ALTER TABLE"
        # The MariaDB-only qualifiers (``if_exists``, ``wait``, ``nowait``)
        # belong to the MariaDB node's contract: the core statement declares
        # none of them, so which fields exist is a question about the class
        # and is answered with isinstance rather than probed off the instance.
        if isinstance(expr, MariaDBAlterTableExpression):
            if expr.if_exists:
                if not self.supports_alter_table_if_exists():
                    raise UnsupportedFeatureError(
                        self.name,
                        "ALTER TABLE IF EXISTS",
                        "Statement-level IF EXISTS requires MariaDB 10.5 or later."
                    )
                head += " IF EXISTS"

        # The statement holds the table as a schema object, so a caller that knows
        # the database can say so and the namespace survives into the SQL
        # instead of being retyped as a bare name.
        table_sql, _ = expr.table.to_sql()
        table_part = f"{head} {table_sql}"

        wait = None
        if isinstance(expr, MariaDBAlterTableExpression):
            if expr.nowait:
                wait = "NOWAIT"
            elif expr.wait is not None:
                wait = f"WAIT {int(expr.wait)}"
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
        # AlterTableAction is an abstract base and cannot be instantiated, so
        # this reports that the entry is not an implementation of it rather
        # than naming a concrete type. Checked here because the loop below
        # calls `action.to_sql()` directly, and a non-action carrying the
        # wrong `format_method` would render as valid SQL.
        for position, action in enumerate(expr.actions):
            if not isinstance(action, AlterTableAction):
                raise TypeError(
                    f"AlterTableStatement.actions must hold AlterTableAction implementations, "
                    f"got {type(action).__name__} at position {position}"
                )
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
        """Format MariaDB ``ALTER TABLE ... RENAME INDEX``.

        Raises:
            TypeError: One of the three objects is the wrong kind. Each carries
                its own ``format_method``, so a table passed where an index
                belongs would render as valid SQL naming the table.
        """
        from rhosocial.activerecord.backend.expression.objects import Index, Table

        # Three schema objects, each with its own ``format_*_object``: the
        # table it lives on, and the index before and after its rename. The
        # slots are the node's declared fields, so they are read by name
        # rather than probed for.
        for name, value, kind in (
            ("table", expr.table, Table),
            ("old_index", expr.old_index, Index),
            ("new_index", expr.new_index, Index),
        ):
            if not isinstance(value, kind):
                raise TypeError(
                    f"MariaDBRenameIndexExpression.{name} must be a "
                    f"{kind.__name__}, got {type(value).__name__}"
                )
        expr.validate(strict=self.strict_validation)

        if not self.supports_rename_index():
            raise UnsupportedFeatureError(
                self.name,
                "RENAME INDEX",
                "ALTER TABLE ... RENAME INDEX requires MariaDB 10.5.3 or later."
            )

        # Three schema objects, each rendered by its own `format_*_object`:
        # the table it lives on, and the index before and after its rename.
        table_sql, _ = expr.table.to_sql()
        old_sql, _ = expr.old_index.to_sql()
        new_sql, _ = expr.new_index.to_sql()
        return (
            f"ALTER TABLE {table_sql} RENAME INDEX {old_sql} TO {new_sql}",
            ()
        )