# src/rhosocial/activerecord/backend/impl/mariadb/functions/enum_set.py
"""
MariaDB Enum and SET type function factories.

Functions: find_in_set, elt, field
"""

from typing import Union, Any, List, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from .dialect import MariaDBDialect


def _convert_to_expression(
    dialect: "MariaDBDialect",
    expr: Union[str, "bases.BaseExpression"],
    handle_numeric_literals: bool = True,
) -> "bases.BaseExpression":
    """Helper function to convert an input value to an appropriate BaseExpression.

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert
        handle_numeric_literals: Whether to treat numeric values as literals

    Returns:
        A BaseExpression instance
    """
    if isinstance(expr, bases.BaseExpression):
        return expr
    elif handle_numeric_literals and isinstance(expr, (int, float)):
        return core.Literal(dialect, expr)
    else:
        return core.Column(dialect, expr)


def find_in_set(
    dialect: "MariaDBDialect",
    value: str,
    set_column: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a FIND_IN_SET function call.

    Finds a value within a SET column.

    Args:
        dialect: The MariaDB dialect instance
        value: Value to find
        set_column: SET column name or expression

    Returns:
        A FunctionCall instance for FIND_IN_SET

    Version: All MariaDB versions
    """
    col_expr = _convert_to_expression(dialect, set_column)
    return core.FunctionCall(dialect, "FIND_IN_SET", core.Literal(dialect, value), col_expr)


def elt(
    dialect: "MariaDBDialect",
    index: Union[int, "bases.BaseExpression"],
    *choices: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates an ELT function call.

    Returns the string at the specified index (1-based).

    ELT(N, str1, str2, ...) returns the N-th string.
    If N is 1, returns str1; if N is 2, returns str2, etc.
    Returns NULL if N is less than 1 or greater than the number of arguments.

    Args:
        dialect: The MariaDB dialect instance
        index: 1-based index into the following strings
        *choices: The strings to choose from

    Returns:
        A FunctionCall instance for ELT

    Example:
        - elt(dialect, 1, "a", "b", "c") -> ELT(1, 'a', 'b', 'c') returns 'a'
        - elt(dialect, 2, "a", "b", "c") -> ELT(2, 'a', 'b', 'c') returns 'b'

    Version: All MariaDB versions
    """
    if not choices:
        return core.FunctionCall(dialect, "ELT")

    index_expr = _convert_to_expression(dialect, index)
    choice_exprs = [_convert_to_expression(dialect, c) for c in choices]
    return core.FunctionCall(dialect, "ELT", index_expr, *choice_exprs)


def field(
    dialect: "MariaDBDialect",
    value: Union[str, "bases.BaseExpression"],
    *values: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a FIELD function call.

    Returns the index of the first argument that matches the second argument.

    FIELD(str, str1, str2, ...) returns the position of str in str1, str2, ...
    Returns 0 if str is not found.

    Args:
        dialect: The MariaDB dialect instance
        value: The value to search for
        *values: The values to search within

    Returns:
        A FunctionCall instance for FIELD

    Example:
        - field(dialect, "b", "a", "b", "c") -> FIELD('b', 'a', 'b', 'c') returns 2

    Version: All MariaDB versions
    """
    value_expr = _convert_to_expression(dialect, value)
    if not values:
        return core.FunctionCall(dialect, "FIELD", value_expr)

    value_exprs = [_convert_to_expression(dialect, v) for v in values]
    return core.FunctionCall(dialect, "FIELD", value_expr, *value_exprs)


__all__ = [
    "find_in_set",
    "elt",
    "field",
]