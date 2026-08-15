# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl/column.py
"""MariaDB ALTER TABLE column IF [NOT] EXISTS qualifier formatting."""

from typing import Tuple


class MariaDBAlterColumnModifierMixin:
    """MariaDB column qualifiers for ALTER TABLE actions.

    MariaDB supports the ``IF NOT EXISTS`` / ``IF EXISTS`` qualifiers on
    ``ADD COLUMN`` and ``DROP COLUMN`` since 10.0.2 (vendor extensions,
    not in ISO/IEC 9075-2 §11.10). Applications opt in via
    ``if_not_exists`` / ``if_exists``; ``None`` (default) renders the plain
    SQL-standard form.
    """

    def supports_add_column_if_not_exists(self) -> bool:
        """``ADD COLUMN IF NOT EXISTS`` is supported since MariaDB 10.0.2."""
        return True

    def supports_drop_column_if_exists(self) -> bool:
        """``DROP COLUMN IF EXISTS`` is supported since MariaDB 10.0.2."""
        return True

    def format_add_column_action(self, action) -> Tuple[str, tuple]:
        column_sql, column_params = self.format_column_definition(action.column)
        if getattr(action, "if_not_exists", None) is True:
            return f"ADD COLUMN IF NOT EXISTS {column_sql}", column_params
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(self, action) -> Tuple[str, tuple]:
        if getattr(action, "if_exists", None) is True:
            return f"DROP COLUMN IF EXISTS {self.format_identifier(action.column_name)}", ()
        return f"DROP COLUMN {self.format_identifier(action.column_name)}", ()
