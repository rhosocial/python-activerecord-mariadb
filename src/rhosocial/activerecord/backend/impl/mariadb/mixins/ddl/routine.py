# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl/routine.py
"""MariaDB stored routine mixin.

MariaDB supports stored procedures and stored functions with extensions over
the SQL/PSM standard:

    CREATE [OR REPLACE] PROCEDURE name ([params]) body
    CREATE [OR REPLACE] PROCEDURE IF NOT EXISTS name ([params]) body
    DROP PROCEDURE [IF EXISTS] name
    CREATE [OR REPLACE] [AGGREGATE] FUNCTION name ([params]) RETURNS type body
    DROP FUNCTION [IF EXISTS] name
    CALL name([args])
"""
from typing import TYPE_CHECKING, Tuple

from ..backend import MARIADB_VERSION_BOUNDARIES
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mariadb.expression.routine import (
        MariaDBCallExpression,
        MariaDBCreateFunctionExpression,
        MariaDBCreateProcedureExpression,
        MariaDBDropFunctionExpression,
        MariaDBDropProcedureExpression,
    )


def _format_param(dialect, param) -> str:
    """Format a stored-routine parameter definition.

    A param may be a plain string (``IN name TYPE``), a tuple
    ``(mode, name, type)``, or ``(name, type)``.
    """
    if isinstance(param, tuple):
        if len(param) == 3:
            mode, name, type_sql = param
            return f"{mode} {dialect.format_identifier(name)} {type_sql}"
        if len(param) == 2:
            name, type_sql = param
            return f"{dialect.format_identifier(name)} {type_sql}"
        raise ValueError(f"Invalid parameter definition: {param!r}")
    return str(param)


class MariaDBRoutineMixin:
    """MariaDB stored routine (procedure / function / CALL) support."""

    def supports_procedure(self) -> bool:
        return True

    def supports_stored_function(self) -> bool:
        return True

    def supports_call(self) -> bool:
        return True

    def supports_routine_or_replace(self) -> bool:
        """Whether CREATE OR REPLACE PROCEDURE/FUNCTION is supported.

        MariaDB 10.1.3+ supports ``CREATE OR REPLACE`` for routines.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['ROUTINE_OR_REPLACE']

    def supports_routine_if_not_exists(self) -> bool:
        """Whether CREATE ... IF NOT EXISTS is supported.

        MariaDB 10.1.3+ supports ``CREATE PROCEDURE IF NOT EXISTS``.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['ROUTINE_IF_NOT_EXISTS']

    def supports_aggregate_function(self) -> bool:
        """Whether CREATE AGGREGATE FUNCTION is supported (all versions)."""
        return True

    def format_create_procedure_statement(
        self,
        expr: "MariaDBCreateProcedureExpression",
    ) -> Tuple[str, tuple]:
        """Format ``CREATE [OR REPLACE] [IF NOT EXISTS] PROCEDURE name(params) body``."""
        expr.validate(strict=self.strict_validation)

        parts = ["CREATE"]
        if expr.or_replace:
            if not self.supports_routine_or_replace():
                raise UnsupportedFeatureError(
                    self.name,
                    "CREATE OR REPLACE PROCEDURE",
                    "OR REPLACE for routines requires MariaDB 10.1.3 or later."
                )
            parts.append("OR REPLACE")
        if expr.if_not_exists:
            if not self.supports_routine_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "CREATE PROCEDURE IF NOT EXISTS",
                    "IF NOT EXISTS for routines requires MariaDB 10.1.3 or later."
                )
            parts.append("IF NOT EXISTS")
        parts.append("PROCEDURE")
        parts.append(expr._format_name())

        params = ", ".join(_format_param(self, p) for p in expr.params)
        parts.append(f"({params})")
        if expr.body:
            parts.append(expr.body)
        return " ".join(parts), ()

    def format_drop_procedure_statement(
        self,
        expr: "MariaDBDropProcedureExpression",
    ) -> Tuple[str, tuple]:
        """Format ``DROP PROCEDURE [IF EXISTS] name``."""
        expr.validate(strict=self.strict_validation)
        parts = ["DROP PROCEDURE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(expr._format_name())
        return " ".join(parts), ()

    def format_create_function_statement(
        self,
        expr: "MariaDBCreateFunctionExpression",
    ) -> Tuple[str, tuple]:
        """Format ``CREATE [OR REPLACE] [IF NOT EXISTS] [AGGREGATE] FUNCTION ...``.

        Supports both the MariaDB stored-function expression and the core
        SQL/PSM ``CreateFunctionExpression`` (which uses ``function_name`` /
        ``parameters`` attributes).
        """
        if hasattr(expr, "validate"):
            expr.validate(strict=self.strict_validation)

        if hasattr(expr, "_format_name"):
            name_sql = expr._format_name()
            params = expr.params
            returns = expr.returns
            deterministic = expr.deterministic
            aggregate = expr.aggregate
            or_replace = expr.or_replace
            if_not_exists = expr.if_not_exists
            body = expr.body
        else:
            name_sql = self.format_identifier(expr.function_name)
            params = expr.parameters
            returns = expr.returns
            deterministic = False
            aggregate = False
            or_replace = expr.or_replace
            if_not_exists = False
            body = expr.body if hasattr(expr, "body") else None

        parts = ["CREATE"]
        if or_replace:
            if not self.supports_routine_or_replace():
                raise UnsupportedFeatureError(
                    self.name,
                    "CREATE OR REPLACE FUNCTION",
                    "OR REPLACE for routines requires MariaDB 10.1.3 or later."
                )
            parts.append("OR REPLACE")
        if if_not_exists:
            if not self.supports_routine_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "CREATE FUNCTION IF NOT EXISTS",
                    "IF NOT EXISTS for routines requires MariaDB 10.1.3 or later."
                )
            parts.append("IF NOT EXISTS")
        if aggregate:
            parts.append("AGGREGATE")
        parts.append("FUNCTION")
        parts.append(name_sql)

        if hasattr(expr, "_format_name"):
            param_strs = [_format_param(self, p) for p in params]
        else:
            param_strs = []
            for p in params:
                name = p.get("name", "")
                param_type = p.get("type", "")
                if name and param_type:
                    param_strs.append(
                        f"{self.format_identifier(name)} {param_type}"
                    )
                elif param_type:
                    param_strs.append(param_type)
        parts.append(f"({', '.join(param_strs)})")

        if returns:
            parts.append(f"RETURNS {returns}")
        if deterministic:
            parts.append("DETERMINISTIC")
        if body:
            parts.append(body)
        return " ".join(parts), ()

    def format_drop_function_statement(
        self,
        expr: "MariaDBDropFunctionExpression",
    ) -> Tuple[str, tuple]:
        """Format ``DROP FUNCTION [IF EXISTS] name`` (stored / aggregate function).

        Supports both the MariaDB stored-function expression and the core
        SQL/PSM ``DropFunctionExpression`` (which uses ``function_name`` /
        ``parameters`` attributes).
        """
        if hasattr(expr, "validate"):
            expr.validate(strict=self.strict_validation)
        parts = ["DROP FUNCTION"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        if hasattr(expr, "_format_name"):
            parts.append(expr._format_name())
        else:
            parts.append(self.format_identifier(expr.function_name))
        return " ".join(parts), ()

    def format_call_statement(
        self,
        expr: "MariaDBCallExpression",
    ) -> Tuple[str, tuple]:
        """Format ``CALL name([args])``."""
        expr.validate(strict=self.strict_validation)
        params = []
        arg_parts = []
        for arg in expr.args:
            if hasattr(arg, "to_sql"):
                sql, p = arg.to_sql()
                arg_parts.append(sql)
                params.extend(p)
            elif arg is None:
                arg_parts.append("NULL")
            else:
                arg_parts.append(self.get_parameter_placeholder())
                params.append(arg)
        call_name = expr.name
        if isinstance(call_name, tuple):
            schema, name = call_name
            call_name = (
                f"{self.format_identifier(schema)}.{self.format_identifier(name)}"
            )
        else:
            call_name = self.format_identifier(call_name)
        parts = ["CALL", call_name, f"({', '.join(arg_parts)})"]
        return " ".join(parts), tuple(params)
