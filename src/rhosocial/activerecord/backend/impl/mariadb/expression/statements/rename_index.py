# src/rhosocial/activerecord/backend/impl/mariadb/expression/statements/rename_index.py
"""MariaDB RENAME INDEX expression.

MariaDB 10.5.3+ supports renaming an index with ``ALTER TABLE``:

    ALTER TABLE tbl_name RENAME INDEX old_index_name TO new_index_name

RENAME CONSTRAINT is not supported by MariaDB; the recommended approach is
to drop and recreate the constraint.
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Index, Table

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBRenameIndexStatement(BaseExpression):
    """Represent a MariaDB ``ALTER TABLE ... RENAME INDEX`` statement.

    Attributes:
        table: The table holding the index, as a
            :class:`~...expression.objects.Table`. The database a table
            lives in is a named slot on the object rather than a string
            spliced into both halves of the statement, which is what makes
            ``ALTER TABLE app.users RENAME INDEX ...`` expressible.
        old_index: The index as it is now.
        new_index: The index as it will be known.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_rename_index_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Table,
        old_index: Index,
        new_index: Index,
    ):
        super().__init__(dialect)
        self.table = table
        self.old_index = old_index
        self.new_index = new_index

    def validate(self, strict: bool = True) -> None:
        """Validate the three objects this statement names.

        Raises:
            TypeError: If any of the three is not the kind of object the
                statement acts on.
        """
        if not strict:
            return
        if not isinstance(self.table, Table):
            raise TypeError(
                f"table must be a Table, got {type(self.table).__name__}"
            )
        for name, value in (("old_index", self.old_index), ("new_index", self.new_index)):
            if not isinstance(value, Index):
                raise TypeError(
                    f"{name} must be an Index, got {type(value).__name__}"
                )
