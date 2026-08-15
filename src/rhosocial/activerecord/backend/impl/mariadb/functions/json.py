# src/rhosocial/activerecord/backend/impl/mariadb/functions/json.py
"""
MariaDB JSON function factories.

Functions: json_extract, json_unquote, json_object, json_array, json_contains,
json_set, json_remove, json_type, json_valid, json_search
"""

from typing import Union, Optional, Any, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from .dialect import MariaDBDialect


def _convert_to_expression(
    dialect: "SQLDialectBase",
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


def json_extract(
    dialect: "MariaDBDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    *paths: str,
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
    doc_expr = _convert_to_expression(dialect, json_doc)
    path_expr = core.Literal(dialect, path)
    args = [doc_expr, path_expr]
    for p in paths:
        args.append(core.Literal(dialect, p))
    return core.FunctionCall(dialect, "JSON_EXTRACT", *args)


def json_unquote(
    dialect: "MariaDBDialect",
    json_val: Union[str, "bases.BaseExpression"],
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
    val_expr = _convert_to_expression(dialect, json_val)
    return core.FunctionCall(dialect, "JSON_UNQUOTE", val_expr)


def json_object(
    dialect: "MariaDBDialect",
    *key_value_pairs: Any,
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
    if not key_value_pairs:
        return core.FunctionCall(dialect, "JSON_OBJECT")
    args = []
    for _i, val in enumerate(key_value_pairs):
        args.append(core.Literal(dialect, val))
    return core.FunctionCall(dialect, "JSON_OBJECT", *args)


def json_array(
    dialect: "MariaDBDialect",
    *values: Any,
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
    if not values:
        return core.FunctionCall(dialect, "JSON_ARRAY")
    args = [core.Literal(dialect, v) for v in values]
    return core.FunctionCall(dialect, "JSON_ARRAY", *args)


def json_contains(
    dialect: "MariaDBDialect",
    target: Union[str, "bases.BaseExpression"],
    candidate: Any,
    path: Optional[str] = None,
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
    *path_value_pairs: Any,
) -> "core.FunctionCall":
    """Creates a JSON_SET function call.

    Inserts or updates data in a JSON document.

    Args:
        dialect: The MariaDB dialect instance
        json_doc: JSON document or column
        path: JSON path expression
        value: Value to set
        *path_value_pairs: Additional path-value pairs

    Returns:
        A FunctionCall instance representing JSON_SET

    Version: MariaDB 10.2.3+
    """
    doc_expr = _convert_to_expression(dialect, json_doc)
    args = [doc_expr, core.Literal(dialect, path), core.Literal(dialect, value)]
    for i in range(0, len(path_value_pairs), 2):
        if i + 1 < len(path_value_pairs):
            args.append(core.Literal(dialect, path_value_pairs[i]))
            args.append(core.Literal(dialect, path_value_pairs[i + 1]))
    return core.FunctionCall(dialect, "JSON_SET", *args)


def json_remove(
    dialect: "MariaDBDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    *paths: str,
) -> "core.FunctionCall":
    """Creates a JSON_REMOVE function call.

    Removes data from a JSON document.

    Args:
        dialect: The MariaDB dialect instance
        json_doc: JSON document or column
        path: First JSON path expression
        *paths: Additional JSON path expressions

    Returns:
        A FunctionCall instance representing JSON_REMOVE

    Version: MariaDB 10.2.3+
    """
    doc_expr = _convert_to_expression(dialect, json_doc)
    args = [doc_expr, core.Literal(dialect, path)]
    for p in paths:
        args.append(core.Literal(dialect, p))
    return core.FunctionCall(dialect, "JSON_REMOVE", *args)


def json_type(
    dialect: "MariaDBDialect",
    json_val: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a JSON_TYPE function call.

    Returns the type of a JSON value.

    Args:
        dialect: The MariaDB dialect instance
        json_val: JSON value to check

    Returns:
        A FunctionCall instance representing JSON_TYPE

    Version: MariaDB 10.2.3+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    return core.FunctionCall(dialect, "JSON_TYPE", val_expr)


def json_valid(
    dialect: "MariaDBDialect",
    json_val: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Creates a JSON_VALID function call.

    Validates whether a value is valid JSON.

    Args:
        dialect: The MariaDB dialect instance
        json_val: Value to validate

    Returns:
        A FunctionCall instance representing JSON_VALID

    Version: MariaDB 10.2.3+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    return core.FunctionCall(dialect, "JSON_VALID", val_expr)


def json_search(
    dialect: "MariaDBDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    search_str: str,
    path: Optional[str] = None,
    search_all: bool = False,
) -> "core.FunctionCall":
    """Creates a JSON_SEARCH function call.

    Searches for a string in a JSON document.

    Args:
        dialect: The MariaDB dialect instance
        json_doc: JSON document or column
        search_str: String to search for
        path: Optional path to search within
        search_all: If True, returns all matches; otherwise returns first match

    Returns:
        A FunctionCall instance representing JSON_SEARCH

    Version: MariaDB 10.2.3+
    """
    doc_expr = _convert_to_expression(dialect, json_doc)
    one_or_all = "all" if search_all else "one"
    one_or_all_expr = core.Literal(dialect, one_or_all)
    search_expr = core.Literal(dialect, search_str)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(
            dialect, "JSON_SEARCH", doc_expr, one_or_all_expr, search_expr,
            core.Literal(dialect, None), path_expr,
        )
    return core.FunctionCall(dialect, "JSON_SEARCH", doc_expr, one_or_all_expr, search_expr)


__all__ = [
    "json_extract",
    "json_unquote",
    "json_object",
    "json_array",
    "json_contains",
    "json_set",
    "json_remove",
    "json_type",
    "json_valid",
    "json_search",
]