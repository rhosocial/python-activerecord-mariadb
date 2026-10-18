# src/rhosocial/activerecord/backend/impl/mariadb/functions/math_enhanced.py
"""
MariaDB enhanced math function factories.

Additional mathematical functions beyond the basic math module.
Includes: round, pow, power, sqrt, mod, ceil, floor, truncate, max, min, avg

Functions: round_, pow, power, sqrt, mod, ceil, floor, trunc, max_, min_, avg

Every operand is an expression: pass a ``Column`` to read a column and a
``Literal`` to write a number.  Operands used to be accepted as bare strings
and bare numbers, and a string was *parsed* to find out which: ``"3.7"`` was
read as the number 3.7 and ``"price"`` as a column.  That parse could not be
right in both directions -- a column named ``3.7`` was unreachable, and
``round_(dialect, "3.7")`` silently rounded the number rather than the column.
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core
from rhosocial.activerecord.backend.expression.functions.aggregate import (
    AvgFunction,
    MaxFunction,
    MinFunction,
)
from rhosocial.activerecord.backend.expression.functions.math import (
    CeilFunction,
    FloorFunction,
    ModuloFunction,
    PowerFunction,
    RoundFunction,
    SquareRootFunction,
    TruncateFunction,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def round_(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
    precision: int = 0,
) -> RoundFunction:
    """Creates a ROUND function node.

    Rounds a numeric value to the specified number of decimal places.

    Usage:
        - round_(dialect, Column(dialect, "price")) -> ROUND("price", 0)
        - round_(dialect, Column(dialect, "price"), 2) -> ROUND("price", 2)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to round
        precision: Number of decimal places (default 0)

    Returns:
        A RoundFunction node; the class writes the ROUND spelling and
        normalises the bare ``precision`` int into an integer value node.

    Version: All MariaDB versions
    """
    return RoundFunction(dialect, expr, precision)


def pow(
    dialect: "SQLDialectBase",
    base: "bases.BaseExpression",
    exponent: "bases.BaseExpression",
) -> PowerFunction:
    """Creates a POWER function node.

    Returns the value of base raised to the power of exponent. The node's
    class writes the ``POWER`` spelling; MariaDB accepts ``POW`` as a
    synonym of it, so this factory and :func:`power` now answer with the
    one standard node instead of two spellings of the same call.

    Usage:
        - pow(dialect, Literal(dialect, 2), Literal(dialect, 3)) -> POWER(2, 3)
        - pow(dialect, Column(dialect, "x"), Literal(dialect, 2)) -> POWER("x", 2)

    Args:
        dialect: The SQL dialect instance
        base: The base expression
        exponent: The exponent expression

    Returns:
        A PowerFunction node.

    Version: All MariaDB versions
    """
    return PowerFunction(dialect, base, exponent)


def power(
    dialect: "SQLDialectBase",
    base: "bases.BaseExpression",
    exponent: "bases.BaseExpression",
) -> PowerFunction:
    """Creates a POWER function node.

    Returns the value of base raised to the power of exponent. The same
    standard node as :func:`pow`; MariaDB spells the synonym ``POW`` and
    this backend renders the class's ``POWER``.

    Usage:
        - power(dialect, Literal(dialect, 2), Literal(dialect, 3)) -> POWER(2, 3)
        - power(dialect, Column(dialect, "x"), Column(dialect, "y")) -> POWER("x", "y")

    Args:
        dialect: The SQL dialect instance
        base: The base expression
        exponent: The exponent expression

    Returns:
        A PowerFunction node.

    Version: All MariaDB versions
    """
    return PowerFunction(dialect, base, exponent)


def sqrt(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> SquareRootFunction:
    """Creates a SQRT function node.

    Returns the square root of the argument.

    Usage:
        - sqrt(dialect, Literal(dialect, 16)) -> SQRT(16)
        - sqrt(dialect, Column(dialect, "value")) -> SQRT("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A SquareRootFunction node.

    Version: All MariaDB versions
    """
    return SquareRootFunction(dialect, expr)


def mod(
    dialect: "SQLDialectBase",
    dividend: "bases.BaseExpression",
    divisor: "bases.BaseExpression",
) -> ModuloFunction:
    """Creates a MOD function node.

    Returns the remainder of dividend divided by divisor.

    Usage:
        - mod(dialect, Literal(dialect, 10), Literal(dialect, 3)) -> MOD(10, 3)
        - mod(dialect, Column(dialect, "total"), Literal(dialect, 10)) -> MOD("total", 10)

    Args:
        dialect: The SQL dialect instance
        dividend: The dividend expression
        divisor: The divisor expression

    Returns:
        A ModuloFunction node.

    Version: All MariaDB versions
    """
    return ModuloFunction(dialect, dividend, divisor)


def ceil(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> CeilFunction:
    """Creates a CEIL function node.

    Returns the smallest integer value not less than the argument.

    Usage:
        - ceil(dialect, Literal(dialect, 3.14)) -> CEIL(3.14)
        - ceil(dialect, Column(dialect, "price")) -> CEIL("price")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A CeilFunction node.

    Version: All MariaDB versions (CEILING is also available as alias)
    """
    return CeilFunction(dialect, expr)


def floor(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> FloorFunction:
    """Creates a FLOOR function node.

    Returns the largest integer value not greater than the argument.

    Usage:
        - floor(dialect, Literal(dialect, 3.14)) -> FLOOR(3.14)
        - floor(dialect, Column(dialect, "price")) -> FLOOR("price")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FloorFunction node.

    Version: All MariaDB versions
    """
    return FloorFunction(dialect, expr)


def trunc(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
    precision: int = 0,
) -> TruncateFunction:
    """Creates a TRUNCATE function node.

    Returns the value truncated to the specified number of decimal places.

    Usage:
        - trunc(dialect, Literal(dialect, 3.14)) -> TRUNCATE(3.14, 0)
        - trunc(dialect, Literal(dialect, 3.14), 2) -> TRUNCATE(3.14, 2)
        - trunc(dialect, Column(dialect, "price"), 2) -> TRUNCATE("price", 2)

    Note:
        MariaDB uses TRUNCATE, not TRUNC (which is used by some other
        databases), and the classed node carries that spelling.

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to truncate
        precision: Number of decimal places (default 0)

    Returns:
        A TruncateFunction node; the bare ``precision`` int is normalised
        into an integer value node by the class.

    Version: All MariaDB versions
    """
    return TruncateFunction(dialect, expr, precision)


def max_(
    dialect: "SQLDialectBase",
    *args: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """Creates a GREATEST or MAX function call.

    Returns the maximum value from the arguments.

    Usage:
        - max_(dialect, lit(1), lit(5), lit(3)) -> GREATEST(1, 5, 3)
        - max_(dialect, Column("a"), Column("b")) -> GREATEST("a", "b")

    Note:
        When called with a single argument, uses MAX (aggregate).
        When called with multiple arguments, uses GREATEST (scalar).

        Only the aggregate half is a classed node: MAX is a standard
        function, so it is a ``MaxFunction``. GREATEST is a MariaDB scalar
        with no standard node of its own and stays on the generic call --
        the escape hatch.

    Args:
        dialect: The SQL dialect instance
        *args: The expressions to compare

    Returns:
        A MaxFunction node for one argument, a FunctionCall for GREATEST.

    Version: All MariaDB versions
    """
    if len(args) == 1:
        return MaxFunction(dialect, args[0])
    return core.FunctionCall(dialect, "GREATEST", *args)


def min_(
    dialect: "SQLDialectBase",
    *args: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """Creates a LEAST or MIN function call.

    Returns the minimum value from the arguments.

    Usage:
        - min_(dialect, lit(1), lit(5), lit(3)) -> LEAST(1, 5, 3)
        - min_(dialect, Column("a"), Column("b")) -> LEAST("a", "b")

    Note:
        When called with a single argument, uses MIN (aggregate).
        When called with multiple arguments, uses LEAST (scalar).

        Only the aggregate half is a classed node: MIN is a standard
        function, so it is a ``MinFunction``. LEAST is a MariaDB scalar
        with no standard node of its own and stays on the generic call --
        the escape hatch.

    Args:
        dialect: The SQL dialect instance
        *args: The expressions to compare

    Returns:
        A MinFunction node for one argument, a FunctionCall for LEAST.

    Version: All MariaDB versions
    """
    if len(args) == 1:
        return MinFunction(dialect, args[0])
    return core.FunctionCall(dialect, "LEAST", *args)


def avg(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> AvgFunction:
    """Creates an AVG function node.

    Returns the average value of the argument.

    Usage:
        - avg(dialect, Column(dialect, "price")) -> AVG("price")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        An AvgFunction node.

    Version: All MariaDB versions
    """
    return AvgFunction(dialect, expr)


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
