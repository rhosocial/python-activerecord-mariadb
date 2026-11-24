# src/rhosocial/activerecord/backend/impl/mariadb/mixins/trigger.py
"""MariaDB trigger DDL mixin.

MariaDB supports triggers with some differences from MySQL:
- INSTEAD OF triggers for views (MariaDB 10.4+)
- OR REPLACE syntax for triggers
- Multiple triggers per timing/event (MariaDB 10.4+)
"""
from typing import Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import (
        CreateTriggerStatement,
        DropTriggerStatement,
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
    - Both accept IF NOT EXISTS, but from different releases: MySQL 8.0.29,
      MariaDB 10.1.4 (MDEV-7286)
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
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES['INSTEAD_OF_TRIGGER'])

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

    def supports_trigger_order(self) -> bool:
        """Whether trigger ordering (FOLLOWS/PRECEDES) is supported.

        MariaDB 10.2.3+ supports FOLLOWS/PRECEDES for trigger ordering.

        Returns:
            True if MariaDB version >= 10.2.3.
        """
        return self.version_at_least((10, 2, 3))

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether ``CREATE TRIGGER IF NOT EXISTS`` is supported.

        MariaDB 10.1.4 added it, alongside ``OR REPLACE`` and the matching
        DROP clause, as part of "consistent support for IF EXISTS, IF NOT
        EXISTS, and OR REPLACE" (MDEV-7286). The 10.0 grammar has no slot for
        it. See ``MARIADB_VERSION_BOUNDARIES['TRIGGER_IF_NOT_EXISTS']``.

        Note that the MariaDB Knowledge Base has carried two different
        per-clause badges for this option (10.1.4 in the clause body, while a
        table-of-contents entry said 10.2.3); neither is the 10.1.20/10.2.4
        pair sometimes attributed to it. The 10.1.4 release notes and the
        10.1.4-to-10.0.15 grammar comparison are the sources this gate uses.

        Returns:
            True if MariaDB version >= 10.1.4.
        """
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES['TRIGGER_IF_NOT_EXISTS'])

    def supports_trigger_if_exists(self) -> bool:
        """Whether ``DROP TRIGGER IF EXISTS`` is supported.

        It is accepted by every version this backend supports. The clause is
        already in the 10.0.15 grammar (``DROP TRIGGER_SYM opt_if_exists
        sp_name``) and the 10.1.4 release notes describe that release as
        making its support *consistent* rather than introducing it, so there
        is no floor to gate on. Verified live on 10.2.44 through 13.1.1: an
        absent name with ``IF EXISTS`` is a warning (1360), the same name
        without it is errno 1360.

        Returns:
            True.
        """
        return True

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
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES['INSTEAD_OF_TRIGGER'])

    def format_create_trigger_statement(
        self,
        expr: "CreateTriggerStatement"
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
            expr: CreateTriggerStatement instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.objects import Function, Table, Trigger

        # Three objects, each with its own format_method, so each needs its kind
        # checked here: a Function where the table belongs renders as valid SQL
        # over the function's name. The slots are the node's declared fields,
        # read by name rather than probed for.
        for name, value, kind in (
            ("trigger", expr.trigger, Trigger),
            ("table", expr.table, Table),
        ):
            if not isinstance(value, kind):
                raise TypeError(
                    f"CreateTriggerStatement.{name} must be a "
                    f"{kind.__name__}, got {type(value).__name__}"
                )
        if expr.function is not None and not isinstance(expr.function, Function):
            raise TypeError(
                f"CreateTriggerStatement.function must be a Function, "
                f"got {type(expr.function).__name__}"
            )

        # The timing / level / events slots take the core enum or its raw
        # spelling; the enum branch is selected with isinstance, which is the
        # same shape core's ``format_comment_on_statement`` normalises
        # ``object_type`` with.
        from enum import Enum

        timing = expr.timing.value if isinstance(expr.timing, Enum) else expr.timing

        if timing == "INSTEAD OF" and not self.supports_instead_of_trigger():
            raise UnsupportedFeatureError(
                self.name,
                "INSTEAD OF triggers",
                "INSTEAD OF triggers require MariaDB 10.4 or later."
            )

        if expr.level:
            level = expr.level.value if isinstance(expr.level, Enum) else expr.level
            if level == "FOR EACH STATEMENT":
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

        # ``or_replace`` and ``ordering`` are MariaDB-only slots that core's
        # ``CreateTriggerStatement`` does not carry. Read them optionally so a
        # core expression renders the plain form instead of failing on a
        # missing attribute the caller had no way to set.
        if getattr(expr, "or_replace", False):
            parts.append("OR REPLACE")

        parts.append("TRIGGER")

        if expr.if_not_exists:
            if not self.supports_trigger_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "CREATE TRIGGER IF NOT EXISTS",
                    "CREATE TRIGGER IF NOT EXISTS requires MariaDB 10.1.4 or later."
                )
            parts.append("IF NOT EXISTS")

        # The trigger's own name, the table it fires on, and -- when this
        # trigger is ordered against another -- a sibling trigger. Each is a
        # schema object and each renders itself, so a trigger created in
        # another database can say ``app`.`trg` without a second spelling of that.
        trigger_sql, _ = expr.trigger.to_sql()
        parts.append(trigger_sql)
        parts.append(timing)

        if expr.events:
            parts.append(
                expr.events[0].value
                if isinstance(expr.events[0], Enum)
                else expr.events[0]
            )

        parts.append("ON")
        table_sql, _ = expr.table.to_sql()
        parts.append(table_sql)
        parts.append("FOR EACH ROW")

        all_params = []

        ordering = getattr(expr, "ordering", None)
        if ordering:
            order_type, order_trigger = ordering
            order_sql, _ = order_trigger.to_sql()
            parts.append(order_type.upper())
            parts.append(order_sql)

        parts.append("BEGIN")

        if expr.function:
            procedure_sql, _ = expr.function.to_sql()
            parts.append(f"CALL {procedure_sql}();")
        elif expr.body:
            body_sql, body_params = expr.body.to_sql()
            parts.append(body_sql)
            all_params.extend(body_params)

        parts.append("END")

        return " ".join(parts), tuple(all_params)

    def format_drop_trigger_statement(
        self,
        expr: "DropTriggerStatement"
    ) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement for MariaDB.

        Args:
            expr: DropTriggerStatement instance.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            TypeError: ``expr.trigger`` is not a Trigger.
            UnsupportedFeatureError: ``DROP TRIGGER IF EXISTS`` was requested
                but this dialect does not answer the probe.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.objects import Trigger

        if not isinstance(expr.trigger, Trigger):
            raise TypeError(
                f"DropTriggerStatement.trigger must be a Trigger, "
                f"got {type(expr.trigger).__name__}"
            )
        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            if not self.supports_trigger_if_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "DROP TRIGGER IF EXISTS",
                    "The dialect answered supports_trigger_if_exists() as False."
                )
            parts.append("IF EXISTS")

        # MariaDB drops a trigger by its own name; the database is part of
        # that name, so it comes from the object rather than the connection.
        trigger_sql, _ = expr.trigger.to_sql()
        parts.append(trigger_sql)

        return " ".join(parts), ()


__all__ = ['MariaDBTriggerMixin']
