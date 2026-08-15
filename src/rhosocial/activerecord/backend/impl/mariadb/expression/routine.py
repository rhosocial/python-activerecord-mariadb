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

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBRoutineExpression(BaseExpression):
    """Base class for MariaDB stored routine DDL statements.

    Attributes:
        name: Routine name (may be schema-qualified).
        params: Parameter definitions list (strings or ``(mode, name, type)``
            tuples).
        body: Routine body SQL text (for CREATE statements).
        or_replace: Whether to use ``CREATE OR REPLACE`` (MariaDB 10.1.3+).
        if_not_exists: Whether to use ``CREATE ... IF NOT EXISTS``
            (MariaDB 10.1.3+).
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: Any,
        *,
        params: Optional[List[Any]] = None,
        body: Optional[str] = None,
        or_replace: bool = False,
        if_not_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.name: Any = name
        self.params: List[Any] = list(params or [])
        self.body: Optional[str] = body
        self.or_replace: bool = or_replace
        self.if_not_exists: bool = if_not_exists
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        if not strict:
            return
        if isinstance(self.name, tuple):
            if len(self.name) != 2 or not all(isinstance(part, str) for part in self.name):
                raise ValueError(f"Invalid schema-qualified routine name: {self.name!r}")
        elif not isinstance(self.name, str):
            raise TypeError(
                f"name must be str or (schema, name) tuple, got {type(self.name)}"
            )

    def _format_name(self) -> str:
        if isinstance(self.name, tuple):
            schema, name = self.name
            return (
                f"{self.dialect.format_identifier(schema)}."
                f"{self.dialect.format_identifier(name)}"
            )
        return self.dialect.format_identifier(self.name)


class MariaDBCreateProcedureExpression(MariaDBRoutineExpression):
    """Represent ``CREATE [OR REPLACE] PROCEDURE``."""

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_create_procedure_statement(self)


class MariaDBDropProcedureExpression(MariaDBRoutineExpression):
    """Represent ``DROP PROCEDURE [IF EXISTS]``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: Any,
        *,
        if_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect, name, dialect_options=dialect_options)
        self.if_exists: bool = if_exists

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_drop_procedure_statement(self)


class MariaDBCreateFunctionExpression(MariaDBRoutineExpression):
    """Represent ``CREATE [OR REPLACE] [AGGREGATE] FUNCTION`` (stored function)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: Any,
        *,
        returns: str,
        params: Optional[List[Any]] = None,
        body: Optional[str] = None,
        deterministic: bool = False,
        aggregate: bool = False,
        or_replace: bool = False,
        if_not_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            dialect,
            name,
            params=params,
            body=body,
            or_replace=or_replace,
            if_not_exists=if_not_exists,
            dialect_options=dialect_options,
        )
        self.returns: str = returns
        self.deterministic: bool = deterministic
        self.aggregate: bool = aggregate

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_create_function_statement(self)


class MariaDBDropFunctionExpression(MariaDBRoutineExpression):
    """Represent ``DROP FUNCTION [IF EXISTS]`` (stored / aggregate function)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: Any,
        *,
        if_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect, name, dialect_options=dialect_options)
        self.if_exists: bool = if_exists

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_drop_function_statement(self)


class MariaDBCallExpression(BaseExpression):
    """Represent ``CALL procedure_name([args])``.

    Attributes:
        name: Stored procedure name (may be schema-qualified).
        args: Positional argument list.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: Any,
        args: Optional[List[Any]] = None,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.name: Any = name
        self.args: List[Any] = list(args or [])
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        if not strict:
            return
        if isinstance(self.name, tuple):
            if len(self.name) != 2 or not all(isinstance(part, str) for part in self.name):
                raise ValueError(f"Invalid schema-qualified procedure name: {self.name!r}")
        elif not isinstance(self.name, str):
            raise TypeError(
                f"name must be str or (schema, name) tuple, got {type(self.name)}"
            )

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_call_statement(self)
