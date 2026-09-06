# 自定义表达式

## 概述

MariaDB 后端使用 MariaDB 特有的 SQL 语法扩展了核心表达式类。您可以创建新的表达式类型，以添加对 MariaDB 独有的 SQL 结构的支持。

## 表达式设计原则

表达式是**声明式**的——它们收集所有参数，并将 SQL 生成委托给方言：

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, **params):
        self.dialect = dialect
        self.params = params

    def to_sql(self, dialect):
        # 委托方言生成 SQL
        return dialect.format_my_expression(**self.params)
```

## 创建自定义表达式

### 第一步：定义表达式类

```python
from rhosocial.activerecord.backend.expression.base import BaseExpression

class MariaDBJSONExpression(BaseExpression):
    """用于 JSON_EXTRACT 的 MariaDB JSON 表达式。"""

    def __init__(self, dialect, column, path):
        self.dialect = dialect
        self.column = column
        self.path = path

    def to_sql(self, dialect):
        return f"JSON_EXTRACT({self.column.to_sql(dialect)}, '{self.path}')"
```

### 第二步：向方言注册

```python
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

class CustomMariaDBDialect(MariaDBDialect):
    def format_json_extract(self, column, path):
        return f"JSON_EXTRACT({column}, '{path}')"
```

### 第三步：在代码中使用

MariaDB 使用反引号引用标识符：

```python
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.core import FunctionCall

# 使用表达式系统构建表达式
expr = FunctionCall(
    dialect, "JSON_EXTRACT",
    Column(dialect, "data"),
    Literal(dialect, "$.name"),
)
sql, params = expr.to_sql()
# sql: JSON_EXTRACT(`data`, %s)
# params: ('$.name',)
```

## 运算符混合类

使用运算符混合类支持常见的比较和算术操作：

```python
from rhosocial.activerecord.backend.expression.operators import ComparisonMixin, ArithmeticMixin
from rhosocial.activerecord.backend.expression import Column

class MyExpression(ComparisonMixin, ArithmeticMixin, BaseExpression):
    pass

# 现在支持 ==, !=, <, >, +, -, *, / 等
expr = MyExpression(dialect, Column(dialect, "amount")) > 100
sql, params = expr.to_sql()
# sql: `amount` > %s
# params: (100,)
```

## 序列化

表达式支持序列化/反序列化，用于缓存和日志记录：

```python
# 序列化
data = expr.serialize()

# 反序列化
expr = BaseExpression.deserialize(data)
```

## 另请参阅

- [核心表达式系统](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/expression) — 表达式基类和运算符
- [MariaDB 方言](../backend_specific_features/dialect.md) — MariaDB 特有的 SQL 函数

💡 *AI 提示词：* "如何为 MariaDB JSON 函数创建自定义表达式？"
