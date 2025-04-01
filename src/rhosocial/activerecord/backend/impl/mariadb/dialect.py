import uuid
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Any, Dict, Tuple, Set, Union

from .types import MARIADB_TYPE_MAPPINGS
from ...dialect import (
    TypeMapper, ValueMapper, DatabaseType, SQLBuilder,
    SQLExpressionBase, SQLDialectBase, ReturningClauseHandler, ExplainOptions, ExplainType, ExplainFormat,
    AggregateHandler, JsonOperationHandler
)
from ...errors import TypeConversionError, ReturningNotSupportedError, WindowFunctionNotSupportedError, \
    GroupingSetNotSupportedError, JsonOperationNotSupportedError
from ...helpers import (
    safe_json_dumps, parse_datetime, convert_datetime,
    array_converter, safe_json_loads
)
from ...typing import ConnectionConfig

# Driver type enum
class DriverType(Enum):
    MARIADB_CONNECTOR = "mariadb-connector"
    MYSQL_CONNECTOR = "mysql-connector"
    PYMYSQL = "pymysql"
    MYSQLCLIENT = "mysqlclient"

# Version boundary constants
MARIADB_10_2_0 = (10, 2, 0)   # Window function support
MARIADB_10_2_3 = (10, 2, 3)   # JSON functions available
MARIADB_10_2_7 = (10, 2, 7)   # JSON arrow operators
MARIADB_10_5_0 = (10, 5, 0)   # RETURNING clause support
MARIADB_10_6_0 = (10, 6, 0)   # FORMAT option in EXPLAIN

def _is_version_at_least(current_version, required_version):
    """Check if current version is at least the required version"""
    return current_version >= required_version

class MariaDBTypeMapper(TypeMapper):
    """MariaDB type mapper implementation"""

    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """Get MariaDB column type definition

        Args:
            db_type: Generic database type
            **params: Type parameters (length, precision, etc.)

        Returns:
            str: MariaDB column type definition

        Raises:
            ValueError: If type is not supported
        """
        if db_type not in MARIADB_TYPE_MAPPINGS:
            raise ValueError(f"Unsupported type: {db_type}")

        mapping = MARIADB_TYPE_MAPPINGS[db_type]
        if mapping.format_func:
            return mapping.format_func(mapping.db_type, params)
        return mapping.db_type

    def get_placeholder(self, db_type: Optional[DatabaseType] = None) -> str:
        """Get parameter placeholder

        Note: MariaDB uses ? for all parameter types
        """
        return "?"


class MariaDBValueMapper(ValueMapper):
    """MariaDB value mapper implementation"""

    def __init__(self, config: ConnectionConfig):
        self.config = config
        # Define basic type converters
        self._base_converters = {
            int: int,
            float: float,
            Decimal: str,
            bool: lambda x: 1 if x else 0,
            uuid.UUID: str,
            date: lambda x: convert_datetime(x, format="%Y-%m-%d"),
            time: lambda x: convert_datetime(x, format="%H:%M:%S"),
            datetime: lambda x: convert_datetime(x, timezone=self.config.timezone),
            dict: safe_json_dumps,
            list: array_converter,
            tuple: array_converter,
        }

        # Define database type converters
        self._db_type_converters = {
            DatabaseType.BOOLEAN: lambda v: 1 if v else 0,
            DatabaseType.DATE: lambda v: convert_datetime(v, format="%Y-%m-%d"),
            DatabaseType.TIME: lambda v: convert_datetime(v, format="%H:%M:%S"),
            DatabaseType.DATETIME: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.TIMESTAMP: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.JSON: safe_json_dumps,
            DatabaseType.ARRAY: array_converter,
            DatabaseType.UUID: str,
            DatabaseType.DECIMAL: str,
        }

        # Define Python type conversions after database read
        self._from_python_converters = {
            DatabaseType.BOOLEAN: {
                int: bool,
                str: lambda v: v.lower() in ('true', '1', 'yes', 'on'),
                bool: lambda v: v,
            },
            DatabaseType.DATE: {
                str: lambda v: v,
                datetime: lambda v: v.date(),
                date: lambda v: v,
            },
            DatabaseType.TIME: {
                str: lambda v: v,
                datetime: lambda v: v.time(),
                time: lambda v: v,
            },
            DatabaseType.DATETIME: {
                str: lambda v: parse_datetime(v),
                int: lambda v: datetime.fromtimestamp(v),
                float: lambda v: datetime.fromtimestamp(v),
                datetime: lambda v: v,
            },
            DatabaseType.TIMESTAMP: {
                str: lambda v: parse_datetime(v),
                int: lambda v: datetime.fromtimestamp(v),
                float: lambda v: datetime.fromtimestamp(v),
                datetime: lambda v: v,
            },
            DatabaseType.JSON: {
                str: safe_json_loads,
                dict: lambda v: v,
                list: lambda v: v,
            },
            DatabaseType.ARRAY: {
                str: safe_json_loads,
                list: lambda v: v,
                tuple: list,
            },
            DatabaseType.UUID: {
                str: uuid.UUID,
                uuid.UUID: lambda v: v,
            },
            DatabaseType.DECIMAL: {
                str: Decimal,
                int: Decimal,
                float: Decimal,
                Decimal: lambda v: v,
            },
            DatabaseType.INTEGER: {
                str: int,
                float: int,
                bool: int,
                int: lambda v: v,
            },
            DatabaseType.FLOAT: {
                str: float,
                int: float,
                float: lambda v: v,
            },
            DatabaseType.TEXT: {
                str: lambda v: v,
                int: str,
                float: str,
                bool: str,
                datetime: str,
                date: str,
                time: str,
                uuid.UUID: str,
                Decimal: str,
            },
            DatabaseType.BLOB: {
                str: lambda v: v.encode(),
                bytes: lambda v: v,
                bytearray: bytes,
            }
        }

    def to_database(self, value: Any, db_type: Optional[DatabaseType] = None) -> Any:
        """Convert Python value to MariaDB storage value

        Args:
            value: Python value
            db_type: Target database type

        Returns:
            Any: Converted value suitable for MariaDB

        Raises:
            TypeConversionError: If type conversion fails
        """
        if value is None:
            return None

        try:
            # First try basic type conversion
            if db_type is None:
                value_type = type(value)
                if value_type in self._base_converters:
                    return self._base_converters[value_type](value)

            # Then try database type conversion
            if db_type in self._db_type_converters:
                return self._db_type_converters[db_type](value)

            # Special handling for numeric types
            if db_type in (DatabaseType.TINYINT, DatabaseType.SMALLINT,
                           DatabaseType.INTEGER, DatabaseType.BIGINT):
                return int(value)
            if db_type in (DatabaseType.FLOAT, DatabaseType.DOUBLE):
                return float(value)

            # Default to original value
            return value

        except Exception as e:
            raise TypeConversionError(
                f"Failed to convert {type(value)} to {db_type}: {str(e)}"
            )

    def from_database(self, value: Any, db_type: DatabaseType) -> Any:
        """Convert MariaDB storage value to Python value

        Args:
            value: MariaDB storage value
            db_type: Source database type

        Returns:
            Any: Converted Python value

        Raises:
            TypeConversionError: If type conversion fails
        """
        if value is None:
            return None

        try:
            # Get current Python type
            current_type = type(value)

            # Get converter mapping for target type
            type_converters = self._from_python_converters.get(db_type)
            if type_converters:
                # Find converter for current Python type
                converter = type_converters.get(current_type)
                if converter:
                    return converter(value)

                # If no direct converter, try indirect conversion via string
                if current_type != str and str in type_converters:
                    return type_converters[str](str(value))

            # Return original value if no converter found
            return value

        except Exception as e:
            raise TypeConversionError(
                f"Failed to convert MariaDB value {value} ({type(value)}) to {db_type}: {str(e)}"
            )


class MariaDBExpression(SQLExpressionBase):
    """MariaDB expression implementation"""

    def format(self, dialect: SQLDialectBase) -> str:
        """Format MariaDB expression"""
        return self.expression


class MariaDBReturningHandler(ReturningClauseHandler):
    """MariaDB RETURNING clause handler implementation"""

    def __init__(self, version: tuple):
        """Initialize MariaDB RETURNING handler

        Args:
            version: MariaDB version tuple
        """
        self._version = version

    @property
    def is_supported(self) -> bool:
        """Check if RETURNING clause is supported

        Note: MariaDB 10.5+ supports RETURNING
        """
        return _is_version_at_least(self._version, MARIADB_10_5_0)

    def format_clause(self, columns: Optional[List[str]] = None) -> str:
        """Format RETURNING clause

        Args:
            columns: Column names to return. None means all columns.

        Returns:
            str: Formatted RETURNING clause

        Raises:
            ReturningNotSupportedError: If RETURNING not supported
        """
        if not self.is_supported:
            raise ReturningNotSupportedError(
                "MariaDB version does not support RETURNING. Version 10.5 or higher is required."
            )

        if not columns:
            return "RETURNING *"

        # Validate and escape each column name
        safe_columns = [self._validate_column_name(col) for col in columns]
        return f"RETURNING {', '.join(safe_columns)}"

    def _validate_column_name(self, column: str) -> str:
        """Validate and escape column name

        Args:
            column: Column name to validate

        Returns:
            str: Escaped column name

        Raises:
            ValueError: If column name is invalid
        """
        # Remove any quotes first
        clean_name = column.strip('`')

        # Basic validation
        if not clean_name or clean_name.isspace():
            raise ValueError("Empty column name")

        # Check for common SQL injection patterns
        dangerous_patterns = [';', '--', 'union', 'select', 'drop', 'delete', 'update']
        lower_name = clean_name.lower()
        if any(pattern in lower_name for pattern in dangerous_patterns):
            raise ValueError(f"Invalid column name: {column}")

        # If name contains special chars, wrap in backticks
        if ' ' in clean_name or '.' in clean_name or '`' in clean_name:
            return f"`{clean_name}`"

        return clean_name


class MariaDBJsonHandler(JsonOperationHandler):
    """MariaDB-specific implementation of JSON operations."""

    def __init__(self, version: tuple):
        """Initialize handler with MariaDB version info.

        Args:
            version: MariaDB version as (major, minor, patch) tuple
        """
        self._version = version

        # Cache capability detection results
        self._json_supported = None
        self._arrows_supported = None
        self._function_support = {}

    @property
    def supports_json_operations(self) -> bool:
        """Check if MariaDB version supports JSON operations.

        MariaDB supports JSON operations from version 10.2.3

        Returns:
            bool: True if JSON operations are supported
        """
        if self._json_supported is None:
            self._json_supported = _is_version_at_least(self._version, MARIADB_10_2_3)
        return self._json_supported

    @property
    def supports_json_arrows(self) -> bool:
        """Check if MariaDB version supports -> and ->> operators.

        MariaDB added -> and ->> in version 10.2.7

        Returns:
            bool: True if JSON arrow operators are supported
        """
        if self._arrows_supported is None:
            self._arrows_supported = _is_version_at_least(self._version, MARIADB_10_2_7)
        return self._arrows_supported

    def format_json_operation(self,
                              column: Union[str, Any],
                              path: Optional[str] = None,
                              operation: str = "extract",
                              value: Any = None,
                              alias: Optional[str] = None) -> str:
        """Format JSON operation according to MariaDB syntax.

        This method converts abstract JSON operations into MariaDB-specific syntax,
        handling version differences and using alternatives for unsupported functions.

        Args:
            column: JSON column name or expression
            path: JSON path (e.g. '$.name')
            operation: Operation type (extract, text, contains, exists, etc.)
            value: Value for operations that need it (contains, insert, etc.)
            alias: Optional alias for the result

        Returns:
            str: Formatted MariaDB JSON operation

        Raises:
            JsonOperationNotSupportedError: If JSON operations not supported by MariaDB version
        """
        if not self.supports_json_operations:
            raise JsonOperationNotSupportedError(
                f"JSON operations are not supported in MariaDB {'.'.join(map(str, self._version))}"
            )

        # Handle column formatting
        col = str(column)

        # Default path handling
        if not path:
            path = "$"  # Root path if none provided
        elif not path.startswith('$'):
            path = f"$.{path}"  # Auto-prefix with root if not already

        # Use shorthand operators if available for extract operations
        if self.supports_json_arrows:
            if operation == "extract":
                expr = f"{col}->{path}"
                return f"{expr} as {alias}" if alias else expr
            elif operation == "text":
                expr = f"{col}->>{path}"
                return f"{expr} as {alias}" if alias else expr

        # Function-based approach
        if operation == "extract":
            expr = f"JSON_EXTRACT({col}, '{path}')"

        elif operation == "text":
            if _is_version_at_least(self._version, MARIADB_10_2_7):
                expr = f"JSON_UNQUOTE(JSON_EXTRACT({col}, '{path}'))"
            else:
                # Fallback for older versions
                expr = f"CAST(JSON_EXTRACT({col}, '{path}') AS CHAR)"

        elif operation == "contains":
            # Check if path contains value
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                expr = f"JSON_CONTAINS({col}, '{json_value}', '{path}')"
            elif isinstance(value, str):
                expr = f"JSON_CONTAINS({col}, '\"{value}\"', '{path}')"
            else:
                # For numeric/boolean comparison
                expr = f"JSON_CONTAINS({col}, '{value}', '{path}')"

        elif operation == "exists":
            expr = f"JSON_CONTAINS_PATH({col}, 'one', '{path}')"

        elif operation == "type":
            expr = f"JSON_TYPE(JSON_EXTRACT({col}, '{path}'))"

        elif operation == "remove":
            expr = f"JSON_REMOVE({col}, '{path}')"

        elif operation == "insert":
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                expr = f"JSON_INSERT({col}, '{path}', CAST('{json_value}' AS JSON))"
            elif isinstance(value, str):
                expr = f"JSON_INSERT({col}, '{path}', '\"{value}\"')"
            else:
                expr = f"JSON_INSERT({col}, '{path}', {value})"

        elif operation == "replace":
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                expr = f"JSON_REPLACE({col}, '{path}', CAST('{json_value}' AS JSON))"
            elif isinstance(value, str):
                expr = f"JSON_REPLACE({col}, '{path}', '\"{value}\"')"
            else:
                expr = f"JSON_REPLACE({col}, '{path}', {value})"

        elif operation == "set":
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                expr = f"JSON_SET({col}, '{path}', CAST('{json_value}' AS JSON))"
            elif isinstance(value, str):
                expr = f"JSON_SET({col}, '{path}', '\"{value}\"')"
            else:
                expr = f"JSON_SET({col}, '{path}', {value})"

        elif operation == "array_length":
            expr = f"JSON_LENGTH(JSON_EXTRACT({col}, '{path}'))"

        elif operation == "keys":
            expr = f"JSON_KEYS(JSON_EXTRACT({col}, '{path}'))"

        else:
            # Default to extract if operation not recognized
            expr = f"JSON_EXTRACT({col}, '{path}')"

        if alias:
            return f"{expr} as {alias}"
        return expr

    def supports_json_function(self, function_name: str) -> bool:
        """Check if specific JSON function is supported in this MariaDB version.

        Args:
            function_name: Name of JSON function to check (e.g., "json_extract")

        Returns:
            bool: True if function is supported
        """
        # Cache results for performance
        if function_name in self._function_support:
            return self._function_support[function_name]

        # All functions require JSON support
        if not self.supports_json_operations:
            self._function_support[function_name] = False
            return False

        # Define version requirements for each function
        function_versions = {
            # Core JSON functions available since 10.2.3
            "json_extract": MARIADB_10_2_3,
            "json_insert": MARIADB_10_2_3,
            "json_replace": MARIADB_10_2_3,
            "json_set": MARIADB_10_2_3,
            "json_remove": MARIADB_10_2_3,
            "json_type": MARIADB_10_2_3,
            "json_valid": MARIADB_10_2_3,
            "json_quote": MARIADB_10_2_3,
            "json_contains": MARIADB_10_2_3,
            "json_contains_path": MARIADB_10_2_3,
            "json_array": MARIADB_10_2_3,
            "json_object": MARIADB_10_2_3,
            "json_array_length": MARIADB_10_2_3,
            "json_array_append": MARIADB_10_2_3,
            "json_depth": MARIADB_10_2_3,
            "json_keys": MARIADB_10_2_3,
            "json_length": MARIADB_10_2_3,
            "json_merge": MARIADB_10_2_3,
            "json_merge_patch": MARIADB_10_2_3,
            "json_search": MARIADB_10_2_3,
            "json_unquote": MARIADB_10_2_3,

            # Arrow operators
            "->": MARIADB_10_2_7,
            "->>": MARIADB_10_2_7
        }

        # Check if function is supported based on version
        required_version = function_versions.get(function_name.lower())
        if required_version:
            is_supported = _is_version_at_least(self._version, required_version)
        else:
            # Unknown function, assume not supported
            is_supported = False

        # Cache result
        self._function_support[function_name] = is_supported
        return is_supported


class MariaDBAggregateHandler(AggregateHandler):
    """MariaDB-specific aggregate functionality handler."""

    def __init__(self, version: tuple):
        """Initialize with MariaDB version.

        Args:
            version: MariaDB version tuple (major, minor, patch)
        """
        super().__init__(version)
        self._window_support_cache = None
        self._json_support_cache = None
        self._grouping_support_cache = None

    @property
    def supports_window_functions(self) -> bool:
        """Check if MariaDB supports window functions.

        MariaDB supports window functions from version 10.2.0
        """
        if self._window_support_cache is None:
            self._window_support_cache = _is_version_at_least(self._version, MARIADB_10_2_0)
        return self._window_support_cache

    @property
    def supports_json_operations(self) -> bool:
        """Check if MariaDB supports JSON operations.

        MariaDB supports JSON operations across all modern versions,
        with more advanced support from 10.2.3
        """
        if self._json_support_cache is None:
            self._json_support_cache = _is_version_at_least(self._version, MARIADB_10_2_3)
        return self._json_support_cache

    @property
    def supports_advanced_grouping(self) -> bool:
        """Check if MariaDB supports advanced grouping.

        MariaDB supports ROLLUP but not CUBE or GROUPING SETS.
        """
        if self._grouping_support_cache is None:
            # MariaDB has supported WITH ROLLUP since very early versions
            self._grouping_support_cache = True
        return self._grouping_support_cache

    def format_window_function(self,
                               expr: str,
                               partition_by: Optional[List[str]] = None,
                               order_by: Optional[List[str]] = None,
                               frame_type: Optional[str] = None,
                               frame_start: Optional[str] = None,
                               frame_end: Optional[str] = None,
                               exclude_option: Optional[str] = None) -> str:
        """Format window function SQL for MariaDB.

        Args:
            expr: Base expression for window function
            partition_by: PARTITION BY columns
            order_by: ORDER BY columns
            frame_type: Window frame type (ROWS/RANGE only, GROUPS not supported)
            frame_start: Frame start specification
            frame_end: Frame end specification
            exclude_option: Frame exclusion option (not supported in MariaDB)

        Returns:
            str: Formatted window function SQL

        Raises:
            WindowFunctionNotSupportedError: If window functions not supported or using unsupported features
        """
        if not self.supports_window_functions:
            raise WindowFunctionNotSupportedError(
                f"Window functions not supported in MariaDB {'.'.join(map(str, self._version))}. "
                f"Requires MariaDB 10.2.0 or higher."
            )

        window_parts = []

        if partition_by:
            window_parts.append(f"PARTITION BY {', '.join(partition_by)}")

        if order_by:
            window_parts.append(f"ORDER BY {', '.join(order_by)}")

        # Build frame clause
        frame_clause = []
        if frame_type:
            if frame_type == "GROUPS":
                raise WindowFunctionNotSupportedError("GROUPS frame type not supported in MariaDB")

            frame_clause.append(frame_type)

            if frame_start:
                if frame_end:
                    frame_clause.append(f"BETWEEN {frame_start} AND {frame_end}")
                else:
                    frame_clause.append(frame_start)

        if frame_clause:
            window_parts.append(" ".join(frame_clause))

        if exclude_option:
            raise WindowFunctionNotSupportedError("EXCLUDE options not supported in MariaDB")

        window_clause = " ".join(window_parts)
        return f"{expr} OVER ({window_clause})"

    def format_json_operation(self,
                              column: str,
                              path: str,
                              operation: str = "extract",
                              value: Any = None) -> str:
        """Format JSON operation SQL for MariaDB.

        Args:
            column: JSON column name
            path: JSON path string
            operation: Operation type (extract, contains, exists)
            value: Value for contains operation

        Returns:
            str: Formatted JSON operation SQL

        Raises:
            JsonOperationNotSupportedError: If JSON operations not supported
            ValueError: For unsupported operations
        """
        if not self.supports_json_operations:
            raise JsonOperationNotSupportedError(
                f"JSON operations not supported in MariaDB {'.'.join(map(str, self._version))}"
            )

        # Ensure path is properly formatted
        if path and not path.startswith('$'):
            path = f"$.{path}"

        # Handle different operations
        if operation == "extract":
            return f"JSON_EXTRACT({column}, '{path}')"
        elif operation == "text":
            if _is_version_at_least(self._version, MARIADB_10_2_7):
                return f"JSON_UNQUOTE(JSON_EXTRACT({column}, '{path}'))"
            else:
                # Fallback for older versions
                return f"CAST(JSON_EXTRACT({column}, '{path}') AS CHAR)"
        elif operation == "contains":
            if value is None:
                raise ValueError("Value is required for 'contains' operation")

            # For JSON value comparison
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                return f"JSON_CONTAINS({column}, '{json_value}', '{path}')"
            elif isinstance(value, str):
                return f"JSON_CONTAINS({column}, '\"{value}\"', '{path}')"
            else:
                # For numeric/boolean comparison
                return f"JSON_CONTAINS({column}, '{value}', '{path}')"
        elif operation == "exists":
            return f"JSON_CONTAINS_PATH({column}, 'one', '{path}')"
        elif operation == "type":
            return f"JSON_TYPE(JSON_EXTRACT({column}, '{path}'))"
        elif operation == "keys":
            return f"JSON_KEYS(JSON_EXTRACT({column}, '{path}'))"
        elif operation == "length":
            return f"JSON_LENGTH(JSON_EXTRACT({column}, '{path}'))"
        elif operation == "array_length":
            return f"JSON_LENGTH(JSON_EXTRACT({column}, '{path}'))"
        elif operation == "set":
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                return f"JSON_SET({column}, '{path}', CAST('{json_value}' AS JSON))"
            elif isinstance(value, str):
                return f"JSON_SET({column}, '{path}', '\"{value}\"')"
            else:
                return f"JSON_SET({column}, '{path}', {value})"
        elif operation == "insert":
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                return f"JSON_INSERT({column}, '{path}', CAST('{json_value}' AS JSON))"
            elif isinstance(value, str):
                return f"JSON_INSERT({column}, '{path}', '\"{value}\"')"
            else:
                return f"JSON_INSERT({column}, '{path}', {value})"
        elif operation == "replace":
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                return f"JSON_REPLACE({column}, '{path}', CAST('{json_value}' AS JSON))"
            elif isinstance(value, str):
                return f"JSON_REPLACE({column}, '{path}', '\"{value}\"')"
            else:
                return f"JSON_REPLACE({column}, '{path}', {value})"
        elif operation == "remove":
            return f"JSON_REMOVE({column}, '{path}')"
        else:
            raise ValueError(f"Unsupported JSON operation: {operation}")

    def format_grouping_sets(self,
                             type_name: str,
                             columns: List[Union[str, List[str]]]) -> str:
        """Format grouping sets SQL for MariaDB.

        MariaDB only supports ROLLUP with different syntax: GROUP BY col1, col2 WITH ROLLUP

        Args:
            type_name: Grouping type (CUBE, ROLLUP, GROUPING SETS)
            columns: Columns to group by

        Raises:
            GroupingSetNotSupportedError: If grouping type not supported in MariaDB
        """
        if type_name == "ROLLUP":
            # MariaDB uses WITH ROLLUP syntax
            if isinstance(columns[0], list):
                # Flatten nested lists
                flat_columns = []
                for col_group in columns:
                    if isinstance(col_group, list):
                        flat_columns.extend(col_group)
                    else:
                        flat_columns.append(col_group)

                return f"{', '.join(flat_columns)} WITH ROLLUP"
            else:
                return f"{', '.join(columns)} WITH ROLLUP"
        elif type_name in ("CUBE", "GROUPING SETS"):
            raise GroupingSetNotSupportedError(
                f"{type_name} not supported in MariaDB. Only ROLLUP is available using WITH ROLLUP syntax."
            )
        else:
            raise GroupingSetNotSupportedError(f"Unknown grouping type: {type_name}")


class MariaDBSQLBuilder(SQLBuilder):
    """MariaDB specific SQL Builder

    Extends the base SQLBuilder to handle MariaDB's ? placeholder syntax.
    """

    def __init__(self, dialect: SQLDialectBase):
        """Initialize MariaDB SQL builder

        Args:
            dialect: MariaDB dialect instance
        """
        super().__init__(dialect)

    def build(self, sql: str, params: Optional[Union[Tuple, List, Dict]] = None) -> Tuple[str, Tuple]:
        """Build SQL statement with parameters for MariaDB

        All question mark placeholders (?) in the SQL statement are treated as parameter
        placeholders and must have corresponding parameters.

        Args:
            sql: SQL statement with ? placeholders
            params: Parameter values

        Returns:
            Tuple[str, Tuple]: (Processed SQL, Processed parameters)

        Raises:
            ValueError: If parameter count doesn't match placeholder count
        """
        if not params:
            return sql, ()

        # Convert params to tuple if needed
        if isinstance(params, (list, dict)):
            params = tuple(params)

        # First pass: collect information about parameters
        final_params = []
        expr_positions = {}  # Maps original position to expression
        param_count = 0

        for i, param in enumerate(params):
            if isinstance(param, SQLExpressionBase):
                expr_positions[i] = self.dialect.format_expression(param)
            else:
                final_params.append(param)
                param_count += 1

        # Second pass: build SQL with correct placeholders
        result = []
        current_pos = 0
        param_position = 0  # Counter for regular parameters
        placeholder_count = 0  # Total placeholder counter

        while True:
            # Find next placeholder
            placeholder_pos = sql.find('?', current_pos)
            if placeholder_pos == -1:
                # No more placeholders, add remaining SQL
                result.append(sql[current_pos:])
                break

            # Add SQL up to placeholder
            result.append(sql[current_pos:placeholder_pos])

            # Check if this position corresponds to an expression
            if placeholder_count in expr_positions:
                # Add the formatted expression
                result.append(expr_positions[placeholder_count])
            else:
                # Add a parameter placeholder
                result.append(self.dialect.get_parameter_placeholder(param_position))
                param_position += 1

            current_pos = placeholder_pos + 1
            placeholder_count += 1

        # Verify parameter count
        if placeholder_count != len(params):
            raise ValueError(
                f"Parameter count mismatch: SQL needs {placeholder_count} "
                f"parameters but {len(params)} were provided"
            )

        return ''.join(result), tuple(final_params)

class MariaDBDialect(SQLDialectBase):
    """MariaDB dialect implementation"""

    def __init__(self, config: ConnectionConfig):
        """Initialize MariaDB dialect

        Args:
            config: Database connection configuration
        """
        version = getattr(config, 'version', (10, 5, 0))
        super().__init__(version)
        if config.version:
            self._version = config.version

        if hasattr(config, 'driver_type') and config.driver_type:
            self._driver_type = config.driver_type
        else:
            self._driver_type = DriverType.MARIADB_CONNECTOR

        # Initialize handlers
        self._type_mapper = MariaDBTypeMapper()
        self._value_mapper = MariaDBValueMapper(config)
        self._returning_handler = MariaDBReturningHandler(version)
        self._aggregate_handler = MariaDBAggregateHandler(version)
        self._json_operation_handler = MariaDBJsonHandler(version)

    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Format MariaDB expression"""
        if not isinstance(expr, MariaDBExpression):
            raise ValueError(f"Unsupported expression type: {type(expr)}")
        return expr.format(self)

    def get_placeholder(self) -> str:
        """Get MariaDB parameter placeholder"""
        return self._type_mapper.get_placeholder(None)

    def format_string_literal(self, value: str) -> str:
        """Quote string literal

        MariaDB uses single quotes for string literals
        """
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    def format_identifier(self, identifier: str) -> str:
        """Quote identifier (table/column name)

        MariaDB uses backticks for identifiers
        """
        if '`' in identifier:
            escaped = identifier.replace('`', '``')
            return f"`{escaped}`"
        return f"`{identifier}`"

    def format_limit_offset(self, limit: Optional[int] = None,
                            offset: Optional[int] = None) -> str:
        """Format LIMIT and OFFSET clause

        MariaDB requires LIMIT when using OFFSET
        """
        if limit is None and offset is not None:
            return f"LIMIT 18446744073709551615 OFFSET {offset}"  # MariaDB maximum value
        elif limit is not None:
            if offset is not None:
                return f"LIMIT {limit} OFFSET {offset}"
            return f"LIMIT {limit}"
        return ""

    def get_parameter_placeholder(self, position: int) -> str:
        """Get MariaDB parameter placeholder

        MariaDB typically uses ? for all parameters regardless of position
        """
        return "?"

    def format_like_pattern(self, pattern: str) -> str:
        """Format LIKE pattern by escaping % characters

        Args:
            pattern: Original LIKE pattern

        Returns:
            str: Escaped pattern
        """
        return pattern.replace("%", "%%")

    def format_explain(self, sql: str, options: Optional[ExplainOptions] = None) -> str:
        """Format MariaDB EXPLAIN statement

        Args:
            sql: SQL to explain
            options: EXPLAIN options

        Returns:
            str: Formatted EXPLAIN statement
        """
        if not options:
            options = ExplainOptions()

        # Base EXPLAIN
        parts = ["EXPLAIN"]

        # Handle FORMAT option for MariaDB 10.6+
        if options.format != ExplainFormat.TEXT and _is_version_at_least(self._version, MARIADB_10_6_0):
            if options.format == ExplainFormat.JSON:
                parts.append("FORMAT=JSON")
            elif options.format == ExplainFormat.TREE:
                parts.append("FORMAT=TREE")

        # MariaDB doesn't support ANALYZE directly as a keyword
        # Instead use ANALYZE with EXPLAIN after MariaDB 10.1
        if options.type == ExplainType.ANALYZE:
            if _is_version_at_least(self._version, (10, 1, 0)):
                parts[0] = "EXPLAIN ANALYZE"
            else:
                major, minor, patch = self._version
                raise ValueError(
                    f"ANALYZE option not supported in MariaDB {major}.{minor}.{patch}. "
                    f"Requires version 10.1.0 or higher."
                )

        # Add the SQL to explain
        parts.append(sql)
        return " ".join(parts)

    @property
    def supported_formats(self) -> Set[ExplainFormat]:
        """Get supported EXPLAIN output formats for current MariaDB version

        Returns:
            Set[ExplainFormat]: Set of supported formats
        """
        # All versions support TEXT format
        formats = {ExplainFormat.TEXT}

        # MariaDB 10.6+ supports JSON and TREE formats
        if _is_version_at_least(self._version, MARIADB_10_6_0):
            formats.add(ExplainFormat.JSON)
            formats.add(ExplainFormat.TREE)

        return formats

    def create_expression(self, expression: str) -> MariaDBExpression:
        """Create MariaDB expression"""
        return MariaDBExpression(expression)