# 索引类型

## 概述

MariaDB 支持多种索引类型用于查询优化。

## 索引类型

### B-Tree 索引（默认）

```python
from rhosocial.activerecord.backend.expression import CreateIndexExpression

# 标准 B-tree 索引
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_users_name",
    table_name="users",
    columns=["name"],
)
sql, params = create_idx.to_sql()
# sql: CREATE INDEX idx_users_name ON users (name)
```

### Hash 索引

```python
# Hash 索引（仅 MEMORY 引擎）
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"],
    index_type="HASH",
)
```

### 空间索引

```python
# 空间索引（MyISAM/InnoDB）
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_locations_coords",
    table_name="locations",
    columns=["coordinates"],
    index_type="SPATIAL",
)
```

### 全文索引

```python
# 全文索引
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_articles_content",
    table_name="articles",
    columns=["title", "content"],
    index_type="FULLTEXT",
)
```

## 索引优化

```sql
-- 检查索引使用情况
EXPLAIN SELECT * FROM users WHERE name = 'John';

-- 分析索引
ANALYZE TABLE users;
```

## 另请参阅

- [EXPLAIN](./explain.md) — 查询执行计划

💡 *AI 提示：* "何时应该在 MariaDB 中使用 HASH 而不是 B-Tree 索引？"
