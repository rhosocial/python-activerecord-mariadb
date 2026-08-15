# src/rhosocial/activerecord/backend/impl/mariadb/protocols/alter_table.py
"""MariaDB ALTER TABLE statement-level protocol."""

from typing import TYPE_CHECKING, Protocol, Tuple, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mariadb.expression.rename_index import (
        MariaDBRenameIndexExpression,
    )


@runtime_checkable
class MariaDBAlterTableSupport(Protocol):
    """MariaDB ALTER TABLE statement-level support protocol.

    Feature Source: Native support (version-dependent)

    MariaDB extends the ALTER TABLE header with:
    - Statement-level ``IF EXISTS`` (MariaDB 10.5+): no error if the table
      does not exist
    - ``WAIT n | NOWAIT`` metadata lock wait timeout (MariaDB 10.3+)
    - ``RENAME INDEX`` (MariaDB 10.5.3+): rename an index in-place

    Official Documentation:
    - ALTER TABLE: https://mariadb.com/kb/en/alter-table/
    - WAIT and NOWAIT: https://mariadb.com/kb/en/wait-and-nowait/

    Version Requirements:
    - Statement-level IF EXISTS: MariaDB 10.5+
    - WAIT n | NOWAIT: MariaDB 10.3+
    - RENAME INDEX: MariaDB 10.5.3+
    """

    def supports_alter_table_if_exists(self) -> bool:
        """Whether statement-level ALTER TABLE IF EXISTS is supported (10.5+)."""
        ...

    def supports_alter_table_wait(self) -> bool:
        """Whether ALTER TABLE WAIT n | NOWAIT is supported (10.3+)."""
        ...

    def supports_rename_index(self) -> bool:
        """Whether ALTER TABLE ... RENAME INDEX is supported (10.5.3+)."""
        ...

    def format_rename_index_statement(
        self,
        expr: "MariaDBRenameIndexExpression",
    ) -> Tuple[str, tuple]:
        """Format a MariaDB ALTER TABLE ... RENAME INDEX statement."""
        ...