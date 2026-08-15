# src/rhosocial/activerecord/backend/impl/mariadb/expression/locking.py
"""
MariaDB-specific row-level locking expressions.

MariaDB supports row-level locking with FOR UPDATE and FOR SHARE:
- FOR UPDATE: Exclusive lock (write lock), blocks other FOR UPDATE and FOR SHARE
- FOR SHARE: Shared lock (read lock), allows other FOR SHARE but blocks FOR UPDATE

MariaDB 10.3+ additionally supports:
- FOR SHARE NOWAIT: Fail immediately if rows are locked
- FOR UPDATE NOWAIT: Fail immediately if rows are locked
- FOR UPDATE SKIP LOCKED: Skip locked rows instead of waiting
- FOR SHARE SKIP LOCKED: Skip locked rows instead of waiting
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause
from rhosocial.activerecord.backend.expression import bases

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBLockStrength(Enum):
    """
    Enumeration of MariaDB row-level lock strength options.

    MariaDB supports two lock strengths for row-level locking:

    - UPDATE: Exclusive lock (FOR UPDATE), blocks all other locks
    - SHARE: Shared lock (FOR SHARE), allows other shared locks

    Version requirements (MariaDB):
    - FOR UPDATE: All versions
    - FOR SHARE: MariaDB 10.3+
    """

    UPDATE = "FOR UPDATE"  # Exclusive lock (strongest)
    SHARE = "FOR SHARE"  # Shared lock (MariaDB 10.3+)


class MariaDBForUpdateClause(ForUpdateClause):
    """
    MariaDB-specific FOR UPDATE clause with lock strength support.

    Extends the standard ForUpdateClause with MariaDB's row-level
    locking capabilities.

    MariaDB supports:
    - FOR UPDATE: Exclusive lock on selected rows
    - FOR SHARE: Shared lock on selected rows (MariaDB 10.3+)
    - NOWAIT: Fail immediately if rows are locked (MariaDB 10.3+)
    - SKIP LOCKED: Skip locked rows instead of waiting (MariaDB 10.3+)

    Note: MariaDB does NOT support PostgreSQL's FOR NO KEY UPDATE
    or FOR KEY SHARE lock strengths.

    Example Usage:
        # Basic FOR UPDATE (same as parent class)
        for_update = MariaDBForUpdateClause(dialect)

        # FOR SHARE (MariaDB 10.3+)
        for_update = MariaDBForUpdateClause(dialect, strength=MariaDBLockStrength.SHARE)

        # FOR SHARE with NOWAIT (MariaDB 10.3+)
        for_update = MariaDBForUpdateClause(
            dialect,
            strength=MariaDBLockStrength.SHARE,
            nowait=True
        )

        # FOR UPDATE with SKIP LOCKED (MariaDB 10.3+)
        for_update = MariaDBForUpdateClause(
            dialect,
            strength=MariaDBLockStrength.UPDATE,
            skip_locked=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        strength: Optional[MariaDBLockStrength] = None,
        of_columns: Optional[List[Union[str, "bases.BaseExpression"]]] = None,
        nowait: bool = False,
        skip_locked: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MariaDB FOR UPDATE clause.

        Args:
            dialect: The SQL dialect to use for formatting
            strength: Lock strength (defaults to UPDATE for backward compatibility)
            of_columns: Columns to apply the lock to
            nowait: If True, fail immediately if rows are locked (MariaDB 10.3+)
            skip_locked: If True, skip locked rows instead of waiting (MariaDB 10.3+)
            dialect_options: Additional dialect-specific options
        """
        super().__init__(
            dialect,
            of_columns=of_columns,
            nowait=nowait,
            skip_locked=skip_locked,
            dialect_options=dialect_options,
        )
        # Default to UPDATE for backward compatibility
        self.strength = strength if strength is not None else MariaDBLockStrength.UPDATE

    def to_sql(self) -> "bases.SQLQueryAndParams":
        """
        Generate the SQL representation of the MariaDB FOR UPDATE clause.

        Delegates to the dialect's format_for_update_clause method
        to follow the Expression-Dialect separation pattern.

        Returns:
            Tuple containing:
            - SQL string fragment for the FOR UPDATE clause
            - Tuple of parameter values for prepared statements
        """
        return self.dialect.format_for_update_clause(self)