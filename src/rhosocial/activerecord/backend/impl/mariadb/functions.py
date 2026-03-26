# src/rhosocial/activerecord/backend/impl/mariadb/functions.py
"""MariaDB-specific SQL function factories.

This module provides factory functions for creating MariaDB-specific SQL
expression objects, including JSON functions, sequence functions, full-text
search functions, and SET type functions.

Usage Rules:
- All functions accept a dialect instance as the first argument
- For column references, pass Column objects or column name strings
- For literal values, pass the value directly (will be converted to Literal)
- Functions return appropriate expression objects (FunctionCall, RawSQLExpression, etc.)

Version Requirements:
- JSON functions: MariaDB 10.2.3+
- JSON arrow operators: MariaDB 10.2.7+
- Window functions: MariaDB 10.2+
- CTEs: MariaDB 10.2+
- INTERSECT/EXCEPT: MariaDB 10.3+
- SEQUENCE: MariaDB 10.3+
- RETURNING: MariaDB 10.5+
- Full-text search: All versions
"""

from typing import Union, Optional, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from rhosocial.activerecord.backend.expression import bases, core
    from .dialect import MariaDBDialect


def _convert_to_expression(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
    handle_numeric_literals: bool = True
) -> "bases.BaseExpression":
    """Helper function to convert an input value to an appropriate BaseExpression.

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert
        handle_numeric_literals: Whether to treat numeric values as literals

    Returns:
        A BaseExpression instance
    """
    from rhosocial.activerecord.backend.expression import bases, core
    if isinstance(expr, bases.BaseExpression):
        return expr
    elif handle_numeric_literals and isinstance(expr, (int, float)):
        return core.Literal(dialect, expr)
    else:
        return core.Column(dialect, expr)


def json_extract(
    dialect: "MariaDBDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    *paths: str
) -> "core.FunctionCall":
    """Creates a JSON_EXTRACT function call.

    Extracts data from a JSON document at the specified path(s).

    Usage rules:
    - To extract from a column: json_extract(dialect, Column(dialect, "json_col"), "$.name")
    - To extract from a literal: json_extract(dialect, '{"a": 1}', "$.a")
    - Multiple paths: json_extract(dialect, col, "$.name", "$.age")

    Args:
        dialect: The MariaDB dialect instance
        json_doc: JSON document (column or literal)
        path: First JSON path expression
        *paths: Additional JSON path expressions

    Returns:
        A FunctionCall instance representing JSON_EXTRACT

    Version: MariaDB 10.2.3+
    """
    from rhosocial.activerecord.backend.expression import core
    doc_expr = _convert_to_expression(dialect, json_doc)
    path_expr = core.Literal(dialect, path)
    args = [doc_expr, path_expr]
    for p in paths:
        args.append(core.Literal(dialect, p))
    return core.FunctionCall(dialect, "JSON_EXTRACT", *args)


def json_arrow(
    dialect: "MariaDBDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    unquote: bool = False
) -> "core.BinaryExpression":
    """Creates a JSON arrow operator expression (-> or ->>).

    MariaDB 10.2.7+ supports -> and ->> operators for JSON.

    Args:
        dialect: The MariaDB dialect instance
        json_doc: JSON document (column or literal)
        path: JSON path expression
        unquote: If True, use ->> (unquoted result)

    Returns:
        A BinaryExpression representing the arrow operator

    Version: MariaDB 10.2.7+
    """
    from rhosocial.activerecord.backend.expression import core, operators
    doc_expr = _convert_to_expression(dialect, json_doc)
    path_literal = core.Literal(dialect, path)

    op = operators.JsonArrowUnquotedOperator if unquote else operators.JsonArrowOperator
    return core.BinaryExpression(doc_expr, path_literal, op(dialect))


def json_unquote(
    dialect: "MariaDBDialect",
    json_val: Union[str, "bases.BaseExpression"]
) -> "core.FunctionCall":
    """Creates a JSON_UNQUOTE function call.

    Unquotes a JSON value and returns the result as a string.

    Args:
        dialect: The MariaDB dialect instance
        json_val: JSON value to unquote

    Returns:
        A FunctionCall instance representing JSON_UNQUOTE

    Version: MariaDB 10.2.3+
    """
    from rhosocial.activerecord.backend.expression import core
    val_expr = _convert_to_expression(dialect, json_val)
    return core.FunctionCall(dialect, "JSON_UNQUOTE", val_expr)


def json_object(
    dialect: "MariaDBDialect",
    *key_value_pairs: Any
) -> "core.FunctionCall":
    """Creates a JSON_OBJECT function call.

    Creates a JSON object from key-value pairs.

    Usage rules:
    - Empty object: json_object(dialect)
    - With values: json_object(dialect, "name", "John", "age", 30)

    Args:
        dialect: The MariaDB dialect instance
        *key_value_pairs: Alternating keys and values

    Returns:
        A FunctionCall instance representing JSON_OBJECT

    Version: MariaDB 10.2.3+
    """
    from rhosocial.activerecord.backend.expression import core
    if not key_value_pairs:
        return core.FunctionCall(dialect, "JSON_OBJECT")
    args = []
    for val in key_value_pairs:
        args.append(core.Literal(dialect, val))
    return core.FunctionCall(dialect, "JSON_OBJECT", *args)


def json_array(
    dialect: "MariaDBDialect",
    *values: Any
) -> "core.FunctionCall":
    """Creates a JSON_ARRAY function call.

    Creates a JSON array from values.

    Usage rules:
    - Empty array: json_array(dialect)
    - With values: json_array(dialect, 1, 2, 3)

    Args:
        dialect: The MariaDB dialect instance
        *values: Values to include in the array

    Returns:
        A FunctionCall instance representing JSON_ARRAY

    Version: MariaDB 10.2.3+
    """
    from rhosocial.activerecord.backend.expression import core
    if not values:
        return core.FunctionCall(dialect, "JSON_ARRAY")
    args = [core.Literal(dialect, v) for v in values]
    return core.FunctionCall(dialect, "JSON_ARRAY", *args)


def json_contains(
    dialect: "MariaDBDialect",
    target: Union[str, "bases.BaseExpression"],
    candidate: Any,
    path: Optional[str] = None
) -> "core.FunctionCall":
    """Creates a JSON_CONTAINS function call.

    Checks if a JSON document contains a specific value.

    Args:
        dialect: The MariaDB dialect instance
        target: Target JSON document or column
        candidate: Value to search for
        path: Optional path within the document

    Returns:
        A FunctionCall instance representing JSON_CONTAINS

    Version: MariaDB 10.2.3+
    """
    from rhosocial.activerecord.backend.expression import core
    target_expr = _convert_to_expression(dialect, target)
    candidate_expr = core.Literal(dialect, candidate)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_CONTAINS", target_expr, candidate_expr, path_expr)
    return core.FunctionCall(dialect, "JSON_CONTAINS", target_expr, candidate_expr)


def json_set(
    dialect: "MariaDBDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    value: Any,
    *path_value_pairs: Any
) -> "core.FunctionCall":
    """Creates a JSON_SET function call.

    Updates or adds data in a JSON document.

    Args:
        dialect: The MariaDB dialect instance
        json_doc: JSON document or column
        path: JSON path expression
        value: Value to set
        *path_value_pairs: Additional (path, value) pairs

    Returns:
        A FunctionCall instance representing JSON_SET

    Version: MariaDB 10.2.3+
    """
    from rhosocial.activerecord.backend.expression import core
    doc_expr = _convert_to_expression(dialect, json_doc)
    args = [doc_expr, core.Literal(dialect, path), core.Literal(dialect, value)]
    for i in range(0, len(path_value_pairs), 2):
        args.append(core.Literal(dialect, path_value_pairs[i]))
        if i + 1 < len(path_value_pairs):
            args.append(core.Literal(dialect, path_value_pairs[i + 1]))
    return core.FunctionCall(dialect, "JSON_SET", *args)


def json_remove(
    dialect: "MariaDBDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    *paths: str
) -> "core.FunctionCall":
    """Creates a JSON_REMOVE function call.

    Removes data from a JSON document.

    Args:
        dialect: The MariaDB dialect instance
        json_doc: JSON document or column
        path: JSON path to remove
        *paths: Additional paths to remove

    Returns:
        A FunctionCall instance representing JSON_REMOVE

    Version: MariaDB 10.2.3+
    """
    from rhosocial.activerecord.backend.expression import core
    doc_expr = _convert_to_expression(dialect, json_doc)
    args = [doc_expr, core.Literal(dialect, path)]
    for p in paths:
        args.append(core.Literal(dialect, p))
    return core.FunctionCall(dialect, "JSON_REMOVE", *args)


def nextval(
    dialect: "MariaDBDialect",
    sequence_name: str
) -> "core.RawSQLExpression":
    """Creates a NEXTVAL expression for sequences.

    MariaDB 10.3+ supports SEQUENCE storage engine.

    Args:
        dialect: The MariaDB dialect instance
        sequence_name: Name of the sequence

    Returns:
        A RawSQLExpression for NEXT VALUE FOR

    Version: MariaDB 10.3+
    """
    from rhosocial.activerecord.backend.expression import core
    quoted_name = dialect.format_identifier(sequence_name)
    return core.RawSQLExpression(dialect, f"NEXT VALUE FOR {quoted_name}")


def currval(
    dialect: "MariaDBDialect",
    sequence_name: str
) -> "core.RawSQLExpression":
    """Creates a CURRVAL expression for sequences.

    MariaDB 10.3+ supports SEQUENCE storage engine.

    Args:
        dialect: The MariaDB dialect instance
        sequence_name: Name of the sequence

    Returns:
        A RawSQLExpression for CURRENT VALUE FOR

    Version: MariaDB 10.3+
    """
    from rhosocial.activerecord.backend.expression import core
    quoted_name = dialect.format_identifier(sequence_name)
    return core.RawSQLExpression(dialect, f"CURRENT VALUE FOR {quoted_name}")


def match_against(
    dialect: "MariaDBDialect",
    columns: List[Union[str, "bases.BaseExpression"]],
    search_string: str,
    mode: str = 'natural_language',
    query_expansion: bool = False
) -> "core.FunctionCall":
    """Creates a MATCH ... AGAINST expression for full-text search.

    Args:
        dialect: The MariaDB dialect instance
        columns: Columns to search
        search_string: Search string
        mode: Search mode ('natural_language', 'boolean')
        query_expansion: Enable query expansion

    Returns:
        A FunctionCall instance for MATCH ... AGAINST

    Version: All MariaDB versions (with FULLTEXT index)
    """
    from rhosocial.activerecord.backend.expression import core
    col_exprs = [_convert_to_expression(dialect, col) for col in columns]

    against_args = [core.Literal(dialect, search_string)]

    if mode == 'boolean':
        against_args.append(core.RawSQLExpression(dialect, "IN BOOLEAN MODE"))
    elif query_expansion:
        against_args.append(core.RawSQLExpression(dialect, "WITH QUERY EXPANSION"))

    match_func = core.FunctionCall(dialect, "MATCH", *col_exprs)
    against_func = core.FunctionCall(dialect, "AGAINST", *against_args)

    return core.RawSQLExpression(
        dialect,
        f"{match_func.compile(dialect)} {against_func.compile(dialect)}"
    )


def find_in_set(
    dialect: "MariaDBDialect",
    value: str,
    set_column: Union[str, "bases.BaseExpression"]
) -> "core.FunctionCall":
    """Creates a FIND_IN_SET function call.

    Finds a value within a SET column.

    Args:
        dialect: The MariaDB dialect instance
        value: Value to find
        set_column: SET column name

    Returns:
        A FunctionCall instance for FIND_IN_SET
    """
    from rhosocial.activerecord.backend.expression import core
    col_expr = _convert_to_expression(dialect, set_column)
    return core.FunctionCall(dialect, "FIND_IN_SET", core.Literal(dialect, value), col_expr)


__all__ = [
    'json_extract',
    'json_arrow',
    'json_unquote',
    'json_object',
    'json_array',
    'json_contains',
    'json_set',
    'json_remove',
    'nextval',
    'currval',
    'match_against',
    'find_in_set',
]
