# src/rhosocial/activerecord/backend/impl/mariadb/mixins/locking.py
"""MariaDB row-level locking mixin.

MariaDB supports FOR UPDATE, FOR SHARE, NOWAIT, and SKIP LOCKED.
"""
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause


class MariaDBLockingMixin:
    """MariaDB row-level locking support mixin.

    MariaDB locking features:
    - FOR UPDATE: Exclusive lock (all versions)
    - FOR SHARE: Shared lock (replaces LOCK IN SHARE MODE)
    - NOWAIT: Fail immediately if rows are locked (10.3+)
    - SKIP LOCKED: Skip locked rows (10.3+)

    Official Documentation:
    - https://mariadb.com/kb/en/select/#lock-clauses

    Version Requirements:
    - FOR UPDATE: All versions
    - FOR SHARE: All versions (alias for LOCK IN SHARE MODE)
    - NOWAIT: MariaDB 10.3+
    - SKIP LOCKED: MariaDB 10.3+

    Note: MariaDB does NOT support PostgreSQL's:
    - FOR NO KEY UPDATE
    - FOR KEY SHARE
    """

    def supports_for_update(self) -> bool:
        """Whether FOR UPDATE clause is supported.

        MariaDB supports FOR UPDATE in all versions.

        Returns:
            True.
        """
        return True

    def supports_for_share(self) -> bool:
        """Whether FOR SHARE clause is supported.

        MariaDB supports FOR SHARE (synonym for LOCK IN SHARE MODE).

        Returns:
            True.
        """
        return True

    def supports_for_update_nowait(self) -> bool:
        """Whether FOR UPDATE NOWAIT is supported.

        MariaDB 10.3+ supports NOWAIT.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['SKIP_LOCKED']

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported.

        MariaDB 10.3+ supports SKIP LOCKED.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['SKIP_LOCKED']

    def supports_lock_strength(self, strength: str) -> bool:
        """Check if a specific lock strength is supported.

        Args:
            strength: Lock strength name ('UPDATE', 'SHARE').

        Returns:
            True if supported.
        """
        strength_upper = strength.upper() if isinstance(strength, str) else str(strength)
        valid_strengths = {'UPDATE', 'SHARE'}
        return strength_upper in valid_strengths

    def format_for_update_clause(
        self,
        clause: "ForUpdateClause"
    ) -> Tuple[str, tuple]:
        """Format FOR UPDATE clause for MariaDB.

        Syntax:
            FOR UPDATE [OF tbl_name [, tbl_name] ...] [NOWAIT | SKIP LOCKED]
            FOR SHARE [OF tbl_name [, tbl_name] ...] [NOWAIT | SKIP LOCKED]

        Args:
            clause: ForUpdateClause instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        parts = []

        lock_type = getattr(clause, 'lock_type', 'UPDATE')
        if isinstance(lock_type, str):
            lock_type_upper = lock_type.upper()
        else:
            lock_type_upper = str(lock_type)

        if lock_type_upper == 'SHARE':
            parts.append("FOR SHARE")
        else:
            parts.append("FOR UPDATE")

        if clause.tables:
            tables_sql = ", ".join(
                self.format_identifier(t) for t in clause.tables
            )
            parts.append(f"OF {tables_sql}")

        nowait = getattr(clause, 'nowait', False)
        skip_locked = getattr(clause, 'skip_locked', False)

        if skip_locked:
            if not self.supports_for_update_skip_locked():
                from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name,
                    "SKIP LOCKED",
                    "SKIP LOCKED requires MariaDB 10.3 or later."
                )
            parts.append("SKIP LOCKED")
        elif nowait:
            if not self.supports_for_update_nowait():
                from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name,
                    "NOWAIT",
                    "NOWAIT requires MariaDB 10.3 or later."
                )
            parts.append("NOWAIT")

        return " ".join(parts), ()

    def format_lock_in_share_mode(self) -> Tuple[str, tuple]:
        """Format LOCK IN SHARE MODE clause (legacy syntax).

        This is the older syntax for FOR SHARE.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return "LOCK IN SHARE MODE", ()


__all__ = ['MariaDBLockingMixin']
