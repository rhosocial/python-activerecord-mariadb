# src/rhosocial/activerecord/backend/impl/mariadb/protocols/rename_table.py
"""MariaDB RENAME TABLE protocol."""

from typing import TYPE_CHECKING, Protocol, Tuple, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mariadb.expression.rename_table import (
        MariaDBRenameTableExpression,
    )


@runtime_checkable
class MariaDBRenameTableSupport(Protocol):
    """MariaDB RENAME TABLE support protocol.

    Feature Source: Native support (all versions)

    MariaDB supports atomic multi-table renames in a single statement:

        RENAME TABLE[S] [IF EXISTS] tbl_name [WAIT n | NOWAIT]
          TO new_tbl_name [, tbl_name2 TO new_tbl_name2] ...

    Official Documentation:
    - RENAME TABLE: https://mariadb.com/kb/en/rename-table/

    Version Requirements:
    - Basic multi-table rename: All versions
    - WAIT n | NOWAIT: MariaDB 10.3+
    - Statement-level IF EXISTS: MariaDB 10.5+
    """

    def supports_rename_table(self) -> bool:
        """Whether RENAME TABLE is supported."""
        ...

    def supports_multi_table_rename(self) -> bool:
        """Whether multiple rename pairs in one statement are supported."""
        ...

    def supports_rename_table_if_exists(self) -> bool:
        """Whether statement-level IF EXISTS is supported (MariaDB 10.5+)."""
        ...

    def supports_rename_table_wait(self) -> bool:
        """Whether WAIT n | NOWAIT lock wait option is supported (MariaDB 10.3+)."""
        ...

    def format_rename_table_statement(
        self,
        expr: "MariaDBRenameTableExpression",
    ) -> Tuple[str, tuple]:
        """Format a MariaDB RENAME TABLE statement.

        Args:
            expr: MariaDBRenameTableExpression instance
            dialect_options: MariaDB-specific options:
                - 'if_exists': Add statement-level IF EXISTS (MariaDB 10.5+)
                - 'wait': Lock wait timeout in seconds (MariaDB 10.3+)
                - 'nowait': Do not wait for metadata locks (MariaDB 10.3+)
        """
        ...