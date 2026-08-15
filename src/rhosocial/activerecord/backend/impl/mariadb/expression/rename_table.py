# src/rhosocial/activerecord/backend/impl/mariadb/expression/rename_table.py
"""MariaDB RENAME TABLE statement expression.

MariaDB extends the standard RENAME TABLE with several options:

    RENAME TABLE[S] [IF EXISTS] tbl_name [WAIT n | NOWAIT]
      TO new_tbl_name [, tbl_name2 TO new_tbl_name2] ...

Differences from the generic/MySQL form:
- ``TABLE`` or ``TABLES`` keyword (both accepted, no semantic difference)
- Statement-level ``IF EXISTS`` (since MariaDB 10.5): no error if a source
  table does not exist
- Per-statement ``WAIT n | NOWAIT`` lock wait timeout (since MariaDB 10.3)

The statement is atomic for the tables it renames: either all renames
succeed or all are rolled back.
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBRenameTableExpression(BaseExpression):
    """Represent a MariaDB ``RENAME TABLE ...`` statement.

    Attributes:
        renames: Sequence of ``(old_name, new_name)`` table name pairs.
        dialect_options: MariaDB-specific options:
            - 'if_exists': Add statement-level IF EXISTS (MariaDB 10.5+).
            - 'wait': Lock wait timeout in seconds (MariaDB 10.3+).
            - 'nowait': Do not wait for metadata locks (MariaDB 10.3+).
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        renames: List[Tuple[str, str]],
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.renames: List[Tuple[str, str]] = list(renames)
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        """Validate the rename pair list.

        Raises:
            ValueError: If the rename list is empty or contains an invalid pair.
        """
        if not strict:
            return
        if not self.renames:
            raise ValueError("RENAME TABLE requires at least one <table> TO <table> pair")
        for pair in self.renames:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise ValueError(f"Invalid rename pair: {pair!r}")
            old_name, new_name = pair
            if not isinstance(old_name, str) or not isinstance(new_name, str):
                raise TypeError("Rename table names must be strings")

    def to_sql(self) -> Tuple[str, tuple]:
        """Generate SQL by delegating to the dialect."""
        return self.dialect.format_rename_table_statement(self)
