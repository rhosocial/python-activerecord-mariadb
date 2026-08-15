# src/rhosocial/activerecord/backend/impl/mariadb/protocols/modify_column.py
"""MariaDB MODIFY COLUMN and CHANGE COLUMN protocol."""

from typing import Protocol, Tuple, runtime_checkable


@runtime_checkable
class MariaDBModifyColumnSupport(Protocol):
    """MariaDB MODIFY COLUMN and CHANGE COLUMN protocol.

    Feature Source: MariaDB native (not SQL standard)

    MariaDB ALTER TABLE features beyond SQL standard:
    - MODIFY COLUMN: Redefine a column with new specification (name unchanged)
    - CHANGE COLUMN: Rename and redefine a column in one operation
    - FIRST/AFTER: Column positioning within the table

    Official Documentation:
    - ALTER TABLE: https://mariadb.com/kb/en/alter-table/

    Version Requirements:
    - MODIFY COLUMN: All MariaDB versions
    - CHANGE COLUMN: All MariaDB versions
    """

    def supports_modify_column(self) -> bool:
        """Whether MODIFY COLUMN is supported."""
        ...

    def supports_change_column(self) -> bool:
        """Whether CHANGE COLUMN is supported."""
        ...

    def format_modify_column_action(self, action) -> Tuple[str, tuple]:
        """Format MODIFY COLUMN action for ALTER TABLE.

        Args:
            action: ModifyColumn action instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_change_column_action(self, action) -> Tuple[str, tuple]:
        """Format CHANGE COLUMN action for ALTER TABLE.

        Args:
            action: ChangeColumn action instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
