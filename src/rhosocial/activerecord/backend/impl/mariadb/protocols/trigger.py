# src/rhosocial/activerecord/backend/impl/mariadb/protocols/trigger.py
"""MariaDB trigger DDL protocol."""

from typing import Any, Protocol, Tuple, runtime_checkable

from rhosocial.activerecord.backend.dialect.protocols import TriggerObjectSupport


@runtime_checkable
class MariaDBTriggerSupport(TriggerObjectSupport, Protocol):
    """MariaDB trigger DDL protocol.

    Feature Source: Native support (no extension required)

    MariaDB triggers:
    - BEFORE/AFTER: Timing
    - INSERT/UPDATE/DELETE: Event
    - FOR EACH ROW: Level (only row-level triggers supported)
    - NEW/OLD: Row references

    MariaDB-specific trigger enhancements:
    - Trigger IF NOT EXISTS: CREATE TRIGGER IF NOT EXISTS (MariaDB 10.1.4+)
    - Trigger ordering: FOLLOWS/PRECEDES (MariaDB 10.2.3+)
    - INSTEAD OF triggers on views: MariaDB 10.4+

    Official Documentation:
    - CREATE TRIGGER: https://mariadb.com/kb/en/create-trigger/
    - DROP TRIGGER: https://mariadb.com/kb/en/drop-trigger/
    - 10.1.4 release notes (MDEV-7286): https://mariadb.com/docs/release-notes/community-server/old-releases/10.1/10.1.4.md

    Version Requirements:
    - Triggers: MariaDB 5.x+
    - Trigger IF NOT EXISTS: MariaDB 10.1.4+
    - DROP TRIGGER IF EXISTS: every supported version (present in 10.0.15)
    - Trigger FOLLOWS/PRECEDES: MariaDB 10.2.3+
    """

    def supports_trigger(self) -> bool:
        """Whether triggers are supported."""
        ...

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether CREATE TRIGGER IF NOT EXISTS is supported (MariaDB 10.1.4+)."""
        ...

    def supports_trigger_if_exists(self) -> bool:
        """Whether DROP TRIGGER IF EXISTS is supported (all supported versions)."""
        ...

    def supports_instead_of_trigger(self) -> bool:
        """Whether INSTEAD OF triggers are supported.

        MariaDB 10.4+ supports INSTEAD OF triggers on views; before that
        floor the formatter refuses the timing by name.
        """
        ...

    def supports_statement_trigger(self) -> bool:
        """Whether statement-level triggers are supported.

        MariaDB only supports row-level triggers (FOR EACH ROW).
        This method always returns False for MariaDB.
        """
        ...

    def supports_trigger_referencing(self) -> bool:
        """Whether trigger referencing (NEW/OLD) is supported.

        MariaDB supports NEW and OLD row references in triggers.
        """
        ...

    def supports_trigger_when(self) -> bool:
        """Whether WHEN condition on triggers is supported.

        MariaDB does NOT support WHEN condition on triggers.
        This method always returns False for MariaDB.
        """
        ...

    def supports_trigger_order(self) -> bool:
        """Whether trigger ordering (FOLLOWS/PRECEDES) is supported (MariaDB 10.2.3+)."""
        ...

    def supports_create_trigger(self) -> bool:
        """Whether CREATE TRIGGER is supported."""
        ...

    def supports_drop_trigger(self) -> bool:
        """Whether DROP TRIGGER is supported."""
        ...

    def supports_or_replace_trigger(self) -> bool:
        """Whether CREATE OR REPLACE TRIGGER is supported (MariaDB 10.1.4+)."""
        ...

    def supports_multiple_triggers_per_timing(self) -> bool:
        """Whether multiple triggers per timing/event are supported (MariaDB 10.2.3+)."""
        ...

    def format_create_trigger_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement.

        Args:
            expr: CreateTriggerStatement instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_drop_trigger_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement.

        Args:
            expr: DropTriggerStatement instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
