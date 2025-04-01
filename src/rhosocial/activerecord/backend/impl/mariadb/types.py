from typing import Dict

from ...dialect import DatabaseType, TypeMapping
from ...helpers import format_with_length, format_decimal

# MariaDB type mapping configuration
MARIADB_TYPE_MAPPINGS: Dict[DatabaseType, TypeMapping] = {
    DatabaseType.TINYINT: TypeMapping("TINYINT"),
    DatabaseType.SMALLINT: TypeMapping("SMALLINT"),
    DatabaseType.INTEGER: TypeMapping("INT"),
    DatabaseType.BIGINT: TypeMapping("BIGINT"),
    DatabaseType.FLOAT: TypeMapping("FLOAT"),
    DatabaseType.DOUBLE: TypeMapping("DOUBLE"),
    DatabaseType.DECIMAL: TypeMapping("DECIMAL", format_decimal),
    DatabaseType.CHAR: TypeMapping("CHAR", format_with_length),
    DatabaseType.VARCHAR: TypeMapping("VARCHAR", format_with_length),
    DatabaseType.TEXT: TypeMapping("TEXT"),
    DatabaseType.DATE: TypeMapping("DATE"),
    DatabaseType.TIME: TypeMapping("TIME"),
    DatabaseType.DATETIME: TypeMapping("DATETIME"),
    DatabaseType.TIMESTAMP: TypeMapping("TIMESTAMP"),
    DatabaseType.BLOB: TypeMapping("BLOB"),
    DatabaseType.BOOLEAN: TypeMapping("TINYINT(1)"),
    DatabaseType.UUID: TypeMapping("CHAR(36)"),
    DatabaseType.JSON: TypeMapping("JSON"),
    DatabaseType.ARRAY: TypeMapping("JSON"),
    DatabaseType.CUSTOM: TypeMapping("TEXT"),
}


class MariaDBTypes:
    """MariaDB specific type constants"""
    TINYTEXT = "TINYTEXT"
    MEDIUMTEXT = "MEDIUMTEXT"
    LONGTEXT = "LONGTEXT"
    TINYBLOB = "TINYBLOB"
    MEDIUMBLOB = "MEDIUMBLOB"
    LONGBLOB = "LONGBLOB"
    BINARY = "BINARY"
    VARBINARY = "VARBINARY"
    BIT = "BIT"
    ENUM = "ENUM"
    SET = "SET"
    GEOMETRY = "GEOMETRY"
    POINT = "POINT"
    LINESTRING = "LINESTRING"
    POLYGON = "POLYGON"

    # Auto increment primary key
    AUTO_INCREMENT = "INT AUTO_INCREMENT PRIMARY KEY"


class MariaDBColumnType:
    """MariaDB column type definition"""

    def __init__(self, sql_type: str, **constraints):
        """Initialize column type

        Args:
            sql_type: SQL type definition
            **constraints: Constraint conditions
        """
        self.sql_type = sql_type
        self.constraints = constraints

    def __str__(self):
        """Generate complete type definition statement"""
        sql = self.sql_type

        # Handle auto increment primary key
        if "auto_increment" in self.constraints and "primary_key" in self.constraints:
            if any(type in self.sql_type.upper() for type in ["INT", "BIGINT", "SMALLINT"]):
                return f"{self.sql_type} AUTO_INCREMENT PRIMARY KEY"

        # Handle primary key
        if "primary_key" in self.constraints:
            sql += " PRIMARY KEY"

        # Handle other constraints
        if "auto_increment" in self.constraints:
            sql += " AUTO_INCREMENT"
        if "unique" in self.constraints:
            sql += " UNIQUE"
        if "not_null" in self.constraints:
            sql += " NOT NULL"
        if "default" in self.constraints:
            sql += f" DEFAULT {self.constraints['default']}"
        if "unsigned" in self.constraints:
            sql += " UNSIGNED"
        if "character_set" in self.constraints:
            sql += f" CHARACTER SET {self.constraints['character_set']}"
        if "collate" in self.constraints:
            sql += f" COLLATE {self.constraints['collate']}"

        return sql

    @classmethod
    def get_type(cls, db_type: DatabaseType, **params) -> 'MariaDBColumnType':
        """Create MariaDB column type from generic type

        Args:
            db_type: Generic database type definition
            **params: Type parameters and constraints

        Returns:
            MariaDBColumnType: MariaDB column type instance

        Raises:
            ValueError: If type is not supported
        """
        mapping = MARIADB_TYPE_MAPPINGS.get(db_type)
        if not mapping:
            raise ValueError(f"Unsupported type: {db_type}")

        sql_type = mapping.db_type
        if mapping.format_func:
            sql_type = mapping.format_func(sql_type, params)

        constraints = {k: v for k, v in params.items()
                       if k in ['primary_key', 'auto_increment', 'unique',
                                'not_null', 'default', 'unsigned',
                                'character_set', 'collate']}

        return cls(sql_type, **constraints)