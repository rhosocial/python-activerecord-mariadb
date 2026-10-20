# src/rhosocial/activerecord/backend/impl/mariadb/mixins/locking.py
"""MariaDB row-level locking mixin.

MariaDB supports FOR UPDATE, LOCK IN SHARE MODE, NOWAIT, and SKIP LOCKED.
"""
from typing import Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause


class MariaDBLockingMixin:
    """MariaDB row-level locking support mixin.

    MariaDB locking features:
    - FOR UPDATE: Exclusive lock (all versions)
    - LOCK IN SHARE MODE: Shared lock (all versions) -- MariaDB's only
      spelling of the shared lock
    - NOWAIT: Fail immediately if rows are locked (10.3+)
    - SKIP LOCKED: Skip locked rows (10.6+)

    Official Documentation:
    - https://mariadb.com/kb/en/select/#lock-clauses

    Version Requirements:
    - FOR UPDATE: All versions
    - LOCK IN SHARE MODE: All versions
    - NOWAIT: MariaDB 10.3+
    - SKIP LOCKED: MariaDB 10.6+

    Note: MariaDB does NOT support PostgreSQL's:
    - FOR NO KEY UPDATE
    - FOR KEY SHARE

    Nor MySQL 8.0's ``FOR SHARE`` spelling of the shared lock: MariaDB kept
    the pre-8.0 ``LOCK IN SHARE MODE`` form, so ``FOR SHARE`` is a syntax
    error there (errno 1064 on every measured version, 10.2.44 through
    13.1.1 -- see :meth:`supports_for_share`). The shared lock and the wait
    modifiers do not combine either: ``LOCK IN SHARE MODE NOWAIT`` and
    ``LOCK IN SHARE MODE SKIP LOCKED`` are also errno 1064 on every measured
    version, so only ``FOR UPDATE`` carries a wait modifier here.
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

        ``FOR SHARE`` is MySQL 8.0's spelling of the shared lock. MariaDB
        never adopted it: it kept the pre-8.0 ``LOCK IN SHARE MODE`` form, so
        the spelling is a parse error there rather than a synonym.

        Measured live on the 15-server grid (direct connections, TLSv1.2):
        ``SELECT 1 FOR SHARE`` and ``SELECT ... FOR SHARE`` over a subquery
        are both rejected with errno 1064 ("You have an error in your SQL
        syntax ...") on 10.2.44, 10.3.39, 10.4.34, 10.5.29, 10.6.28,
        10.11.19, 11.4.13, 11.7.2, 11.8.9, 12.0.2, 12.1.2, 12.2.2, 12.3.3,
        13.0.2 and 13.1.1 -- so not one version on the grid, newest included,
        accepts the spelling. The shared lock itself works on every one of
        them under the spelling MariaDB kept, which is what
        :meth:`supports_lock_in_share_mode` reports and what the formatter
        refuses in favour of (see :meth:`format_for_update_clause`).

        Returns:
            False.
        """
        return False

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

    def supports_lock_in_share_mode(self) -> bool:
        """Whether the legacy LOCK IN SHARE MODE syntax is supported."""
        return True

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
            FOR UPDATE [NOWAIT | SKIP LOCKED]
            LOCK IN SHARE MODE

        ``FOR SHARE`` is MySQL 8.0's spelling of the shared lock and is not a
        MariaDB spelling at all, so a ``SHARE`` strength is refused here
        rather than re-written: the spelling MariaDB does accept takes no
        wait modifier (see :meth:`supports_for_share`).

        Args:
            clause: ForUpdateClause instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression import LockStrength

        parts = []

        strength = clause.strength
        # The clause text is the enum's ``phrase``, never a copy kept here:
        # core writes each strength's SQL exactly once (``_LOCK_PHRASES``),
        # so a hand-maintained duplicate in this override would drift the
        # moment core adds or renames a member -- and it would have to be
        # kept in step with the probes below anyway, which are MariaDB's
        # own answers. What a server accepts stays a per-backend fact, so
        # the gating is by probe and the spelling is by the enum.
        if strength == LockStrength.NO_KEY_UPDATE and not self.supports_for_no_key_update():
            raise UnsupportedFeatureError(self.name, strength.phrase)
        if strength == LockStrength.SHARE and not self.supports_for_share():
            # Refuse, do not re-spell. The shared lock does exist here, but
            # only as LOCK IN SHARE MODE, and that form takes neither
            # NOWAIT nor SKIP LOCKED: both are errno 1064 on all 15 measured
            # versions, so translating the strength would move the refusal to
            # execution time on exactly the requests that carry a modifier --
            # and a formatter that renders a strength its own probe answered
            # False for makes the probe decorative. Core's answer for a
            # dialect whose FOR SHARE probe is False is this same error, so
            # the spelling stays one answer across both layers; what this
            # override adds is the name of the spelling MariaDB does accept.
            raise UnsupportedFeatureError(
                self.name,
                strength.phrase,
                "MariaDB spells the shared lock LOCK IN SHARE MODE, not FOR "
                "SHARE (errno 1064 on every measured version, 10.2.44 "
                "through 13.1.1), and LOCK IN SHARE MODE accepts neither "
                "NOWAIT nor SKIP LOCKED. Use LockStrength.LOCK_IN_SHARE_MODE, "
                "or format_lock_in_share_mode(), for a shared lock here.",
            )
        if strength == LockStrength.KEY_SHARE and not self.supports_for_key_share():
            raise UnsupportedFeatureError(self.name, strength.phrase)
        if strength == LockStrength.LOCK_IN_SHARE_MODE and not self.supports_lock_in_share_mode():
            raise UnsupportedFeatureError(
                self.name, strength.phrase,
                "This MariaDB dialect does not support LOCK IN SHARE MODE."
            )
        parts.append(strength.phrase)

        if clause.of_columns:
            # An OF entry is either a bare name or an expression. A schema
            # object renders itself -- so a lock can name a table in another
            # database -- while a bare string is a column name and takes the
            # identifier formatter. This is core's own contract for the
            # clause, spelled out because the MariaDB override does not
            # inherit core's formatter.
            of_parts = []
            for entry in clause.of_columns:
                if isinstance(entry, str):
                    of_parts.append(self.format_identifier(entry))
                else:
                    of_parts.append(entry.to_sql()[0])
            tables_sql = ", ".join(of_parts)
            parts.append(f"OF {tables_sql}")

        if clause.skip_locked:
            if not self.supports_for_update_skip_locked():
                raise UnsupportedFeatureError(
                    self.name,
                    "SKIP LOCKED",
                    "SKIP LOCKED requires MariaDB 10.3 or later."
                )
            parts.append("SKIP LOCKED")
        elif clause.nowait:
            if not self.supports_for_update_nowait():
                raise UnsupportedFeatureError(
                    self.name,
                    "NOWAIT",
                    "NOWAIT requires MariaDB 10.3 or later."
                )
            parts.append("NOWAIT")

        return " ".join(parts), ()

    def format_lock_in_share_mode(self, clause: "ForUpdateClause" = None) -> Tuple[str, tuple]:
        """Format LOCK IN SHARE MODE clause.

        This is MariaDB's spelling of the shared lock -- the only one it
        has; MySQL 8.0's ``FOR SHARE`` is a syntax error here (errno 1064 on
        every measured version). Accepted on every version, 10.2.44 through
        13.1.1.

        Args:
            clause: Optional ForUpdateClause instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return "LOCK IN SHARE MODE", ()


__all__ = ['MariaDBLockingMixin']
