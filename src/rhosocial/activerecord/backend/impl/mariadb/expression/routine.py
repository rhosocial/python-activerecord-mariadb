# src/rhosocial/activerecord/backend/impl/mariadb/expression/routine.py
"""MariaDB stored routine expressions.

MariaDB supports:

    CREATE [OR REPLACE] PROCEDURE name ([params]) body
    CREATE [OR REPLACE] PROCEDURE IF NOT EXISTS name ([params]) body
    DROP PROCEDURE [IF EXISTS] name
    CALL name([args])
    CREATE [OR REPLACE] AGGREGATE FUNCTION name ([params]) RETURNS type ...
    DROP FUNCTION [IF EXISTS] name
"""

from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import (
    Function,
    Procedure,
    RoutineObject,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBRoutineExpression(BaseExpression):
    """Base class for MariaDB stored routine DDL statements.

    Attributes:
        routine: The routine this statement names, as a
            :class:`~...expression.objects.Procedure` or
            :class:`~...expression.objects.Function`. MariaDB has no
            inner schema, so a qualified routine name is
            ``catalog`.`name`` and the catalog slot is the database;
            which of the two kinds is expected is the subclass's
            :attr:`routine_kind`.
        params: Parameter definitions list (strings or ``(mode, name, type)``
            tuples).
        body: Routine body SQL text (for CREATE statements).
        or_replace: Whether to use ``CREATE OR REPLACE`` (MariaDB 10.1.3+).
        if_not_exists: Whether to use ``CREATE ... IF NOT EXISTS``
            (MariaDB 10.1.3+).
    """

    #: The object class this statement names. Subclasses that name a function
    #: narrow it, so CREATE FUNCTION holds a :class:`Function` rather than a
    #: :class:`Procedure`.
    routine_kind: type = Procedure

    def __init__(
        self,
        dialect: "SQLDialectBase",
        routine: RoutineObject,
        *,
        params: Optional[List[Any]] = None,
        body: Optional[str] = None,
        or_replace: bool = False,
        if_not_exists: bool = False,
    ):
        super().__init__(dialect)
        self.routine: RoutineObject = routine
        self.params: List[Any] = list(params or [])
        self.body: Optional[str] = body
        self.or_replace: bool = or_replace
        self.if_not_exists: bool = if_not_exists

    def validate(self, strict: bool = True) -> None:
        if not strict:
            return
        if not isinstance(self.routine, self.routine_kind):
            raise TypeError(
                f"routine must be a {self.routine_kind.__name__}, "
                f"got {type(self.routine).__name__}"
            )


class MariaDBCreateProcedureExpression(MariaDBRoutineExpression):
    """Represent ``CREATE [OR REPLACE] PROCEDURE``."""

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_create_procedure_statement(self)


class MariaDBDropProcedureExpression(MariaDBRoutineExpression):
    """Represent ``DROP PROCEDURE [IF EXISTS]``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        routine: Procedure,
        *,
        if_exists: bool = False,
    ):
        super().__init__(dialect, routine)
        self.if_exists: bool = if_exists

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_drop_procedure_statement(self)


class MariaDBCreateFunctionExpression(MariaDBRoutineExpression):
    """Represent ``CREATE [OR REPLACE] [AGGREGATE] FUNCTION`` (stored function)."""

    routine_kind = Function

    def __init__(
        self,
        dialect: "SQLDialectBase",
        routine: Function,
        *,
        returns: str,
        params: Optional[List[Any]] = None,
        body: Optional[str] = None,
        deterministic: bool = False,
        aggregate: bool = False,
        or_replace: bool = False,
        if_not_exists: bool = False,
    ):
        super().__init__(
            dialect,
            routine,
            params=params,
            body=body,
            or_replace=or_replace,
            if_not_exists=if_not_exists,
        )
        self.returns: str = returns
        self.deterministic: bool = deterministic
        self.aggregate: bool = aggregate

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_create_function_statement(self)


class MariaDBDropFunctionExpression(MariaDBRoutineExpression):
    """Represent ``DROP FUNCTION [IF EXISTS]`` (stored / aggregate function)."""

    routine_kind = Function

    def __init__(
        self,
        dialect: "SQLDialectBase",
        routine: Function,
        *,
        if_exists: bool = False,
    ):
        super().__init__(dialect, routine)
        self.if_exists: bool = if_exists

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_drop_function_statement(self)


class MariaDBCallExpression(BaseExpression):
    """Represent ``CALL procedure_name([args])``.

    Attributes:
        procedure: The procedure being called, as a
            :class:`~...expression.objects.Procedure`. The database a
            procedure lives in is a named slot on the object, so
            ``app`.`get_user`` needs no second spelling here.
        args: Positional argument list.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        procedure: Procedure,
        args: Optional[List[Any]] = None,
    ):
        super().__init__(dialect)
        self.procedure: Procedure = procedure
        self.args: List[Any] = list(args or [])

    def validate(self, strict: bool = True) -> None:
        if not strict:
            return
        if not isinstance(self.procedure, Procedure):
            raise TypeError(
                f"procedure must be a Procedure, got {type(self.procedure).__name__}"
            )

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_call_statement(self)
