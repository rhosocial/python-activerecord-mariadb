# src/rhosocial/activerecord/backend/impl/mariadb/expression/truncate.py
"""MariaDB-specific TRUNCATE expression."""

from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
    TruncateExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBTruncateExpression(TruncateExpression):
    """A MariaDB TRUNCATE statement extending the generic one.

    MariaDB adds the ``WAIT n`` / ``NOWAIT`` metadata lock wait options
    (MariaDB 10.3+), which are mutually exclusive and have no generic
    equivalent.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        restart_identity: bool = False,
        cascade: bool = False,
        *,
        wait: Optional[int] = None,
        nowait: bool = False,
    ):
        super().__init__(
            dialect,
            table_name=table_name,
            restart_identity=restart_identity,
            cascade=cascade,
        )
        self.wait = wait
        self.nowait = nowait


__all__ = [
    "MariaDBTruncateExpression",
]
