# src/rhosocial/activerecord/backend/impl/mariadb/mixins/modify_column.py
"""MariaDB MODIFY COLUMN and CHANGE COLUMN mixin.

MariaDB ALTER TABLE features beyond SQL standard:
- MODIFY COLUMN: Redefine a column with new specification (name unchanged)
- CHANGE COLUMN: Rename and redefine a column in one operation
- FIRST/AFTER: Column positioning within the table
"""
from typing import Tuple


class MariaDBModifyColumnMixin:
    """MariaDB MODIFY COLUMN and CHANGE COLUMN implementation.

    MariaDB ALTER TABLE features beyond SQL standard:
    - MODIFY COLUMN: Redefine a column with new specification (name unchanged)
    - CHANGE COLUMN: Rename and redefine a column in one operation
    - FIRST/AFTER: Column positioning within the table

    Version Requirements:
    - MODIFY COLUMN: All MariaDB versions
    - CHANGE COLUMN: All MariaDB versions
    """

    def supports_modify_column(self) -> bool:
        """Whether MODIFY COLUMN is supported (all MariaDB versions)."""
        return True

    def supports_change_column(self) -> bool:
        """Whether CHANGE COLUMN is supported (all MariaDB versions)."""
        return True

    def format_modify_column_action(self, action) -> Tuple[str, tuple]:
        """Format MODIFY COLUMN action for ALTER TABLE.

        Args:
            action: ModifyColumn action instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        col_sql, col_params = self.format_column_definition(action.column)
        sql = f"MODIFY COLUMN {col_sql}"
        if action.after_column:
            sql += f" AFTER {self.format_identifier(action.after_column)}"
        elif action.first:
            sql += " FIRST"
        return sql, col_params

    def format_change_column_action(self, action) -> Tuple[str, tuple]:
        """Format CHANGE COLUMN action for ALTER TABLE.

        Args:
            action: ChangeColumn action instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        col_sql, col_params = self.format_column_definition(action.column)
        sql = f"CHANGE COLUMN {self.format_identifier(action.old_name)} {col_sql}"
        if action.after_column:
            sql += f" AFTER {self.format_identifier(action.after_column)}"
        elif action.first:
            sql += " FIRST"
        return sql, col_params


__all__ = ['MariaDBModifyColumnMixin']