# Custom Data Types

## Overview

The MariaDB backend provides a type system for converting between Python types and MariaDB column types. You can add support for new Python types by creating custom DataType subclasses.

## Type System Architecture

The type system has two layers:

1. **Core DataType hierarchy** — base classes for type conversion
2. **Backend-specific DataType** — MariaDB-specific type handling

## Creating Custom Data Types

### Step 1: Define the DataType Subclass

```python
from rhosocial.activerecord.backend.impl.mariadb.types import MariaDBDataType

class PointDataType(MariaDBDataType):
    """Custom data type for geographic points."""

    @staticmethod
    def to_sql(value, dialect):
        """Convert Python Point to MariaDB POINT literal."""
        if value is None:
            return None
        return f"ST_GeomFromText('POINT({value.x} {value.y})')"

    @staticmethod
    def from_sql(value, dialect):
        """Convert MariaDB POINT to Python Point."""
        if value is None:
            return None
        # Parse WKT format
        coords = value.replace("POINT(", "").replace(")", "").split()
        return Point(float(coords[0]), float(coords[1]))
```

### Step 2: Register with @handles Decorator

```python
from rhosocial.activerecord.backend.impl.mariadb.types import MariaDBDataType

@MariaDBDataType.handles(Point)
class PointAdapter:
    @staticmethod
    def to_sql(value, dialect):
        return f"ST_GeomFromText('POINT({value.x} {value.y})')"

    @staticmethod
    def from_sql(value, dialect):
        coords = value.replace("POINT(", "").replace(")", "").split()
        return Point(float(coords[0]), float(coords[1]))
```

### Step 3: Use in Models

```python
from rhosocial.activerecord import Model

class Location(Model):
    __tablename__ = "locations"
    id: int
    name: str
    coordinates: Point  # Uses custom type
```

## Type Parameters

When defining custom types, consider these parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `precision` | Total digits for numeric types | `DECIMAL(10, 2)` |
| `scale` | Digits after decimal point | `DECIMAL(10, 2)` |
| `length` | Maximum length for string types | `VARCHAR(255)` |
| `unsigned` | Unsigned integer flag | `INT UNSIGNED` |

## MariaDB-Specific Types

The MariaDB backend provides these built-in types:

| MariaDB Type | Python Type | Notes |
|--------------|-------------|-------|
| `SET` | `set` | Comma-separated values |
| `ENUM` | `str` | Limited to defined values |
| `JSON` | `dict/list` | Native JSON support (10.2.3+) |
| `TINYINT(1)` | `bool` | Boolean representation |
| `GEOMETRY` | `bytes` | Spatial data |

## See Also

- [MariaDB Field Types](../backend_specific_features/field_types.md) — MariaDB-specific data types
- [Type Mapping](../type_adapters/mapping.md) — MariaDB to Python type conversion table
- [Core Custom Types Guide](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/template/customization/custom_types.md) — general customization patterns

💡 *AI Prompt:* "How do I add support for a custom Python type in MariaDB?"
