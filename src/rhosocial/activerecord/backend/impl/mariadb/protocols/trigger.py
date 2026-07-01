# src/rhosocial/activerecord/backend/impl/mariadb/protocols/trigger.py
"""MariaDB trigger DDL protocol."""

from typing import Any, Protocol, Tuple, runtime_checkable

from rhosocial.activerecord.backend.dialect.protocols import TriggerSupport


@runtime_checkable
class MariaDBTriggerSupport(TriggerSupport, Protocol):
    """MariaDB trigger DDL protocol.

    Feature Source: Native support (no extension required)

    MariaDB triggers:
    - BEFORE/AFTER: Timing
    - INSERT/UPDATE/DELETE: Event
    - FOR EACH ROW: Level (only row-level triggers supported)
    - NEW/OLD: Row references

    MariaDB-specific trigger enhancements:
    - Trigger IF NOT EXISTS: CREATE OR REPLACE TRIGGER (MariaDB 10.1.4+)
    - Trigger order: FOLLOWS/PRECEDES (MariaDB 10.2.3+)
    - Trigger on all tables: MariaDB 10.3+

    Official Documentation:
    - CREATE TRIGGER: https://mariadb.com/kb/en/create-trigger/

    Version Requirements:
    - Triggers: MariaDB 5.x+
    - Trigger IF NOT EXISTS: MariaDB 10.1.4+
    - Trigger FOLLOWS/PRECEDES: MariaDB 10.2.3+
    """

    def supports_trigger(self) -> bool:
        """Whether triggers are supported."""
        ...

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether CREATE TRIGGER IF NOT EXISTS is supported (MariaDB 10.1.4+)."""
        ...

    def supports_instead_of_trigger(self) -> bool:
        """Whether INSTEAD OF triggers are supported.

        MariaDB does NOT support INSTEAD OF triggers (only BEFORE/AFTER).
        This method always returns False for MariaDB.
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
            expr: CreateTriggerExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_drop_trigger_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement.

        Args:
            expr: DropTriggerExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
