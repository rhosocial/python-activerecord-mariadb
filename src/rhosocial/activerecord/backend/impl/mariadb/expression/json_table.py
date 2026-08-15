# src/rhosocial/activerecord/backend/impl/mariadb/expression/json_table.py
"""
MariaDB-specific JSON_TABLE expression.

This module provides MariaDBJSONTableExpression, JSONTableColumn, and NestedPath
for MariaDB's JSON_TABLE functionality.
"""

from dataclasses import dataclass
from typing import Any, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


@dataclass
class JSONTableColumn:
    """Column definition for JSON_TABLE.

    Attributes:
        name: Column name
        type: SQL data type (e.g., 'VARCHAR(255)', 'INT')
        path: JSON path expression for the column value
        ordinality: If True, use FOR ORDINALITY (row number)
        exists: If True, use EXISTS (boolean for path existence)
        error_handling: Error handling mode ('NULL', 'ERROR', 'DEFAULT')
        default_value: Default value when error handling is 'DEFAULT'
    """
    name: str
    type: Optional[str] = None
    path: Optional[str] = None
    ordinality: bool = False
    exists: bool = False
    error_handling: Optional[str] = None  # 'NULL', 'ERROR', 'DEFAULT'
    default_value: Optional[Any] = None


@dataclass
class NestedPath:
    """NESTED PATH definition for JSON_TABLE.

    Attributes:
        path: JSON path expression for nested data
        columns: List of column definitions within this nested path
        alias: Optional alias for the nested table
    """
    path: str
    columns: List['JSONTableColumn']
    alias: Optional[str] = None


class MariaDBJSONTableExpression(BaseExpression):
    """MariaDB JSON_TABLE expression.

    Generates JSON_TABLE function for converting JSON data to relational format.
    Supported in MariaDB 10.6+.

    Attributes:
        json_doc: JSON document string or expression
        path: JSON path expression for the root array/object
        columns: List of column definitions
        nested_paths: Optional list of NESTED PATH definitions
        alias: Table alias
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_doc: str,
        path: str,
        columns: List[JSONTableColumn],
        nested_paths: Optional[List[NestedPath]] = None,
        alias: Optional[str] = None
    ):
        """Initialize JSON_TABLE expression.

        Args:
            dialect: SQL dialect
            json_doc: JSON document string or expression
            path: JSON path expression for the root
            columns: List of column definitions
            nested_paths: Optional list of NESTED PATH definitions
            alias: Table alias
        """
        super().__init__(dialect)
        self.json_doc = json_doc
        self.path = path
        self.columns = columns
        self.nested_paths = nested_paths or []
        self.alias = alias

    def validate(self, strict: bool = True) -> None:
        """Validate expression parameters.

        Args:
            strict: Enable strict validation

        Raises:
            TypeError: If parameters have wrong types
            ValueError: If column definitions are invalid
        """
        if not strict:
            return

        if not isinstance(self.json_doc, str):
            raise TypeError(f"json_doc must be str, got {type(self.json_doc)}")

        if not isinstance(self.path, str):
            raise TypeError(f"path must be str, got {type(self.path)}")

        if not isinstance(self.columns, list):
            raise TypeError(f"columns must be list, got {type(self.columns)}")

        for col in self.columns:
            if not isinstance(col, JSONTableColumn):
                raise TypeError(f"columns must contain JSONTableColumn, got {type(col)}")

        for nested in self.nested_paths:
            if not isinstance(nested, NestedPath):
                raise TypeError(f"nested_paths must contain NestedPath, got {type(nested)}")

    def to_sql(self):
        """Generate SQL by delegating to dialect's format method.

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return self.dialect.format_json_table_expression(self)