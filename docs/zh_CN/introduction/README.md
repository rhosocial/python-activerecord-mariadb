# 简介

## MariaDB 后端概述

`rhosocial-activerecord-mariadb` 是 rhosocial-activerecord 核心库的 MariaDB 数据库后端实现。它提供完整的 ActiveRecord 模式支持，专门针对 MariaDB 数据库特性进行了优化。

MariaDB 是 MySQL 的社区开发分支，API 兼容但引入了不同版本边界上的独特功能。此后端为 MariaDB 特有功能提供了一流支持，包括：

- **RETURNING 子句**（自 MariaDB 10.5 起）-- 支持 INSERT 和 DELETE，但不支持 UPDATE
- **SEQUENCE**（自 MariaDB 10.3 起）-- 数据库级别序列对象
- **INTERSECT / EXCEPT**（自 MariaDB 10.3 起）-- 比 MySQL 更早添加的集合操作
- **系统版本化表**（自 MariaDB 10.3 起）-- 内置时态数据支持
- **窗口函数**（自 MariaDB 10.2 起）
- **公共表表达式**（自 MariaDB 10.2 起）

此后端负责三个主要任务：

- **SQL 方言生成** -- 将通用查询构建器转换为 MariaDB 特定的 SQL 语句
- **数据类型映射** -- 处理 MariaDB 类型，包括 TINYINT 到 BIGINT、CHAR/VARCHAR/TEXT 变体、DATE/TIME/DATETIME/TIMESTAMP、BINARY/VARBINARY/BLOB、JSON、ENUM、SET 和 YEAR
- **连接和事务管理** -- 建立 TCP 连接、执行 START TRANSACTION/COMMIT/ROLLBACK，以及管理 MariaDB 特有的行为（如自增和保存点）

## 同步和异步

MariaDB 后端提供功能等效的同步和异步 API。文档中使用同步示例，但异步 API 的使用方式完全相同 -- 只需将方法调用替换为相应的异步等效方法。

### 命名约定

| 组件 | 同步 | 异步 |
|------|------|------|
| 后端类 | `MariaDBBackend` | `AsyncMariaDBBackend` |
| 事务管理器 | `MariaDBTransactionManager` | `AsyncMariaDBTransactionManager` |
| 连接配置 | `MariaDBConnectionConfig` | `MariaDBConnectionConfig`（共享） |
| 方言 | `MariaDBDialect` | `MariaDBDialect`（共享） |

连接配置和方言在同步和异步之间共享 -- 它们是纯数据对象，不是活动连接。

### 模型层

| 操作 | `ActiveRecord`（同步） | `AsyncActiveRecord`（异步） |
|------|----------------------|----------------------------|
| 查找一个 | `find_one()` | `async find_one()` |
| 查找所有 | `find_all()` | `async find_all()` |
| 保存 | `save()` | `async save()` |
| 删除 | `delete()` | `async delete()` |
| 查询构建器 | `.query()` -> `ActiveQuery` | `.query()` -> `AsyncActiveQuery` |

方法名在同步和异步之间完全相同 -- 区别在于类级别，而非方法级别。

### 异步驱动

MariaDB 使用相同的库同时支持同步和异步（v2.0.0+）：

| 后端 | 同步驱动 | 异步驱动 | 备注 |
|------|---------|---------|------|
| MariaDB | `mariadb` | `mariadb`（asyncConnect） | 同一库，v2.0.0+ |

如果导入 `AsyncMariaDBBackend` 但未安装异步驱动，将在导入时获得 `ImportError`。

## 快速开始

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, DefaultTimestampMixin
from rhosocial.activerecord.backend.impl.mariadb import (
    MariaDBBackend, AsyncMariaDBBackend, MariaDBConnectionConfig,
)

class User(UUIDMixin, DefaultTimestampMixin, ActiveRecord):
    username: str = Field(..., max_length=50)
    email: str
    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'

# 同步
config = MariaDBConnectionConfig(
    host='localhost', port=3306,
    database='myapp', username='user', password='password',
)
User.configure(config, MariaDBBackend)

user = User(username='tom', email='tom@example.com')
user.save()
found = User.query().where(User.c.username == 'tom').one()

# 异步
User.configure(config, AsyncMariaDBBackend)
user = await User(username='tom', email='tom@example.com').save()
```

## 与核心库的关系

rhosocial-activerecord 使用模块化设计，核心库提供数据库无关的 ActiveRecord 实现，数据库后端作为单独的扩展包存在。MariaDB 后端的命名空间是 `rhosocial.activerecord.backend.impl.mariadb`，与其他后端处于同一级别。

```
rhosocial.activerecord
├── backend.impl.sqlite      # SQLite 后端
├── backend.impl.dummy       # 测试用虚拟后端
├── backend.impl.mysql       # MySQL 后端
└── backend.impl.mariadb     # MariaDB 后端（本包）
    ├── MariaDBBackend
    ├── AsyncMariaDBBackend
    └── ...
```

后端不参与 ActiveRecord 层的变更 -- 它们严格遵循后端接口协议。后端更新与核心库的 ActiveRecord 功能解耦。

## 与 MySQL 的差异

MariaDB 与 MySQL API 兼容，但有影响后端的重要差异：

| 功能 | MySQL | MariaDB |
|------|-------|---------|
| RETURNING 子句 | 不支持 | 支持 INSERT/DELETE（10.5+），**不支持** UPDATE |
| INTERSECT/EXCEPT | 不支持 | 10.3 起支持 |
| SEQUENCE | 不支持 | 10.3 起支持 |
| 系统版本化表 | 不支持 | 10.3 起支持 |
| 窗口函数 | 8.0 起 | 10.2 起 |
| CTE | 8.0 起 | 10.2 起 |
| MERGE 语句 | 不支持 | 不支持 |
| `OR REPLACE` DDL | 有限 | 支持表、触发器、例程 |
| `CREATE TABLE ... IF NOT EXISTS` | 支持 | 支持 |
| `EXPLAIN FORMAT=TREE` | 支持（8.0+） | 不支持 |
| `CUBE` / `GROUPING SETS` | 支持 | 不支持 |
| Schema 层 | 无（schema = database） | 无（schema = database） |
| LATERAL 连接 | 8.0+ 支持 | 支持 |
| `FOR UPDATE SKIP LOCKED` | 8.0+ 支持 | 10.3+ 支持 |

## 已知限制和怪癖

每个数据库都有与 SQL 标准不同的行为。本节记录可能让您感到意外的 MariaDB 特定怪癖：

| 怪癖 | 描述 |
|------|------|
| RETURNING 不支持 UPDATE | RETURNING 适用于 INSERT/DELETE/REPLACE（10.5+），但不适用于 UPDATE |
| REPLACE INTO 更改 AUTO_INCREMENT | 删除并重新插入行，更改 AUTO_INCREMENT 值 |
| 系统版本化表 | 10.3+ 支持 `WITH SYSTEM VERSIONING` 用于时态数据 |
| OR REPLACE | 支持表、触发器和例程的 `CREATE OR REPLACE` |
| 版本边界与 MySQL 不同 | CTE 自 10.2 起，窗口函数自 10.2 起等 |
| 不支持 MERGE 语句 | 请改用 `INSERT ... ON DUPLICATE KEY UPDATE` |
| 不支持 CUBE/GROUPING SETS | MariaDB 不支持这些分组操作 |
| 不支持物化 CTE | 不支持 `MATERIALIZED` 提示 |
| 不支持 QUALIFY 子句 | 请改用子查询或 CTE |

AI Prompt: "什么是 ActiveRecord 模式？它与 DataMapper 模式有什么区别？"
