# MariaDB 到 Python 类型映射

## 概述

MariaDB 后端负责将 MariaDB 数据库数据类型转换为 Python 对象，并将 Python 对象转换回 MariaDB 可识别的格式。

## 类型映射表

### 数值类型

| MariaDB 类型 | Python 类型 | 描述 |
|--------------|-------------|-------------|
| TINYINT | int | 8 位整数 |
| SMALLINT | int | 16 位整数 |
| MEDIUMINT | int | 24 位整数 |
| INT | int | 32 位整数 |
| BIGINT | int | 64 位整数 |
| FLOAT | float | 单精度浮点数 |
| DOUBLE | float | 双精度浮点数 |
| DECIMAL | Decimal | 精确数值 |

### 字符串类型

| MariaDB 类型 | Python 类型 | 描述 |
|--------------|-------------|-------------|
| CHAR | str | 定长字符串 |
| VARCHAR | str | 变长字符串 |
| TINYTEXT | str | 最多 255 字节 |
| TEXT | str | 最多 65535 字节 |
| MEDIUMTEXT | str | 最多 16777215 字节 |
| LONGTEXT | str | 最多 4294967295 字节 |
| JSON | dict/list | JSON 文档（10.2.3+） |

### 日期和时间类型

| MariaDB 类型 | Python 类型 | 描述 |
|--------------|-------------|-------------|
| DATE | date | 日期 |
| TIME | time | 时间 |
| DATETIME | datetime | 日期和时间 |
| TIMESTAMP | datetime | 时间戳（驱动中时区感知） |
| YEAR | int | 年份 |

### 二进制类型

| MariaDB 类型 | Python 类型 | 描述 |
|--------------|-------------|-------------|
| BINARY | bytes | 定长二进制 |
| VARBINARY | bytes | 变长二进制 |
| TINYBLOB | bytes | 最多 255 字节 |
| BLOB | bytes | 最多 65535 字节 |
| MEDIUMBLOB | bytes | 最多 16777215 字节 |
| LONGBLOB | bytes | 最多 4294967295 字节 |

### 特殊类型

| MariaDB 类型 | Python 类型 | 描述 |
|--------------|-------------|-------------|
| ENUM | str | 枚举值 |
| SET | set | 值集合 |
| BIT | int | 位字段 |
| BOOLEAN | bool | 布尔值（TINYINT(1)） |
| INET4 / INET6 | str | IP 地址 |
| UUID | uuid.UUID | UUID 值 |

## 使用示例

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, DefaultTimestampMixin
from typing import ClassVar
from decimal import Decimal


class Product(UUIDMixin, DefaultTimestampMixin, ActiveRecord):
    name: str
    price: Decimal  # 自动映射为 DECIMAL
    description: str  # 自动映射为 TEXT
    metadata: dict  # 自动映射为 JSON（10.2.3+）

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'products'
```

## dict/list 类型处理

`MariaDBJSONAdapter` 处理 Python 的 `dict` 和 `list` 类型，将其存储为原生 JSON（MariaDB 10.2.3+）或较旧版本的 JSON 字符串：

```python
from rhosocial.activerecord.backend.impl.mariadb.adapters import MariaDBJSONAdapter

adapter = MariaDBJSONAdapter()
data = {"name": "Tom", "tags": ["admin", "user"]}

# 两个版本都会产生相同的 Python 结果
db_value = adapter.to_database(data, dict)  # JSON 字符串
python_value = adapter.from_database(db_value, dict)  # Python dict
```

## 另请参阅

- [类型适配器概述](README.md) — 类型转换架构
- [字段类型](../backend_specific_features/field_types.md) — MariaDB 列类型

💡 *AI 提示词：* "为什么存储货币值推荐使用 DECIMAL 而不是 FLOAT？"
