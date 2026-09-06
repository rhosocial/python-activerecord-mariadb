# MariaDB Field Types

## Overview

MariaDB provides various data types for different use cases.

## Data Type Categories

### Numeric Types

| Type | Size | Range |
|------|------|-------|
| TINYINT | 1 byte | -128 to 127 |
| SMALLINT | 2 bytes | -32768 to 32767 |
| MEDIUMINT | 3 bytes | -8388608 to 8388607 |
| INT | 4 bytes | -2147483648 to 2147483647 |
| BIGINT | 8 bytes | -9223372036854775808 to 9223372036854775807 |
| FLOAT | 4 bytes | Single precision |
| DOUBLE | 8 bytes | Double precision |
| DECIMAL | Variable | Exact precision |

### String Types

| Type | Max Length |
|------|------------|
| CHAR | 255 bytes |
| VARCHAR | 65535 bytes |
| TINYTEXT | 255 bytes |
| TEXT | 65535 bytes |
| MEDIUMTEXT | 16777215 bytes |
| LONGTEXT | 4294967295 bytes |

### Temporal Types

| Type | Format |
|------|--------|
| DATE | YYYY-MM-DD |
| TIME | HH:MM:SS |
| DATETIME | YYYY-MM-DD HH:MM:SS |
| TIMESTAMP | YYYY-MM-DD HH:MM:SS |
| YEAR | YYYY |

### JSON Type

```python
class Product(ActiveRecord):
    __table_name__ = "products"
    name: str
    attributes: dict    # JSON
```

## ENUM and SET Types

```python
class Order(ActiveRecord):
    __table_name__ = "orders"
    status: str  # ENUM('pending', 'shipped', 'delivered')
```

## See Also

- [Type Adapters](../type_adapters/README.md) — Type conversion

💡 *AI Prompt:* "What are the differences between VARCHAR and CHAR in MariaDB?"
