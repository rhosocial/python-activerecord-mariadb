# src/rhosocial/activerecord/backend/impl/mariadb/functions/bitwise.py
"""
MariaDB Bitwise function factories.

Functions: bit_and, bit_or, bit_xor, bit_count, bit_get_bit,
           bit_shift_left, bit_shift_right

Note: MariaDB has native bitwise operators and functions similar to MySQL.
"""

from typing import Union, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core
from rhosocial.activerecord.backend.expression.operators import BinaryArithmeticExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from .dialect import MariaDBDialect


def _convert_to_expression(
    dialect: "SQLDialectBase",
    expr: Union[str, int, float, "bases.BaseExpression"],
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


def bit_and(
    dialect: "MariaDBDialect",
    value: Union[str, int, "bases.BaseExpression"],
    *values: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """Returns the bitwise AND of values.

    Note: MariaDB's BIT_AND() is an aggregate function. For scalar bitwise AND,
    this function returns (value & values[0] & values[1] ...).

    Args:
        dialect: The MariaDB dialect instance
        value: First value
        *values: Additional values to AND

    Returns:
        An expression representing bitwise AND

    Version: All MariaDB versions
    """
    result = _convert_to_expression(dialect, value)
    for v in values:
        v_expr = _convert_to_expression(dialect, v)
        result = BinaryArithmeticExpression(dialect, "&", result, v_expr)
    return result


def bit_or(
    dialect: "MariaDBDialect",
    value: Union[str, int, "bases.BaseExpression"],
    *values: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """Returns the bitwise OR of values.

    Note: MariaDB's BIT_OR() is an aggregate function. For scalar bitwise OR,
    this function returns (value | values[0] | values[1] ...).

    Args:
        dialect: The MariaDB dialect instance
        value: First value
        *values: Additional values to OR

    Returns:
        An expression representing bitwise OR

    Version: All MariaDB versions
    """
    result = _convert_to_expression(dialect, value)
    for v in values:
        v_expr = _convert_to_expression(dialect, v)
        result = BinaryArithmeticExpression(dialect, "|", result, v_expr)
    return result


def bit_xor(
    dialect: "MariaDBDialect",
    value: Union[str, int, "bases.BaseExpression"],
    *values: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """Returns the bitwise XOR of values.

    Note: MariaDB's BIT_XOR() is an aggregate function. For scalar bitwise XOR,
    this function returns (value ^ values[0] ^ values[1] ...).

    Args:
        dialect: The MariaDB dialect instance
        value: First value
        *values: Additional values to XOR

    Returns:
        An expression representing bitwise XOR

    Version: All MariaDB versions
    """
    result = _convert_to_expression(dialect, value)
    for v in values:
        v_expr = _convert_to_expression(dialect, v)
        result = BinaryArithmeticExpression(dialect, "^", result, v_expr)
    return result


def bit_count(
    dialect: "MariaDBDialect",
    value: Union[str, int, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Returns the number of bits set to 1 in the binary representation.

    Args:
        dialect: The MariaDB dialect instance
        value: Column or expression to count bits

    Returns:
        A FunctionCall instance representing BIT_COUNT(expr)

    Version: MariaDB 10.0+
    """
    value_expr = _convert_to_expression(dialect, value)
    return core.FunctionCall(dialect, "BIT_COUNT", value_expr)


def bit_get_bit(
    dialect: "MariaDBDialect",
    value: Union[str, int, "bases.BaseExpression"],
    bit: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """Returns the value of a specific bit (0 or 1).

    Note: MariaDB does not have a BIT_GET_BIT function in all versions.
    This is implemented as ((value >> bit) & 1).

    Args:
        dialect: The MariaDB dialect instance
        value: The value to get the bit from
        bit: The bit position (0-indexed)

    Returns:
        An expression representing the bit value (0 or 1)

    Version: Native operators available in all MariaDB versions
    """
    value_expr = _convert_to_expression(dialect, value)
    bit_expr = _convert_to_expression(dialect, bit)
    shifted = BinaryArithmeticExpression(dialect, ">>", value_expr, bit_expr)
    return BinaryArithmeticExpression(dialect, "&", shifted, core.Literal(dialect, 1))


def bit_shift_left(
    dialect: "MariaDBDialect",
    value: Union[str, int, "bases.BaseExpression"],
    count: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """Returns the value left-shifted by count bits.

    Note: MariaDB does not have BIT_SHIFT_LEFT function in all versions.
    This is implemented using the native << operator.

    Args:
        dialect: The MariaDB dialect instance
        value: The value to shift
        count: Number of positions to shift

    Returns:
        An expression representing the left-shifted value

    Version: Native operators available in all MariaDB versions
    """
    value_expr = _convert_to_expression(dialect, value)
    count_expr = _convert_to_expression(dialect, count)
    return BinaryArithmeticExpression(dialect, "<<", value_expr, count_expr)


def bit_shift_right(
    dialect: "MariaDBDialect",
    value: Union[str, int, "bases.BaseExpression"],
    count: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """Returns the value right-shifted by count bits.

    Note: MariaDB does not have BIT_SHIFT_RIGHT function in all versions.
    This is implemented using the native >> operator.

    Args:
        dialect: The MariaDB dialect instance
        value: The value to shift
        count: Number of positions to shift

    Returns:
        An expression representing the right-shifted value

    Version: Native operators available in all MariaDB versions
    """
    value_expr = _convert_to_expression(dialect, value)
    count_expr = _convert_to_expression(dialect, count)
    return BinaryArithmeticExpression(dialect, ">>", value_expr, count_expr)


__all__ = [
    "bit_and",
    "bit_or",
    "bit_xor",
    "bit_count",
    "bit_get_bit",
    "bit_shift_left",
    "bit_shift_right",
]