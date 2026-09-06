# 事务隔离级别

## 概述

MariaDB 支持多种事务隔离级别，不同的隔离级别决定了并发事务之间的可见性。

## 隔离级别说明

| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
|---------|------|-----------|------|
| READ UNCOMMITTED | 可能 | 可能 | 可能 |
| READ COMMITTED | 不可能 | 可能 | 可能 |
| REPEATABLE READ (默认) | 不可能 | 不可能 | 可能 |
| SERIALIZABLE | 不可能 | 不可能 | 不可能 |

> **注意**：MariaDB 的默认隔离级别是 `REPEATABLE READ`。对于 InnoDB，`REPEATABLE READ` 使用带一致性快照的 MVCC，在大多数情况下能有效防止幻读。

## 设置隔离级别

您可以在事务管理器上设置隔离级别：

```python
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig
from rhosocial.activerecord.backend.transaction import IsolationLevel

config = MariaDBConnectionConfig(
    host='localhost',
    database='myapp',
    username='user',
    password='password',
)

backend = MariaDBBackend(connection_config=config)
backend.connect()

with backend.transaction() as txn:
    # 为此事务设置隔离级别
    txn.isolation_level = IsolationLevel.READ_COMMITTED
    # ... 事务操作 ...

backend.disconnect()
```

事务管理器会验证隔离级别并拒绝不支持的取值，同时拒绝在事务已激活时更改隔离级别。

## 各隔离级别详解

### READ UNCOMMITTED

每次读取数据时都不会检查未提交的更改；可能发生脏读：

```sql
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
```

仅适用于可以接受近似数据的场景。

### READ COMMITTED

每次读取数据时都读取提交后的数据：

```sql
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

适用于大多数应用场景，平衡了并发性和数据一致性。

### REPEATABLE READ (默认)

在同一事务中多次读取相同数据，结果一致：

```sql
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
```

MariaDB 默认的隔离级别，使用 MVCC 机制实现。

### SERIALIZABLE

最高隔离级别，强制事务顺序执行：

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
```

适用于对数据一致性要求极高的场景，但并发性能较差。

## 支持的取值

`IsolationLevel` 枚举提供：`READ_UNCOMMITTED`、`READ_COMMITTED`、`REPEATABLE_READ`、`SERIALIZABLE`。

💡 *AI 提示词：* "什么是脏读、不可重复读和幻读？"
