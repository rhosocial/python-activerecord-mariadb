# src/rhosocial/activerecord/backend/impl/mariadb/expression/trigger.py
"""MariaDB ``CREATE TRIGGER`` statement expression.

MariaDB's ``CREATE TRIGGER`` accepts three options that SQL:1999 does not have,
so they cannot live on core's expression without lying to every other dialect:

``OR REPLACE``
    MariaDB drops and redefines an existing trigger instead of failing. MySQL
    has no such option; Oracle has its own expression for it.

``FOLLOWS`` / ``PRECEDES``
    Orders this trigger relative to another on the same table and event. MariaDB
    keeps the order stable but does not store it in the trigger definition.

``body``
    The statement to run. MariaDB inherits MySQL's inline body rather than
    requiring a stored function, which is what core's ``function_name`` models.

Declaring them here is what lets the formatter read ``expr.or_replace``,
``expr.ordering`` and ``expr.body`` directly. It previously reached for them with
``getattr(expr, ..., default)``, which turned "this dialect has no such option"
into "this statement silently omits the option the caller asked for".
"""

from typing import List, Optional, Sequence, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.expression.predicates import SQLPredicate
from rhosocial.activerecord.backend.expression.statements import (
    CreateTriggerExpression,
    TriggerEvent,
    TriggerLevel,
    TriggerTiming,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MariaDBCreateTriggerExpression",
]


class MariaDBCreateTriggerExpression(CreateTriggerExpression):
    """A MariaDB ``CREATE TRIGGER`` statement.

    Extends the generic statement with the three MariaDB-only options. Every
    attribute the MariaDB formatter reads is declared here, so the formatter
    never has to ask whether one is present.

    A trigger needs exactly one of ``function_name`` (core's model, calling a
    stored function, given as a ``TableExpression``) or ``body`` (the inline
    statement MariaDB normally uses), and the constructor insists on it: with
    neither, the statement rendered an empty ``BEGIN END``; with both, the
    body was dropped and only the call survived. Neither is something the
    caller could see, so both are refused here instead.

    The signature is long because it mirrors core's ``CreateTriggerExpression``
    plus three MariaDB-only options. That is safer than it looks: everything
    past ``events`` is keyword-only, so no two parameters can be confused.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        trigger_name: str,
        table: TableExpression,
        timing: TriggerTiming,
        events: List[TriggerEvent],
        *,
        function_name: Optional[TableExpression] = None,
        body: Optional[BaseExpression] = None,
        or_replace: bool = False,
        ordering: Optional[Tuple[str, str]] = None,
        level: TriggerLevel = TriggerLevel.ROW,
        condition: Optional[SQLPredicate] = None,
        update_columns: Optional[Sequence[str]] = None,
        referencing: Optional[str] = None,
        if_not_exists: bool = False,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            table: The table the trigger is attached to, carrying its own
                namespace, independently of ``schema_name``.
            schema_name: Namespace to qualify the trigger with, e.g. ``app``.
                None leaves the name unqualified. An empty string raises
                ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
            body: The inline statement to run, as an expression. Mutually
                exclusive with function_name in practice; the formatter prefers
                function_name when both are given.
            or_replace: Redefine an existing trigger of the same name instead
                of failing.
            ordering: ``(relation, other_trigger_name)`` where relation is
                ``"FOLLOWS"`` or ``"PRECEDES"``, placing this trigger after or
                before another on the same table and event.
        """
        if (function_name is None) == (body is None):
            raise ValueError(
                "a MariaDB trigger needs exactly one of function_name or body: "
                f"got function_name={function_name!r}, body={'set' if body is not None else None}"
            )
        super().__init__(
            dialect,
            trigger_name,
            table,
            timing,
            events,
            function_name,
            level=level,
            condition=condition,
            update_columns=list(update_columns) if update_columns else None,
            referencing=referencing,
            if_not_exists=if_not_exists,
            schema_name=schema_name,
        )
        self.body = body
        self.or_replace = or_replace
        self.ordering = ordering
