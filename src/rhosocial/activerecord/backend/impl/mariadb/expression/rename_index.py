# src/rhosocial/activerecord/backend/impl/mariadb/expression/rename_index.py
"""MariaDB RENAME INDEX expression.

MariaDB 10.5.3+ supports renaming an index with ``ALTER TABLE``:

    ALTER TABLE tbl_name RENAME INDEX old_index_name TO new_index_name

RENAME CONSTRAINT is not supported by MariaDB; the recommended approach is
to drop and recreate the constraint.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBRenameIndexExpression(BaseExpression):
    """Represent a MariaDB ``ALTER TABLE ... RENAME INDEX`` statement.

    Attributes:
        table: Name of the table holding the index.
        old_index_name: Current index name.
        new_index_name: New index name.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        old_index_name: str,
        new_index_name: str,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.table = table
        self.old_index_name = old_index_name
        self.new_index_name = new_index_name
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        """Validate index names.

        Raises:
            TypeError: If index names are not strings.
        """
        if not strict:
            return
        for name in (self.table, self.old_index_name, self.new_index_name):
            if not isinstance(name, str):
                raise TypeError("Table and index names must be strings")

    def to_sql(self):
        """Generate SQL by delegating to the dialect."""
        return self.dialect.format_rename_index_statement(self)
