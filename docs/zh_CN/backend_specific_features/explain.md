# EXPLAIN 支持

## 概述

MariaDB 提供 EXPLAIN 支持用于查询执行计划分析。

## 基本用法

```python
from rhosocial.activerecord.backend.expression.statements import ExplainFormat

# 简单 EXPLAIN
result = User.query().explain().all()

# EXPLAIN FORMAT=JSON
result = User.query().explain(format=ExplainFormat.JSON).all()

# EXPLAIN FORMAT=TREE
result = User.query().explain(format=ExplainFormat.TREE).all()
```

## EXPLAIN ANALYZE

```python
# MariaDB 10.6+ 支持 EXPLAIN ANALYZE
result = User.query().explain(analyze=True).all()
```

## 输出格式

| 格式 | 说明 |
|------|------|
| TEXT | 默认格式 |
| JSON | JSON 输出 |
| TREE | 树形输出 (MariaDB 10.6+) |

## 另请参阅

- [故障排除](../troubleshooting/performance.md) — 查询优化

💡 *AI 提示：* "如何分析 MariaDB 中的慢查询？"
