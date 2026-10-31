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

from rhosocial.activerecord.backend.expression.bases import SQLValue
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MariaDBJSONExtractExpression(AliasableMixin, ComparisonMixin, SQLValue):
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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_extract_expression"


class MariaDBJSONObjectExpression(AliasableMixin, SQLValue):
    """MariaDB JSON_OBJECT expression.

    Creates a JSON object from key-value pairs.

    Example:
        >>> expr = MariaDBJSONObjectExpression(dialect, {'name': 'Alice', 'age': 30})
        OR
        >>> expr = MariaDBJSONObjectExpression(dialect, [('name', 'Alice'), ('age', 30)])
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        data: Any = None,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        # The pairs ride one named parameter -- a mapping or an iterable of
        # two-item entries. An artifact names its parameters, and a
        # ``**kwargs`` catch-all accepts names no artifact can carry
        # (wire §4.11.4), so the extras channel the constructor once had is
        # gone rather than smuggled.
        self.data = data
        self.pairs = self._convert_to_pairs(data) if data is not None else []
        self.alias = alias

    def _convert_to_pairs(self, data: Any) -> List[tuple]:
        """Convert dict or iterable to list of key-value tuples."""
        if isinstance(data, dict):
            return [(k, v) for k, v in data.items()]
        return list(data)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_object_expression"


class MariaDBJSONArrayExpression(AliasableMixin, SQLValue):
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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_array_expression"


class MariaDBJSONContainsExpression(AliasableMixin, ComparisonMixin, SQLValue):
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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_contains_expression"


__all__ = [
    "MariaDBJSONExtractExpression",
    "MariaDBJSONObjectExpression",
    "MariaDBJSONArrayExpression",
    "MariaDBJSONContainsExpression",
]
