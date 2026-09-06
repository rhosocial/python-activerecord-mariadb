# 自定义类型适配器

## 概述

类型适配器负责在 Python 值和 MariaDB 数据库值之间进行转换。MariaDB 后端提供了一个用于注册自定义适配器的类型注册表。

## 类型注册表

类型注册表管理所有类型转换：

```python
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend

backend = MariaDBBackend(...)
registry = backend.type_registry
```

## 注册自定义适配器

### 使用 @handles 装饰器

```python
from rhosocial.activerecord.backend.impl.mariadb.types import MariaDBDataType

@MariaDBDataType.handles(MyClass)
class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        """将 Python MyClass 转换为 MariaDB 值。"""
        return json.dumps(value.__dict__)

    @staticmethod
    def from_sql(value, dialect):
        """将 MariaDB 值转换为 Python MyClass。"""
        return MyClass(**json.loads(value))
```

### 手动注册

```python
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend

class MyAdapter:
    @staticmethod
    def to_sql(value, dialect):
        return str(value)

    @staticmethod
    def from_sql(value, dialect):
        return MyClass(value)

backend = MariaDBBackend(...)
backend.type_registry.register(MyClass, MyAdapter)
```

## SQLTypeAdapter 协议

自定义适配器必须实现 `SQLTypeAdapter` 协议：

```python
class SQLTypeAdapter(Protocol):
    @staticmethod
    def to_sql(value: Any, dialect: Any) -> Any:
        """将 Python 值转换为 SQL 值。"""
        ...

    @staticmethod
    def from_sql(value: Any, dialect: Any) -> Any:
        """将 SQL 值转换为 Python 值。"""
        ...
```

## BaseSQLTypeAdapter

对于常见模式，可以继承 `BaseSQLTypeAdapter`：

```python
from rhosocial.activerecord.backend.adapters import BaseSQLTypeAdapter

class DateAdapter(BaseSQLTypeAdapter):
    @staticmethod
    def to_sql(value, dialect):
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def from_sql(value, dialect):
        if value is None:
            return None
        return date.fromisoformat(value)
```

## 类型转换流程

```
Python 值
    │
    ▼
to_sql(value, dialect)
    │
    ▼
MariaDB 数据库值
    │
    ▼
from_sql(value, dialect)
    │
    ▼
Python 值
```

## 另请参阅

- [类型映射](../type_adapters/mapping.md) — MariaDB 到 Python 类型转换表
- [自定义类型适配器](../type_adapters/custom.md) — 扩展类型支持
- [核心自定义适配器指南](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/template/customization/custom_adapters.md) — 通用自定义模式

💡 *AI 提示词：* "如何为 MariaDB 注册一个自定义类型适配器？"
