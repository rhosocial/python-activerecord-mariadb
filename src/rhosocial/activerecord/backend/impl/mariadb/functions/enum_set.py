# src/rhosocial/activerecord/backend/impl/mariadb/functions/enum_set.py
"""
MariaDB Enum and SET type function factories.

Functions: find_in_set, elt, field

Every argument except :func:`find_in_set`'s searched value is an expression:
pass a ``Column`` to read a column and a ``Literal`` to write a value.  Those
arguments used to be accepted as bare strings, and a bare string became a
column reference -- so ``ELT(1, "a", "b", "c")`` did not choose "a" but read a
column called ``a``, and returned its contents when such a column happened to
exist.
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MariaDBDialect


def find_in_set(
    dialect: "MariaDBDialect",
    value: str,
    set_column: "bases.BaseExpression",
) -> "core.FunctionCall":
    """Creates a FIND_IN_SET function call.

    Finds a value within a SET column.

    Args:
        dialect: The MariaDB dialect instance
        value: The value to find; always a string value, never a column
        set_column: Expression for the SET column to search

    Returns:
        A FunctionCall instance for FIND_IN_SET

    Version: All MariaDB versions
    """
    return core.FunctionCall(
        dialect, "FIND_IN_SET", core.Literal(dialect, value), set_column,
    )


def elt(
    dialect: "MariaDBDialect",
    index: "bases.BaseExpression",
    *choices: "bases.BaseExpression",
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
        - elt(dialect, lit(1), lit("a"), lit("b"), lit("c"))
          -> ELT(?, ?, ?, ?) returns 'a'

    Version: All MariaDB versions
    """
    if not choices:
        return core.FunctionCall(dialect, "ELT")

    return core.FunctionCall(dialect, "ELT", index, *choices)


def field(
    dialect: "MariaDBDialect",
    value: "bases.BaseExpression",
    *values: "bases.BaseExpression",
) -> "core.FunctionCall":
    """Creates a FIELD function call.

    Returns the index of the first argument that matches the second argument.

    FIELD(str, str1, str2, ...) returns the position of str in str1, str2, ...
    Returns 0 if str is not found.

    Args:
        dialect: The MariaDB dialect instance
        value: Expression for the value to search for
        *values: Expressions for the values to search within

    Returns:
        A FunctionCall instance for FIELD

    Example:
        - field(dialect, lit("b"), lit("a"), lit("b"), lit("c"))
          -> FIELD(?, ?, ?, ?) returns 2

    Version: All MariaDB versions
    """
    if not values:
        return core.FunctionCall(dialect, "FIELD", value)

    return core.FunctionCall(dialect, "FIELD", value, *values)


__all__ = [
    "find_in_set",
    "elt",
    "field",
]
