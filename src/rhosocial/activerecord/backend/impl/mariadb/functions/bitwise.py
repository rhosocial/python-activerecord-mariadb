# src/rhosocial/activerecord/backend/impl/mariadb/functions/bitwise.py
"""
MariaDB Bitwise function factories.

Functions: bit_and, bit_or, bit_xor, bit_count, bit_get_bit,
           bit_shift_left, bit_shift_right

Note: MariaDB has native bitwise operators and functions similar to MySQL.

Every operand is an expression: pass a ``Column`` to read a column and a
``Literal`` to write a value.  An operand used to be accepted as a bare
string and a bare number, and which of the two it was had to be worked out
from its type at run time; the number was right, but the string could not say
which it meant, and a column named ``16`` was read as the number sixteen.
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core
from rhosocial.activerecord.backend.expression.operators import BinaryArithmeticExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MariaDBDialect


def bit_and(
    dialect: "MariaDBDialect",
    value: "bases.BaseExpression",
    *values: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """Returns the bitwise AND of values.

    Note: MariaDB's BIT_AND() is an aggregate function. For scalar bitwise AND,
    this function returns (value & values[0] & values[1] ...).

    Args:
        dialect: The MariaDB dialect instance
        value: First value expression
        *values: Additional value expressions to AND

    Returns:
        An expression representing bitwise AND

    Version: All MariaDB versions
    """
    result = value
    for v in values:
        result = BinaryArithmeticExpression(dialect, "&", result, v)
    return result


def bit_or(
    dialect: "MariaDBDialect",
    value: "bases.BaseExpression",
    *values: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """Returns the bitwise OR of values.

    Note: MariaDB's BIT_OR() is an aggregate function. For scalar bitwise OR,
    this function returns (value | values[0] | values[1] ...).

    Args:
        dialect: The MariaDB dialect instance
        value: First value expression
        *values: Additional value expressions to OR

    Returns:
        An expression representing bitwise OR

    Version: All MariaDB versions
    """
    result = value
    for v in values:
        result = BinaryArithmeticExpression(dialect, "|", result, v)
    return result


def bit_xor(
    dialect: "MariaDBDialect",
    value: "bases.BaseExpression",
    *values: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """Returns the bitwise XOR of values.

    Note: MariaDB's BIT_XOR() is an aggregate function. For scalar bitwise XOR,
    this function returns (value ^ values[0] ^ values[1] ...).

    Args:
        dialect: The MariaDB dialect instance
        value: First value expression
        *values: Additional value expressions to XOR

    Returns:
        An expression representing bitwise XOR

    Version: All MariaDB versions
    """
    result = value
    for v in values:
        result = BinaryArithmeticExpression(dialect, "^", result, v)
    return result


def bit_count(
    dialect: "MariaDBDialect",
    value: "bases.BaseExpression",
) -> "core.FunctionCall":
    """Returns the number of bits set to 1 in the binary representation.

    Args:
        dialect: The MariaDB dialect instance
        value: Expression whose bits to count

    Returns:
        A FunctionCall instance representing BIT_COUNT(expr)

    Version: MariaDB 10.0+
    """
    return core.FunctionCall(dialect, "BIT_COUNT", value)


def bit_get_bit(
    dialect: "MariaDBDialect",
    value: "bases.BaseExpression",
    bit: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """Returns the value of a specific bit (0 or 1).

    Note: MariaDB does not have a BIT_GET_BIT function in all versions.
    This is implemented as ((value >> bit) & 1).

    Args:
        dialect: The MariaDB dialect instance
        value: The expression to get the bit from
        bit: The bit position (0-indexed)

    Returns:
        An expression representing the bit value (0 or 1)

    Version: Native operators available in all MariaDB versions
    """
    shifted = BinaryArithmeticExpression(dialect, ">>", value, bit)
    return BinaryArithmeticExpression(dialect, "&", shifted, core.Literal(dialect, 1))


def bit_shift_left(
    dialect: "MariaDBDialect",
    value: "bases.BaseExpression",
    count: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """Returns the value left-shifted by count bits.

    Note: MariaDB does not have BIT_SHIFT_LEFT function in all versions.
    This is implemented using the native << operator.

    Args:
        dialect: The MariaDB dialect instance
        value: The expression to shift
        count: Expression for the number of positions to shift

    Returns:
        An expression representing the left-shifted value

    Version: Native operators available in all MariaDB versions
    """
    return BinaryArithmeticExpression(dialect, "<<", value, count)


def bit_shift_right(
    dialect: "MariaDBDialect",
    value: "bases.BaseExpression",
    count: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """Returns the value right-shifted by count bits.

    Note: MariaDB does not have BIT_SHIFT_RIGHT function in all versions.
    This is implemented using the native >> operator.

    Args:
        dialect: The MariaDB dialect instance
        value: The expression to shift
        count: Expression for the number of positions to shift

    Returns:
        An expression representing the right-shifted value

    Version: Native operators available in all MariaDB versions
    """
    return BinaryArithmeticExpression(dialect, ">>", value, count)


__all__ = [
    "bit_and",
    "bit_or",
    "bit_xor",
    "bit_count",
    "bit_get_bit",
    "bit_shift_left",
    "bit_shift_right",
]
