# src/rhosocial/activerecord/backend/impl/mariadb/expression/dml.py
"""MariaDB-specific DML expression classes."""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements import InsertExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBInsertExpression(InsertExpression):
    """A MariaDB INSERT statement extending the generic one.

    MariaDB supports ``REPLACE INTO`` and ``INSERT IGNORE`` which have no
    direct generic equivalent and different semantics from other backends. The
    flags live here as typed fields and are rendered by the MariaDB
    ``format_insert_statement`` override.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        into,
        source,
        columns=None,
        *,
        on_conflict=None,
        returning=None,
        replace: bool = False,
        ignore: bool = False,
    ):
        super().__init__(
            dialect,
            into=into,
            source=source,
            columns=columns,
            on_conflict=on_conflict,
            returning=returning,
        )
        self.replace = replace
        self.ignore = ignore


__all__ = [
    "MariaDBInsertExpression",
]
