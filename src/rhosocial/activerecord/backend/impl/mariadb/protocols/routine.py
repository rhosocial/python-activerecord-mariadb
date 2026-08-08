# src/rhosocial/activerecord/backend/impl/mariadb/protocols/routine.py
"""MariaDB stored routine protocol."""

from typing import TYPE_CHECKING, Protocol, Tuple, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mariadb.expression.routine import (
        MariaDBCallExpression,
        MariaDBCreateFunctionExpression,
        MariaDBCreateProcedureExpression,
        MariaDBDropFunctionExpression,
        MariaDBDropProcedureExpression,
    )


@runtime_checkable
class MariaDBRoutineSupport(Protocol):
    """MariaDB stored routine support protocol.

    Feature Source: MariaDB 5.2+ (stored procedures/functions), CALL all
    versions.

    Covers CREATE/DROP PROCEDURE, CREATE/DROP FUNCTION (stored and aggregate),
    and CALL. MariaDB extensions include ``CREATE OR REPLACE`` and
    ``CREATE ... IF NOT EXISTS`` (both MariaDB 10.1.3+), plus aggregate
    functions.

    Official Documentation:
    - Stored procedures: https://mariadb.com/kb/en/stored-procedures/
    - CREATE PROCEDURE: https://mariadb.com/kb/en/create-procedure/
    - CREATE FUNCTION: https://mariadb.com/kb/en/create-function/
    - CALL: https://mariadb.com/kb/en/call/
    """

    def supports_procedure(self) -> bool:
        """Whether stored procedures are supported."""
        ...

    def supports_stored_function(self) -> bool:
        """Whether stored functions are supported."""
        ...

    def supports_call(self) -> bool:
        """Whether CALL is supported."""
        ...

    def supports_routine_or_replace(self) -> bool:
        """Whether CREATE OR REPLACE is supported (MariaDB 10.1.3+)."""
        ...

    def supports_routine_if_not_exists(self) -> bool:
        """Whether CREATE ... IF NOT EXISTS is supported (MariaDB 10.1.3+)."""
        ...

    def supports_aggregate_function(self) -> bool:
        """Whether CREATE AGGREGATE FUNCTION is supported."""
        ...

    def format_create_procedure_statement(
        self,
        expr: "MariaDBCreateProcedureExpression",
    ) -> Tuple[str, tuple]:
        """Format CREATE PROCEDURE."""
        ...

    def format_drop_procedure_statement(
        self,
        expr: "MariaDBDropProcedureExpression",
    ) -> Tuple[str, tuple]:
        """Format DROP PROCEDURE."""
        ...

    def format_create_function_statement(
        self,
        expr: "MariaDBCreateFunctionExpression",
    ) -> Tuple[str, tuple]:
        """Format CREATE FUNCTION (stored / aggregate function)."""
        ...

    def format_drop_function_statement(
        self,
        expr: "MariaDBDropFunctionExpression",
    ) -> Tuple[str, tuple]:
        """Format DROP FUNCTION."""
        ...

    def format_call_statement(self, expr: "MariaDBCallExpression") -> Tuple[str, tuple]:
        """Format CALL."""
        ...
