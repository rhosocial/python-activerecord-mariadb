# src/rhosocial/activerecord/backend/impl/mariadb/mixins/trigger.py
"""MariaDB trigger DDL mixin.

MariaDB supports triggers with some differences from MySQL:
- INSTEAD OF triggers for views (MariaDB 10.4+)
- OR REPLACE syntax for triggers
- Multiple triggers per timing/event (MariaDB 10.4+)
"""
from typing import List, Optional, Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import (
        CreateTriggerExpression,
        DropTriggerExpression,
        TriggerEvent,
        TriggerLevel,
    )


class MariaDBTriggerMixin:
    """MariaDB trigger DDL implementation.

    MariaDB trigger features:
    - BEFORE/AFTER: Timing
    - INSERT/UPDATE/DELETE: Events
    - FOR EACH ROW: Level (only row-level triggers supported)
    - INSTEAD OF: For views (MariaDB 10.4+, MySQL doesn't support)
    - NEW/OLD: Row references
    - OR REPLACE: Replace existing trigger
    - Multiple triggers: Multiple triggers per timing/event (10.4+)

    Official Documentation:
    - https://mariadb.com/kb/en/create-trigger/
    - https://mariadb.com/kb/en/trigger/

    Version Requirements:
    - Basic triggers: MariaDB 5.2+
    - INSTEAD OF triggers: MariaDB 10.4+
    - OR REPLACE: MariaDB 10.1.4+
    - Multiple triggers per timing/event: MariaDB 10.4+

    MariaDB vs MySQL:
    - MySQL does NOT support INSTEAD OF triggers
    - MySQL does NOT support multiple triggers per timing/event
    - MySQL 8.0.4+ supports IF NOT EXISTS; MariaDB uses OR REPLACE
    """

    def supports_trigger(self) -> bool:
        """Whether triggers are supported.

        Returns:
            True.
        """
        return True

    def supports_create_trigger(self) -> bool:
        """Whether CREATE TRIGGER is supported.

        Returns:
            True.
        """
        return True

    def supports_drop_trigger(self) -> bool:
        """Whether DROP TRIGGER is supported.

        Returns:
            True.
        """
        return True

    def supports_instead_of_trigger(self) -> bool:
        """Whether INSTEAD OF triggers are supported.

        MariaDB 10.4+ supports INSTEAD OF triggers for views.
        MySQL does NOT support this feature.

        Returns:
            True if MariaDB version >= 10.4.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['INSTEAD_OF_TRIGGER']

    def supports_statement_trigger(self) -> bool:
        """Whether FOR EACH STATEMENT triggers are supported.

        MariaDB does NOT support FOR EACH STATEMENT triggers.

        Returns:
            False.
        """
        return False

    def supports_trigger_referencing(self) -> bool:
        """Whether REFERENCING clause is supported.

        MariaDB does NOT support REFERENCING clause.
        Use OLD and NEW keywords directly.

        Returns:
            False.
        """
        return False

    def supports_trigger_when(self) -> bool:
        """Whether WHEN condition is supported.

        MariaDB does NOT support WHEN condition in triggers.

        Returns:
            False.
        """
        return False

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether CREATE TRIGGER IF NOT EXISTS is supported.

        MariaDB uses OR REPLACE instead of IF NOT EXISTS.

        Returns:
            False (use OR REPLACE).
        """
        return False

    def supports_or_replace_trigger(self) -> bool:
        """Whether CREATE OR REPLACE TRIGGER is supported.

        MariaDB 10.1.4+ supports OR REPLACE.

        Returns:
            True.
        """
        return True

    def supports_multiple_triggers_per_timing(self) -> bool:
        """Whether multiple triggers per timing/event are supported.

        MariaDB 10.4+ supports multiple triggers for the same
        timing and event on a table.

        Returns:
            True if MariaDB version >= 10.4.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['INSTEAD_OF_TRIGGER']

    def format_create_trigger_statement(
        self,
        expr: "CreateTriggerExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement for MariaDB.

        Syntax:
            CREATE [OR REPLACE] TRIGGER [IF NOT EXISTS] trigger_name
            {BEFORE | AFTER | INSTEAD OF}
            {INSERT | UPDATE | UPDATE OF column_list | DELETE}
            ON table_name
            FOR EACH ROW
            [{FOLLOWS | PRECEDES} other_trigger_name]
            trigger_body

        Args:
            expr: CreateTriggerExpression instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        timing = expr.timing.value if hasattr(expr.timing, 'value') else str(expr.timing)

        if timing == "INSTEAD OF" and not self.supports_instead_of_trigger():
            raise UnsupportedFeatureError(
                self.name,
                "INSTEAD OF triggers",
                "INSTEAD OF triggers require MariaDB 10.4 or later."
            )

        if expr.level and hasattr(expr.level, 'value') and expr.level.value == "FOR EACH STATEMENT":
            raise UnsupportedFeatureError(
                self.name,
                "FOR EACH STATEMENT triggers",
                "MariaDB only supports FOR EACH ROW triggers."
            )

        if expr.condition:
            raise UnsupportedFeatureError(
                self.name,
                "WHEN condition in triggers",
                "MariaDB does not support WHEN condition in triggers."
            )

        if expr.referencing:
            raise UnsupportedFeatureError(
                self.name,
                "REFERENCING clause",
                "MariaDB does not support REFERENCING clause. Use OLD and NEW keywords."
            )

        if len(expr.events) > 1:
            raise UnsupportedFeatureError(
                self.name,
                "Multiple trigger events",
                "MariaDB only supports single event per trigger."
            )

        parts = ["CREATE"]

        if expr.or_replace:
            parts.append("OR REPLACE")

        parts.append("TRIGGER")

        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))
        parts.append(timing)

        if expr.events:
            parts.append(expr.events[0].value if hasattr(expr.events[0], 'value') else str(expr.events[0]))

        parts.append("ON")
        parts.append(self.format_identifier(expr.table_name))
        parts.append("FOR EACH ROW")

        all_params = []

        if expr.ordering:
            order_type, order_trigger = expr.ordering
            parts.append(order_type.upper())
            parts.append(self.format_identifier(order_trigger))

        parts.append("BEGIN")

        if expr.function_name:
            parts.append(f"CALL {self.format_identifier(expr.function_name)}();")
        elif expr.body:
            if isinstance(expr.body, str):
                parts.append(expr.body)
            else:
                body_sql, body_params = expr.body.to_sql()
                parts.append(body_sql)
                all_params.extend(body_params)

        parts.append("END")

        return " ".join(parts), tuple(all_params)

    def format_drop_trigger_statement(
        self,
        expr: "DropTriggerExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement for MariaDB.

        Args:
            expr: DropTriggerExpression instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        return " ".join(parts), ()


__all__ = ['MariaDBTriggerMixin']
