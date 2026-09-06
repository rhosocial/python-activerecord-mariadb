# DDL 操作

## 概述

本节介绍 MariaDB 后端的 DDL（数据定义语言）操作。DDL 定义您的数据库模式 -- 表、索引、视图和其他对象。

**重要提示**：rhosocial-activerecord 中的所有 DDL 都是**基于表达式**的。您在 Python 中定义模式，框架生成 SQL，然后通过后端执行。下面的示例使用 `ActiveRecord` 以保持简洁，但 `AsyncActiveRecord` 的工作方式完全相同 -- DDL 生成是纯计算，不涉及 I/O。

DDL 章节分为两部分：

1. **后端 DDL 能力** -- MariaDB 后端支持的完整 DDL 操作集，通过后端特定的表达式类表达。这是后端的全部能力。
2. **ActiveRecord DDL 派生** -- 框架可以从模型类声明自动生成的内容。这是覆盖大多数常见用例的便捷子集。

---

# 第 1 部分：后端 DDL 能力

MariaDB 后端支持以下 DDL 操作。每个操作通过相应的表达式类表达 -- 您构造表达式，然后通过后端执行。

## 支持的操作

| 操作 | MariaDB 支持 | 表达式类 |
|------|-------------|---------|
| CREATE TABLE | 是 | `CreateTableExpression` |
| ALTER TABLE | 是 | `AlterTableExpression` |
| DROP TABLE | 是 | `DropTableExpression` |
| CREATE INDEX | 是 | `CreateIndexExpression` |
| DROP INDEX | 是 | `DropIndexExpression` |
| CREATE VIEW | 是 | `CreateViewExpression` |
| DROP VIEW | 是 | `DropViewExpression` |
| TRUNCATE | 是 | `TruncateExpression` |

## CREATE TABLE

### IF NOT EXISTS

MariaDB 支持 `CREATE TABLE IF NOT EXISTS`。

### 临时表

MariaDB 支持 `CREATE TEMPORARY TABLE`。

### Engine 和 Charset 选项

MariaDB 支持表选项如 `ENGINE`、`DEFAULT CHARSET`、`COLLATE` 和 `COMMENT`：

```sql
CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User accounts table'
```

## ALTER TABLE

### 添加列

| 功能 | MariaDB 支持 |
|------|-------------|
| ADD COLUMN | 是 |
| ADD COLUMN IF NOT EXISTS | 是（语法有差异） |

### 删除列

| 功能 | MariaDB 支持 |
|------|-------------|
| DROP COLUMN | 是 |
| DROP COLUMN IF EXISTS | 是 |

### 重命名列

MariaDB 支持 `RENAME COLUMN`（10.5+）和 `CHANGE COLUMN`（所有版本）。

### 更改列类型

MariaDB 使用 `MODIFY COLUMN` 就地更改列类型：

```sql
ALTER TABLE users MODIFY COLUMN age SMALLINT NOT NULL;
```

## DROP TABLE

| 功能 | MariaDB 支持 |
|------|-------------|
| IF EXISTS | 是 |
| CASCADE/RESTRICT | 解析但忽略 |

## CREATE INDEX

### 索引类型

| 索引类型 | MariaDB 支持 |
|---------|-------------|
| BTREE | 是 |
| HASH | 是 |
| FULLTEXT | 是 |
| SPATIAL | 是 |

### 函数索引

MariaDB 支持函数索引（表达式索引）。

### 全文索引

MariaDB 支持 InnoDB 表上的 `FULLTEXT INDEX`（10.2+ 起）。

## CREATE VIEW

| 功能 | MariaDB 支持 |
|------|-------------|
| OR REPLACE | 是 |
| TEMPORARY | 是 |
| WITH CHECK OPTION | 是 |
| CASCADED/LOCAL | 是 |

## TRUNCATE

| 功能 | MariaDB 支持 |
|------|-------------|
| TRUNCATE TABLE | 是 |
| RESTART IDENTITY | 否 |
| CASCADE | 否 |

## Schema 支持

MariaDB 没有与数据库不同的 schema 层。`schema()` 映射到 `USE database`。

## 序列

MariaDB 自 10.3 版本起支持 `CREATE SEQUENCE`：

```sql
CREATE SEQUENCE order_seq START WITH 1 INCREMENT BY 1;
SELECT NEXTVAL(order_seq);
```

## 后端特定表达式类

| 表达式 | 用途 |
|--------|------|
| `MariaDBLoadDataExpression` | LOAD DATA INFILE |
| `MariaDBShowCreateTableExpression` | SHOW CREATE TABLE |
| `MariaDBShowColumnsExpression` | SHOW COLUMNS |
| 各种 `Show*Expression` | SHOW 命令包装器 |

---

# 第 2 部分：ActiveRecord DDL 派生

`ModelSchemaGenerator` 从 ActiveRecord 模型声明派生 DDL。您在模型类上定义字段、表名、索引和约束 -- 框架生成 SQL。

## 可以从模型派生的功能

| 功能 | 模型集成 | 使用方式 |
|------|---------|---------|
| 表创建 | 是 | `ModelSchemaGenerator.generate_create_table()` |
| 列定义 | 是 | 在模型类上声明字段 |
| 索引 | 是 | `indexes()` 类方法 |
| 约束 | 是 | `UseConstraint` 注解 |
| Engine / CHARSET | 是 | `engine()`、`charset()` 类方法 |
| 表注释 | 是 | `comment()` 类方法 |
| Schema | 是 | `schema()` 类方法 |
| 分区 | **否** | 仅后端特定表达式类 |
| 序列 | **否** | 仅后端特定表达式类 |
| 触发器 | **否** | 仅后端特定表达式类 |
| 存储过程 | **否** | 仅后端特定表达式类 |

## 创建表

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar

class User(ActiveRecord):
    id: int | None = None
    username: str
    email: str
    age: int
    is_active: bool = True

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

MariaDB 生成的 SQL：

```sql
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(255) NOT NULL,
    `email` VARCHAR(255) NOT NULL,
    `age` INT NOT NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

## 生成 DDL SQL

```python
from rhosocial.activerecord.base.ddl_generator import DDLGenerator

create_sql = DDLGenerator.generate_create_table(User)
print(create_sql)
```

## 运行 DDL

```python
# 同步
with User.connection() as conn:
    conn.execute(create_sql)

# 异步
async with User.connection() as conn:
    await conn.execute(create_sql)
```

---

## 另请参阅

- [字段类型](../backend_specific_features/field_types.md) -- DataType 层次结构和后端特定类型
- [索引](../backend_specific_features/indexing.md) -- 索引类型和优化
- [分区](../backend_specific_features/partition.md) -- 表分区策略
- [方言表达式](../backend_specific_features/dialect.md) -- 功能检测和协议系统
- [核心：DDL](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/ddl)

AI Prompt: "MariaDB 和 MySQL 的 DDL 生成有什么区别？"
