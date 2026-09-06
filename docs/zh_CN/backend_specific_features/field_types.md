# MariaDB 字段类型

## 概述

MariaDB 提供多种数据类型用于不同场景。

## 数据类型分类

### 数值类型

| 类型 | 大小 | 范围 |
|------|------|------|
| TINYINT | 1 字节 | -128 到 127 |
| SMALLINT | 2 字节 | -32768 到 32767 |
| MEDIUMINT | 3 字节 | -8388608 到 8388607 |
| INT | 4 字节 | -2147483648 到 2147483647 |
| BIGINT | 8 字节 | -9223372036854775808 到 9223372036854775807 |
| FLOAT | 4 字节 | 单精度 |
| DOUBLE | 8 字节 | 双精度 |
| DECIMAL | 可变 | 精确精度 |

### 字符串类型

| 类型 | 最大长度 |
|------|----------|
| CHAR | 255 字节 |
| VARCHAR | 65535 字节 |
| TINYTEXT | 255 字节 |
| TEXT | 65535 字节 |
| MEDIUMTEXT | 16777215 字节 |
| LONGTEXT | 4294967295 字节 |

### 时间类型

| 类型 | 格式 |
|------|------|
| DATE | YYYY-MM-DD |
| TIME | HH:MM:SS |
| DATETIME | YYYY-MM-DD HH:MM:SS |
| TIMESTAMP | YYYY-MM-DD HH:MM:SS |
| YEAR | YYYY |

### JSON 类型

```python
class Product(ActiveRecord):
    __table_name__ = "products"
    name: str
    attributes: dict    # JSON
```

## ENUM 和 SET 类型

```python
class Order(ActiveRecord):
    __table_name__ = "orders"
    status: str  # ENUM('pending', 'shipped', 'delivered')
```

## 另请参阅

- [类型适配器](../type_adapters/README.md) — 类型转换

💡 *AI 提示：* "MariaDB 中 VARCHAR 和 CHAR 有什么区别？"
