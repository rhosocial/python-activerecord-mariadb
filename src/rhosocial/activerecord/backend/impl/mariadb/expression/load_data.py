# src/rhosocial/activerecord/backend/impl/mariadb/expression/load_data.py
"""
MariaDB-specific LOAD DATA expression.

This module provides MariaDBLoadDataExpression and LoadDataOptions for
MariaDB's LOAD DATA INFILE functionality.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


@dataclass
class LoadDataOptions:
    """Options for LOAD DATA INFILE statement.

    Attributes:
        local: Use LOCAL keyword (client-side file)
        replace: Use REPLACE mode (replace existing rows on duplicate key)
        ignore: Use IGNORE mode (ignore duplicate key errors)
        character_set: Character set of the file
        fields_terminated_by: Field terminator string (default: tab)
        fields_enclosed_by: Field enclosure character
        fields_escaped_by: Escape character
        lines_starting_by: Line prefix to skip
        lines_terminated_by: Line terminator string
        ignore_lines: Number of lines to skip at start
        column_list: List of column names for mapping
        set_assignments: SET clause for column transformations
    """
    local: bool = True
    replace: bool = False
    ignore: bool = False
    character_set: Optional[str] = None
    fields_terminated_by: Optional[str] = None
    fields_enclosed_by: Optional[str] = None
    fields_escaped_by: Optional[str] = None
    lines_starting_by: Optional[str] = None
    lines_terminated_by: Optional[str] = None
    ignore_lines: Optional[int] = None
    column_list: Optional[List[str]] = None
    set_assignments: Optional[Dict[str, Any]] = None


class MariaDBLoadDataExpression(BaseExpression):
    """MariaDB LOAD DATA INFILE expression.

    Collects parameters for LOAD DATA [LOCAL] INFILE statement.
    The actual SQL formatting is done by MariaDBDialect.format_load_data_statement().

    Attributes:
        file_path: Path to the data file
        table: Target table name
        options: Load options
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        file_path: str,
        table: str,
        options: Optional[LoadDataOptions] = None
    ):
        """Initialize LOAD DATA expression.

        Args:
            dialect: SQL dialect
            file_path: Path to the data file
            table: Target table name
            options: Load options (default: LoadDataOptions())
        """
        super().__init__(dialect)
        self.file_path = file_path
        self.table = table
        self.options = options or LoadDataOptions()

    def validate(self, strict: bool = True) -> None:
        """Validate expression parameters.

        Args:
            strict: Enable strict validation (unused but required by base class)

        Raises:
            ValueError: If both replace and ignore are True
            TypeError: If parameters have wrong types
        """
        if not strict:
            return

        if not isinstance(self.file_path, str):
            raise TypeError(f"file_path must be str, got {type(self.file_path)}")

        if not isinstance(self.table, str):
            raise TypeError(f"table must be str, got {type(self.table)}")

        if not isinstance(self.options, LoadDataOptions):
            raise TypeError(f"options must be LoadDataOptions, got {type(self.options)}")

        if self.options.replace and self.options.ignore:
            raise ValueError("Cannot use both REPLACE and IGNORE in LOAD DATA")

    def to_sql(self):
        """Generate SQL by delegating to dialect's format method.

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return self.dialect.format_load_data_statement(self)