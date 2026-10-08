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


class MariaDBRoutineMixin:
    """MariaDB stored routine (procedure / function / CALL) support."""

    def supports_drop_function_cascade(self) -> bool:
        """Whether ``DROP FUNCTION ... CASCADE`` is supported.

        Measured False on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc: every version
        rejects ``DROP FUNCTION f CASCADE`` with errno 1064, sentinel rejected.
        """
        return False

    def supports_drop_function_restrict(self) -> bool:
        """Whether ``DROP FUNCTION ... RESTRICT`` is supported.

        Measured False on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc: every version
        rejects ``DROP FUNCTION f RESTRICT`` with errno 1064, sentinel
        rejected.
        """
        return False

    def _require_routine_kind(self, label: str, value, kind: type) -> None:
        """Refuse a routine object of the wrong kind before it renders.

        The two FUNCTION formatters accept either a MariaDB or a core routine
        expression and read the slot by attribute presence (``routine`` versus
        ``function``), so the expected kind is a property of the expression
        rather than of the formatter. The kind is therefore named at the call
        site and passed in, which keeps the message true of the slot the caller
        actually read.

        Args:
            label: The ``<Class>.<slot>`` the message should point at.
            value: The object about to be rendered.
            kind: The class this call site requires.

        Raises:
            TypeError: ``value`` is not an instance of ``kind``.
        """
        if not isinstance(value, kind):
            raise TypeError(
                f"{label} must be a {kind.__name__}, got {type(value).__name__}"
            )

    def _format_routine_param(self, param) -> str:
        """Format one stored-routine parameter definition.

        A param may be a plain string (``IN name TYPE``), a tuple
        ``(mode, name, type)``, or ``(name, type)``. A parameter name is
        an identifier but never a qualified one -- it lives inside the
        routine's own signature -- so it takes the identifier formatter
        rather than the qualified-name renderer.

        This is a method rather than a module-level function because it
        formats an identifier, and only the dialect formats identifiers.
        """
        if isinstance(param, tuple):
            if len(param) == 3:
                mode, name, type_sql = param
                return f"{mode} {self.format_identifier(name)} {type_sql}"
            if len(param) == 2:
                name, type_sql = param
                return f"{self.format_identifier(name)} {type_sql}"
            raise ValueError(f"Invalid parameter definition: {param!r}")
        return str(param)

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
        """Format ``CREATE [OR REPLACE] [IF NOT EXISTS] PROCEDURE name(params) body``.

        Raises:
            TypeError: ``expr.routine`` is not a Procedure. It carries its own
                format_method, so a Function would render as a well-formed
                CREATE PROCEDURE over that function's name.
        """
        from rhosocial.activerecord.backend.expression.objects import Procedure

        if not isinstance(expr.routine, Procedure):
            raise TypeError(
                f"CreateProcedureStatement.routine must be a Procedure, "
                f"got {type(expr.routine).__name__}"
            )
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
        # The routine's own name: ``app`.`get_user`` when the object carries
        # a database, ``get_user`` when the caller did not ask for one.
        # `format_procedure_object` decides, not this statement.
        procedure_sql, _ = expr.routine.to_sql()
        parts.append(procedure_sql)

        params = ", ".join(self._format_routine_param(p) for p in expr.params)
        parts.append(f"({params})")
        if expr.body:
            parts.append(expr.body)
        return " ".join(parts), ()

    def format_drop_procedure_statement(
        self,
        expr: "MariaDBDropProcedureExpression",
    ) -> Tuple[str, tuple]:
        """Format ``DROP PROCEDURE [IF EXISTS] name``.

        Raises:
            TypeError: ``expr.routine`` is not a Procedure.
        """
        from rhosocial.activerecord.backend.expression.objects import Procedure

        if not isinstance(expr.routine, Procedure):
            raise TypeError(
                f"DropProcedureStatement.routine must be a Procedure, "
                f"got {type(expr.routine).__name__}"
            )
        expr.validate(strict=self.strict_validation)
        parts = ["DROP PROCEDURE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        procedure_sql, _ = expr.routine.to_sql()
        parts.append(procedure_sql)
        return " ".join(parts), ()

    def format_create_function_statement(
        self,
        expr: "MariaDBCreateFunctionExpression",
    ) -> Tuple[str, tuple]:
        """Format ``CREATE [OR REPLACE] [IF NOT EXISTS] [AGGREGATE] FUNCTION ...``.

        Supports both the MariaDB stored-function expression and the core
        SQL/PSM ``CreateFunctionExpression``; the two differ only in how they
        spell their parameter list and in whether they can be aggregate or
        deterministic.

        Raises:
            TypeError: The named routine is not a Function. A Procedure carries
                its own format_method and would render as a well-formed
                CREATE FUNCTION over the procedure's name.
        """
        from rhosocial.activerecord.backend.expression.objects import Function

        if hasattr(expr, "validate"):
            expr.validate(strict=self.strict_validation)

        # Both expressions name the function through a Function object, so a
        # database can be asked for on either path. What differs is the
        # parameter spelling and the two MariaDB-only modifiers.
        if hasattr(expr, "routine"):
            self._require_routine_kind(
                "CreateFunctionStatement.routine",
                expr.routine,
                Function,
            )
            function_sql, _ = expr.routine.to_sql()
            params = expr.params
            returns = expr.returns
            deterministic = expr.deterministic
            aggregate = expr.aggregate
            or_replace = expr.or_replace
            if_not_exists = expr.if_not_exists
            body = expr.body
        else:
            self._require_routine_kind(
                "CreateFunctionStatement.function",
                expr.function,
                Function,
            )
            function_sql, _ = expr.function.to_sql()
            params = expr.parameters
            returns = expr.returns
            deterministic = False
            aggregate = False
            or_replace = expr.or_replace
            if_not_exists = False
            body = expr.body

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
        parts.append(function_sql)

        if hasattr(expr, "routine"):
            param_strs = [self._format_routine_param(p) for p in params]
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
        SQL/PSM ``DropFunctionExpression``.

        Raises:
            TypeError: The named routine is not a Function.
        """
        from rhosocial.activerecord.backend.expression.objects import Function

        if hasattr(expr, "validate"):
            expr.validate(strict=self.strict_validation)
        parts = ["DROP FUNCTION"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        if hasattr(expr, "routine"):
            self._require_routine_kind(
                "DropFunctionStatement.routine",
                expr.routine,
                Function,
            )
            function_sql, _ = expr.routine.to_sql()
        else:
            self._require_routine_kind(
                "DropFunctionStatement.function",
                expr.function,
                Function,
            )
            function_sql, _ = expr.function.to_sql()
        parts.append(function_sql)
        # The DROP FUNCTION form has no dependent-object behavior on MariaDB:
        # both spellings of the cascade pair are measured rejected (errno 1064
        # on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc, sentinel rejected), so each is
        # refused by name through its own probe rather than dropped.
        if getattr(expr, "cascade", False) or getattr(expr, "restrict", False):
            if getattr(expr, "cascade", False):
                if not self.supports_drop_function_cascade():
                    raise UnsupportedFeatureError(
                        self.name,
                        "DROP FUNCTION CASCADE",
                        f"{self.name} does not support DROP FUNCTION CASCADE.",
                    )
                parts.append("CASCADE")
            else:
                if not self.supports_drop_function_restrict():
                    raise UnsupportedFeatureError(
                        self.name,
                        "DROP FUNCTION RESTRICT",
                        f"{self.name} does not support DROP FUNCTION RESTRICT.",
                    )
                parts.append("RESTRICT")
        return " ".join(parts), ()

    def format_call_statement(
        self,
        expr: "MariaDBCallExpression",
    ) -> Tuple[str, tuple]:
        """Format ``CALL name([args])``.

        Raises:
            TypeError: ``expr.procedure`` is not a Procedure.
        """
        from rhosocial.activerecord.backend.expression.objects import Procedure

        if not isinstance(expr.procedure, Procedure):
            raise TypeError(
                f"MariaDBCallExpression.procedure must be a Procedure, "
                f"got {type(expr.procedure).__name__}"
            )
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
        # ``CALL`` names a procedure, which is a routine object: the database
        # slot is part of the name, so it renders like any other qualified
        # name rather than being concatenated here.
        procedure_sql, _ = expr.procedure.to_sql()
        parts = ["CALL", procedure_sql, f"({', '.join(arg_parts)})"]
        return " ".join(parts), tuple(params)
