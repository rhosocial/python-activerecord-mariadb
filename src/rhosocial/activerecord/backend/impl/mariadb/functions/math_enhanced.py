# src/rhosocial/activerecord/backend/impl/mariadb/functions/math_enhanced.py
"""
MariaDB enhanced math function factories.

Additional mathematical functions beyond the basic math module.
Includes: round, pow, power, sqrt, mod, ceil, floor, truncate, max, min, avg

Functions: round_, pow, power, sqrt, mod, ceil, floor, trunc, max_, min_, avg
"""

from typing import Union, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def _convert_to_expression(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """Helper function to convert an input value to an appropriate BaseExpression.

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert

    Returns:
        A BaseExpression instance
    """
    if isinstance(expr, bases.BaseExpression):
        return expr
    elif isinstance(expr, (int, float)):
        return core.Literal(dialect, expr)
    elif isinstance(expr, str):
        try:
            return core.Literal(dialect, float(expr) if '.' in expr else int(expr))
        except ValueError:
            return core.Column(dialect, expr)
    else:
        return core.Column(dialect, expr)


def round_(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
    precision: int = 0,
) -> "core.FunctionCall":
    """Creates a ROUND function call.

    Rounds a numeric value to the specified number of decimal places.

    Usage:
        - round_(dialect, Column("price")) -> ROUND("price")
        - round_(dialect, Column("price"), 2) -> ROUND("price", 2)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to round
        precision: Number of decimal places (default 0)

    Returns:
        A FunctionCall instance representing the ROUND function

    Version: All MariaDB versions
    """
    target_expr = _convert_to_expression(dialect, expr)
    precision_expr = core.Literal(dialect, precision)
    return core.FunctionCall(dialect, "ROUND", target_expr, precision_expr)


def pow(
    dialect: "SQLDialectBase",
    base: Union[str, "bases.BaseExpression"],
    exponent: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a POW function call.

    Returns the value of base raised to the power of exponent.

    Usage:
        - pow(dialect, 2, 3) -> POW(2, 3)
        - pow(dialect, Column("x"), 2) -> POW("x", 2)

    Args:
        dialect: The SQL dialect instance
        base: The base value
        exponent: The exponent value

    Returns:
        A FunctionCall instance representing the POW function

    Version: All MariaDB versions
    """
    base_expr = _convert_to_expression(dialect, base)
    exp_expr = _convert_to_expression(dialect, exponent)
    return core.FunctionCall(dialect, "POW", base_expr, exp_expr)


def power(
    dialect: "SQLDialectBase",
    base: Union[str, "bases.BaseExpression"],
    exponent: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a POWER function call (alias for POW).

    Returns the value of base raised to the power of exponent.

    Usage:
        - power(dialect, 2, 3) -> POWER(2, 3)
        - power(dialect, Column("x"), 2) -> POWER("x", 2)

    Args:
        dialect: The SQL dialect instance
        base: The base value
        exponent: The exponent value

    Returns:
        A FunctionCall instance representing the POWER function

    Version: All MariaDB versions
    """
    base_expr = _convert_to_expression(dialect, base)
    exp_expr = _convert_to_expression(dialect, exponent)
    return core.FunctionCall(dialect, "POWER", base_expr, exp_expr)


def sqrt(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a SQRT function call.

    Returns the square root of the argument.

    Usage:
        - sqrt(dialect, 16) -> SQRT(16)
        - sqrt(dialect, Column("value")) -> SQRT("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the SQRT function

    Version: All MariaDB versions
    """
    target_expr = _convert_to_expression(dialect, expr)
    return core.FunctionCall(dialect, "SQRT", target_expr)


def mod(
    dialect: "SQLDialectBase",
    dividend: Union[str, "bases.BaseExpression"],
    divisor: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a MOD function call.

    Returns the remainder of dividend divided by divisor.

    Usage:
        - mod(dialect, 10, 3) -> MOD(10, 3)
        - mod(dialect, Column("total"), 10) -> MOD("total", 10)

    Args:
        dialect: The SQL dialect instance
        dividend: The dividend value
        divisor: The divisor value

    Returns:
        A FunctionCall instance representing the MOD function

    Version: All MariaDB versions
    """
    dividend_expr = _convert_to_expression(dialect, dividend)
    divisor_expr = _convert_to_expression(dialect, divisor)
    return core.FunctionCall(dialect, "MOD", dividend_expr, divisor_expr)


def ceil(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a CEIL function call.

    Returns the smallest integer value not less than the argument.

    Usage:
        - ceil(dialect, 3.14) -> CEIL(3.14)
        - ceil(dialect, Column("price")) -> CEIL("price")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the CEIL function

    Version: All MariaDB versions (CEILING is also available as alias)
    """
    target_expr = _convert_to_expression(dialect, expr)
    return core.FunctionCall(dialect, "CEIL", target_expr)


def floor(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a FLOOR function call.

    Returns the largest integer value not greater than the argument.

    Usage:
        - floor(dialect, 3.14) -> FLOOR(3.14)
        - floor(dialect, Column("price")) -> FLOOR("price")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the FLOOR function

    Version: All MariaDB versions
    """
    target_expr = _convert_to_expression(dialect, expr)
    return core.FunctionCall(dialect, "FLOOR", target_expr)


def trunc(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
    precision: int = 0,
) -> "core.FunctionCall":
    """Creates a TRUNCATE function call.

    Returns the value truncated to the specified number of decimal places.

    Usage:
        - trunc(dialect, 3.14) -> TRUNCATE(3.14, 0)
        - trunc(dialect, 3.14, 2) -> TRUNCATE(3.14, 2)
        - trunc(dialect, Column("price"), 2) -> TRUNCATE("price", 2)

    Note:
        MariaDB uses TRUNCATE, not TRUNC (which is used by some other databases).

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to truncate
        precision: Number of decimal places (default 0)

    Returns:
        A FunctionCall instance representing the TRUNCATE function

    Version: All MariaDB versions
    """
    target_expr = _convert_to_expression(dialect, expr)
    precision_expr = core.Literal(dialect, precision)
    return core.FunctionCall(dialect, "TRUNCATE", target_expr, precision_expr)


def max_(
    dialect: "SQLDialectBase",
    *args: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a GREATEST or MAX function call.

    Returns the maximum value from the arguments.

    Usage:
        - max_(dialect, 1, 5, 3, 9, 2) -> GREATEST(1, 5, 3, 9, 2)
        - max_(dialect, Column("a"), Column("b")) -> GREATEST("a", "b")

    Note:
        When called with a single column argument, uses MAX (aggregate).
        When called with multiple arguments, uses GREATEST (scalar).

    Args:
        dialect: The SQL dialect instance
        *args: The values to compare

    Returns:
        A FunctionCall instance representing GREATEST or MAX

    Version: All MariaDB versions
    """
    if len(args) == 1:
        arg_expr = _convert_to_expression(dialect, args[0])
        return core.FunctionCall(dialect, "MAX", arg_expr)
    arg_exprs = [_convert_to_expression(dialect, arg) for arg in args]
    return core.FunctionCall(dialect, "GREATEST", *arg_exprs)


def min_(
    dialect: "SQLDialectBase",
    *args: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a LEAST or MIN function call.

    Returns the minimum value from the arguments.

    Usage:
        - min_(dialect, 1, 5, 3, 9, 2) -> LEAST(1, 5, 3, 9, 2)
        - min_(dialect, Column("a"), Column("b")) -> LEAST("a", "b")

    Note:
        When called with a single column argument, uses MIN (aggregate).
        When called with multiple arguments, uses LEAST (scalar).

    Args:
        dialect: The SQL dialect instance
        *args: The values to compare

    Returns:
        A FunctionCall instance representing LEAST or MIN

    Version: All MariaDB versions
    """
    if len(args) == 1:
        arg_expr = _convert_to_expression(dialect, args[0])
        return core.FunctionCall(dialect, "MIN", arg_expr)
    arg_exprs = [_convert_to_expression(dialect, arg) for arg in args]
    return core.FunctionCall(dialect, "LEAST", *arg_exprs)


def avg(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates an AVG function call.

    Returns the average value of the argument.

    Usage:
        - avg(dialect, Column("price")) -> AVG("price")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the AVG function

    Version: All MariaDB versions
    """
    target_expr = _convert_to_expression(dialect, expr)
    return core.FunctionCall(dialect, "AVG", target_expr)


__all__ = [
    "round_",
    "pow",
    "power",
    "sqrt",
    "mod",
    "ceil",
    "floor",
    "trunc",
    "max_",
    "min_",
    "avg",
]