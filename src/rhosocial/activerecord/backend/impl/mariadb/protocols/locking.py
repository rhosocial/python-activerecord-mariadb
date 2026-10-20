# src/rhosocial/activerecord/backend/impl/mariadb/protocols/locking.py
"""MariaDB row-level locking protocol."""

from typing import Any, Protocol, Tuple, runtime_checkable

from rhosocial.activerecord.backend.dialect.protocols import LockingSupport


@runtime_checkable
class MariaDBLockingSupport(LockingSupport, Protocol):
    """MariaDB row-level locking protocol.

    Feature Source: MariaDB native (FOR UPDATE and LOCK IN SHARE MODE on all versions)

    MariaDB locking features beyond SQL standard:
    - LOCK IN SHARE MODE: Shared lock (all versions). MariaDB does not
      accept MySQL 8.0's ``FOR SHARE`` spelling at all: errno 1064 on every
      measured version, 10.2.44 through 13.1.1.
    - NOWAIT: Fail immediately if rows are locked (MariaDB 10.3+)
    - SKIP LOCKED: Skip locked rows (MariaDB 10.6+)

    Note: MariaDB does NOT support PostgreSQL's FOR NO KEY UPDATE or
    FOR KEY SHARE lock strengths.

    Official Documentation:
    - Locking Reads: https://mariadb.com/kb/en/locking-reads/

    Version Requirements:
    - FOR UPDATE: All MariaDB versions
    - LOCK IN SHARE MODE: All MariaDB versions
    - NOWAIT: MariaDB 10.3+
    - SKIP LOCKED: MariaDB 10.6+
    """

    def supports_for_share(self) -> bool:
        """Whether FOR SHARE clause is supported.

        Always False on MariaDB: it kept the pre-8.0 LOCK IN SHARE MODE
        spelling and rejects FOR SHARE with errno 1064 on every measured
        version, 10.2.44 through 13.1.1.
        """
        ...

    def supports_for_update_nowait(self) -> bool:
        """Whether FOR UPDATE NOWAIT is supported (MariaDB 10.3+)."""
        ...

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported (MariaDB 10.3+)."""
        ...

    def format_for_update_clause(self, clause: Any) -> Tuple[str, tuple]:
        """Format MariaDB-specific FOR UPDATE clause.

        Args:
            clause: ForUpdateClause instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def supports_for_update(self) -> bool:
        """Whether FOR UPDATE clause is supported.

        MariaDB supports FOR UPDATE in all versions.
        """
        ...

    def supports_lock_strength(self) -> bool:
        """Whether different lock strengths (FOR NO KEY UPDATE, FOR KEY SHARE) are supported.

        MariaDB does NOT support different lock strengths (PostgreSQL feature).
        """
        ...

    def format_lock_in_share_mode(self, clause: Any) -> Tuple[str, tuple]:
        """Format LOCK IN SHARE MODE clause (legacy MariaDB syntax).

        Args:
            clause: ForUpdateClause instance (lock_type='SHARE')

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
