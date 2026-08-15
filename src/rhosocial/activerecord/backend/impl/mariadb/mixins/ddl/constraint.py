# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl/constraint.py
"""MariaDB ALTER TABLE DROP CONSTRAINT qualifier formatting."""

from typing import Tuple


class MariaDBAlterConstraintModifierMixin:
    """MariaDB ``DROP CONSTRAINT [IF EXISTS]`` formatting.

    MariaDB supports ``DROP CONSTRAINT IF EXISTS`` for named UNIQUE,
    FOREIGN KEY, and CHECK constraints since 10.0.2. The special
    ``DROP PRIMARY KEY`` form never takes ``IF EXISTS`` (MariaDB has a
    separate ``DROP PRIMARY KEY`` clause), so that path is preserved and
    emits the bare form even when ``if_exists=True``.
    """

    def supports_drop_constraint_if_exists(self) -> bool:
        """``DROP CONSTRAINT IF EXISTS`` is supported since MariaDB 10.0.2.

        Exception: ``DROP PRIMARY KEY`` does not accept ``IF EXISTS``.
        """
        return True

    def format_drop_table_constraint_action(self, action) -> Tuple[str, tuple]:
        name = action.constraint_name
        # MariaDB PRIMARY KEY goes through DROP PRIMARY KEY (no IF EXISTS).
        if name.upper() == "PRIMARY":
            return "DROP PRIMARY KEY", ()
        if getattr(action, "if_exists", None) is True:
            result = f"DROP CONSTRAINT IF EXISTS {self.format_identifier(name)}"
        else:
            result = f"DROP CONSTRAINT {self.format_identifier(name)}"
        if getattr(action, "cascade", None):
            result += " CASCADE"
        return result, ()
