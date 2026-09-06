# 性能问题

## 概述

本节介绍 MariaDB 性能问题和优化方法。

## 慢查询分析

### 启用慢查询日志

```sql
-- 查看慢查询配置
SHOW VARIABLES LIKE 'slow_query_log%';

-- 启用慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
```

### 使用 EXPLAIN 分析查询

使用表达式系统构建 EXPLAIN 语句，而不是执行原始 SQL。先用表达式类构建查询，再将其包装在 `ExplainExpression` 中：

```python
from rhosocial.activerecord.backend.expression.statements.explain import (
    ExplainExpression,
    ExplainOptions,
    ExplainFormat,
)

# 使用表达式系统构建查询表达式
query = User.query().where(User.c.name == "Tom").select(User.c.id, User.c.name)

# 基本 EXPLAIN
explain = ExplainExpression(dialect, statement=query)
sql, params = explain.to_sql()
# sql: EXPLAIN SELECT `id`, `name` FROM `users` WHERE `name` = %s
# params: ('Tom',)

# EXPLAIN FORMAT=JSON（MariaDB 10.6+）
explain_json = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(format=ExplainFormat.JSON),
)

# EXPLAIN ANALYZE（MariaDB 10.6+）
explain_analyze = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(analyze=True),
)
```

> **注意**：`EXPLAIN FORMAT=JSON` 和 `EXPLAIN ANALYZE` 需要 MariaDB 10.6+。

## 常见性能问题

### 1. 缺少索引

```sql
-- 添加索引
CREATE INDEX idx_name ON users(name);
```

### 2. SELECT *

```python
# 避免 SELECT *，只查询所需列
users = User.query().select(User.c.id, User.c.name).all()
```

### 3. N+1 查询问题

```python
# 使用 with_() 预加载关联数据，避免 N+1 查询
users = User.query().with_('posts').all()

# 加载嵌套关联
users = User.query().with_('posts.comments').all()

# 使用查询修饰符加载
users = User.query().with_(('posts', lambda q: q.limit(5))).all()
```

### 4. JSON 类型性能

MariaDB 自 10.2.3 起支持原生 JSON 存储。`dict`/`list` 字段通过 `MariaDBJSONAdapter` 序列化：

```python
from rhosocial.activerecord.backend.impl.mariadb.adapters import MariaDBJSONAdapter

adapter = MariaDBJSONAdapter()
data = {"name": "Tom", "tags": ["admin"]}

# 转换为数据库值
db_value = adapter.to_database(data, dict)
# 输出: '{"name": "Tom", "tags": ["admin"]}'

# 转换回 Python
python_value = adapter.from_database(db_value, dict)
# 输出: {'name': 'Tom', 'tags': ['admin']}
```

**建议**：对于新项目，请使用 MariaDB 10.2.3+（最好使用 10.6+ LTS），以获得完整的 JSON 支持，包括箭头运算符（`->>`）和 `JSON_TABLE`。

## 连接超时

```python
config = MariaDBConnectionConfig(
    connect_timeout=30,
    read_timeout=60,
    write_timeout=60,
)
```

## 另请参阅

- [EXPLAIN 支持](../backend_specific_features/explain.md) — 查询执行计划分析
- [索引](../backend_specific_features/indexing.md) — 索引类型和优化

💡 *AI 提示词：* "如何优化 MariaDB 查询性能？"
