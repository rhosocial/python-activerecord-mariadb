# src/rhosocial/activerecord/backend/impl/mariadb/expression/alter_table.py
"""MariaDB-specific ALTER TABLE statement expression.

MariaDB adds statement-level qualifiers with no generic equivalent:

* ``ALTER TABLE IF EXISTS`` — suppress the error for a missing table (10.5+).
* ``ALTER TABLE ... WAIT n | NOWAIT`` — metadata lock wait timeout (10.3+).

They live on ``MariaDBAlterTableExpression`` (deriving the generic
``AlterTableExpression``) and are rendered by the MariaDB
``format_alter_table_statement`` override. MariaDB does **not** share them with
any other backend.
"""

from typing import List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements import (
    AlterTableAction,
    AlterTableExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MariaDBAlterTableExpression",
]


class MariaDBAlterTableExpression(AlterTableExpression):
    """A MariaDB ``ALTER TABLE`` statement extending the generic one.

    Adds the MariaDB-only statement-level ``if_exists``, ``nowait`` and
    ``wait`` qualifiers.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        actions: List[AlterTableAction],
        schema_name: Optional[str] = None,
        *,
        if_exists: bool = False,
        nowait: bool = False,
        wait: Optional[int] = None,
    ):
        """
        Args:
            schema_name: Namespace to qualify the table with, e.g. ``app``.
                None leaves the name unqualified. An empty string raises
                ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect, table_name, actions, schema_name)
        self.if_exists = if_exists
        self.nowait = nowait
        self.wait = wait
