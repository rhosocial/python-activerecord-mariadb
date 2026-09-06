# 类型适配器

## 概述

类型适配器处理 MariaDB 数据类型和 Python 类型之间的转换。rhosocial-activerecord 为常见类型提供内置适配器，并允许您为特殊用例创建自定义适配器。

## 架构：类型转换如何工作

rhosocial-activerecord 使用**两层类型系统**在 Python 类型和 SQL 类型之间进行转换：

### 第 1 层：核心 DataType 层次结构

核心库在 `rhosocial.activerecord.backend.expression.types` 中定义通用 `DataType` 类：

```python
from rhosocial.activerecord.backend.expression.types import (
    IntegerType,
    VarCharType,
    BooleanType,
    TimestampType,
    JsonType,
)
```

这些核心类型是**后端无关**的 -- 它们定义逻辑类型而不指定确切的 SQL 语法。当您在模型上声明字段为 `str`、`int` 或 `bool` 时，框架会将其映射到相应的核心 DataType。

### 第 2 层：后端特定 DataType 子类

每个后端用数据库特定行为扩展核心类型：

| 后端 | 核心类型 | 后端类型 | 行为 |
|------|---------|---------|------|
| MariaDB | `IntegerType` | `MariaDBIntType` | 添加 `AUTO_INCREMENT` |
| MariaDB | `EnumType` | `MariaDBEnumType` | MariaDB ENUM 类型 |
| MariaDB | `SetType` | `MariaDBSetType` | MariaDB SET 类型 |
| MariaDB | `YearType` | `MariaDBYearType` | MariaDB YEAR 类型 |

### 转换流程

```
Python 字段声明
    ↓
核心 DataType（例如 IntegerType）
    ↓
Dialect.suggest_column_type() → 映射到后端特定类型
    ↓
后端 DataType（例如 MariaDBIntType）
    ↓
Dialect.format_data_type() → 生成 SQL 类型字符串
```

## 内容

- [类型映射](mapping.md)：MariaDB 到 Python 类型转换表
- [自定义适配器](custom.md)：扩展类型支持
- [时区处理](timezone.md)：时间戳和时区配置

## 检查类型支持

您可以在运行时检查后端是否支持特定类型：

```python
from rhosocial.activerecord.backend.dialect.protocols import JSONSupport

dialect = backend.dialect

# 检查 JSON 支持
if isinstance(dialect, JSONSupport) and dialect.supports_json_type():
    # JSON 类型可用（MariaDB 10.2.3+）
    ...
```

## 另请参阅

- [后端特定功能：字段类型](../backend_specific_features/field_types.md) -- DataType 层次结构和后端特定类型
- [方言表达式](../backend_specific_features/dialect.md) -- 功能检测和协议系统
- [核心：自定义类型](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/custom_types)

AI Prompt: "类型系统如何在 Python 类型和 MariaDB 类型之间进行转换？"
