# MariaDB 方言表达式

## 概述

MariaDB 提供了自己的 SQL 方言，具有扩展标准 SQL 的功能。

## JSON 函数

### JSON 箭头操作符

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.operators import BinaryExpression

# 获取路径上的 JSON 值 (->>)
expr = BinaryExpression(dialect, "=>",
    Column(dialect, "attributes").json_arrow_text("brand"),
    Literal(dialect, "Dell"))
sql, params = expr.to_sql()
# sql: `attributes`->>'brand' = %s
# params: ('Dell',)
```

## 系统版本表

MariaDB 10.3+ 支持系统版本表：

```sql
CREATE TABLE orders (
    id INT PRIMARY KEY,
    amount DECIMAL(10,2),
    valid_from TIMESTAMP(6) GENERATED ALWAYS AS ROW START,
    valid_to TIMESTAMP(6) GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME(valid_from, valid_to)
) WITH SYSTEM VERSIONING;
```

## RETURNING 子句

MariaDB 10.5+ 支持 RETURNING 用于 DML 操作：

```python
# INSERT RETURNING
user = User(name="John")
user.save()
# 返回插入的行和生成的 id

# UPDATE RETURNING
User.query().where(User.c.id == 1).update(name="Jane")
# 返回受影响的行
```

## 另请参阅

- [字段类型](./field_types.md) — MariaDB 特定数据类型
- [索引](./indexing.md) — 索引类型和优化

💡 *AI 提示：* "MariaDB 的系统版本表如何工作？"
