# src/rhosocial/activerecord/backend/impl/mariadb/expression/json.py
"""
MariaDB-specific JSON expression functions.

This module provides expression classes for MariaDB JSON functions:
- MariaDBJSONExtractExpression
- MariaDBJSONObjectExpression
- MariaDBJSONArrayExpression
- MariaDBJSONContainsExpression
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rhosocial.activerecord.backend.expression.bases import SQLQueryAndParams, SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBJSONExtractExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MariaDB JSON_EXTRACT expression.
    
    Extracts a value from a JSON document using a path.
    
    Example:
        >>> expr = MariaDBJSONExtractExpression(dialect, 'data', '$.name')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_column: str,
        path: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_column = json_column
        self.path = path
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_json_extract(self.json_column, self.path)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


class MariaDBJSONObjectExpression(AliasableMixin, SQLValueExpression):
    """MariaDB JSON_OBJECT expression.
    
    Creates a JSON object from key-value pairs.
    
    Example:
        >>> expr = MariaDBJSONObjectExpression(dialect, {'name': 'Alice', 'age': 30})
        OR
        >>> expr = MariaDBJSONObjectExpression(dialect, ('name', 'Alice'), ('age', 30))
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        data: Any = None,
        *,
        alias: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(dialect)
        self.data = data  # keep raw for get_params() introspection
        self.kwargs: Dict[str, Any] = dict(kwargs)
        if data is not None and kwargs:
            pairs = self._convert_to_pairs(data) + self._convert_to_pairs(kwargs)
        elif data is not None:
            pairs = self._convert_to_pairs(data)
        elif kwargs:
            pairs = self._convert_to_pairs(kwargs)
        else:
            pairs = []
        self.pairs = pairs
        self.alias = alias

    def _convert_to_pairs(self, data: Any) -> List[tuple]:
        """Convert dict or iterable to list of key-value tuples."""
        if isinstance(data, dict):
            return [(k, v) for k, v in data.items()]
        return list(data)

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_json_object(self.pairs)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


class MariaDBJSONArrayExpression(AliasableMixin, SQLValueExpression):
    """MariaDB JSON_ARRAY expression.
    
    Creates a JSON array from values.
    
    Example:
        >>> expr = MariaDBJSONArrayExpression(dialect, [1, 2, 3])
        OR
        >>> expr = MariaDBJSONArrayExpression(dialect, 1, 2, 3)
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        values: Any = None,
        *args: Any,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self._raw_values = values  # keep raw for get_params() introspection
        self.args = list(args)  # keep raw for get_params() introspection
        if values is not None and args:
            self.values = [values] + list(args)
        elif values is not None:
            self.values = values if isinstance(values, list) else [values]
        elif args:
            self.values = list(args)
        else:
            self.values = []
        self.alias = alias

    def get_params(self) -> Dict[str, Any]:
        """Return the raw constructor arguments.

        The ``values`` parameter is normalized into ``self.values`` during
        construction; returning the raw form keeps the round-trip
        (serialize -> deserialize) from double-applying the positional args.
        """
        return {"values": self._raw_values, "args": self.args, "alias": self.alias}

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_json_array(self.values)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


class MariaDBJSONContainsExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MariaDB JSON_CONTAINS expression.
    
    Checks if a JSON document contains a specific value.
    
    Example:
        >>> expr = MariaDBJSONContainsExpression(dialect, 'data', 'urgent', '$.tags')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_column: str,
        value: str,
        path: Optional[str] = None,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.json_column = json_column
        self.value = value
        self.path = path
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_json_contains(
            self.json_column, self.value, self.path
        )
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


__all__ = [
    "MariaDBJSONExtractExpression",
    "MariaDBJSONObjectExpression",
    "MariaDBJSONArrayExpression",
    "MariaDBJSONContainsExpression",
]