# MariaDB to Python Type Mapping

## Overview

The MariaDB backend is responsible for converting MariaDB database data types to Python objects, and converting Python objects back to MariaDB-recognized formats.

## Type Mapping Table

### Numeric Types

| MariaDB Type | Python Type | Description |
|--------------|-------------|-------------|
| TINYINT | int | 8-bit integer |
| SMALLINT | int | 16-bit integer |
| MEDIUMINT | int | 24-bit integer |
| INT | int | 32-bit integer |
| BIGINT | int | 64-bit integer |
| FLOAT | float | Single-precision floating point |
| DOUBLE | float | Double-precision floating point |
| DECIMAL | Decimal | Exact numeric |

### String Types

| MariaDB Type | Python Type | Description |
|--------------|-------------|-------------|
| CHAR | str | Fixed-length string |
| VARCHAR | str | Variable-length string |
| TINYTEXT | str | Up to 255 bytes |
| TEXT | str | Up to 65535 bytes |
| MEDIUMTEXT | str | Up to 16777215 bytes |
| LONGTEXT | str | Up to 4294967295 bytes |
| JSON | dict/list | JSON document (10.2.3+) |

### Date and Time Types

| MariaDB Type | Python Type | Description |
|--------------|-------------|-------------|
| DATE | date | Date |
| TIME | time | Time |
| DATETIME | datetime | Date and time |
| TIMESTAMP | datetime | Timestamp (timezone-aware in driver) |
| YEAR | int | Year |

### Binary Types

| MariaDB Type | Python Type | Description |
|--------------|-------------|-------------|
| BINARY | bytes | Fixed-length binary |
| VARBINARY | bytes | Variable-length binary |
| TINYBLOB | bytes | Up to 255 bytes |
| BLOB | bytes | Up to 65535 bytes |
| MEDIUMBLOB | bytes | Up to 16777215 bytes |
| LONGBLOB | bytes | Up to 4294967295 bytes |

### Special Types

| MariaDB Type | Python Type | Description |
|--------------|-------------|-------------|
| ENUM | str | Enumeration value |
| SET | set | Set of values |
| BIT | int | Bit field |
| BOOLEAN | bool | Boolean value (TINYINT(1)) |
| INET4 / INET6 | str | IP address |
| UUID | uuid.UUID | UUID value |

## Usage Example

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, DefaultTimestampMixin
from typing import ClassVar
from decimal import Decimal


class Product(UUIDMixin, DefaultTimestampMixin, ActiveRecord):
    name: str
    price: Decimal  # Automatically maps to DECIMAL
    description: str  # Automatically maps to TEXT
    metadata: dict  # Automatically maps to JSON (10.2.3+)

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'products'
```

## dict/list Type Handling

The `MariaDBJSONAdapter` handles Python `dict` and `list` types, storing them as native JSON (MariaDB 10.2.3+) or as a JSON string for older versions:

```python
from rhosocial.activerecord.backend.impl.mariadb.adapters import MariaDBJSONAdapter

adapter = MariaDBJSONAdapter()
data = {"name": "Tom", "tags": ["admin", "user"]}

# Both versions produce the same Python result
db_value = adapter.to_database(data, dict)  # JSON string
python_value = adapter.from_database(db_value, dict)  # Python dict
```

## See Also

- [Type Adapters Overview](README.md) — type conversion architecture
- [Field Types](../backend_specific_features/field_types.md) — MariaDB column types

💡 *AI Prompt:* "Why is DECIMAL recommended over FLOAT for storing monetary values?"
