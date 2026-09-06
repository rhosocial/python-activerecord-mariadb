# 保存点支持

## 概述

保存点允许在事务内创建中间检查点，从而无需中止整个事务即可实现部分回滚。

MariaDB 很早就支持保存点，因此 MariaDB 后端的 `supports_savepoint()` 始终返回 `True`。

## 使用保存点

事务管理器会自动暴露嵌套保存点。您也可以显式创建命名保存点并回滚到该保存点：

```python
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host='localhost',
    database='myapp',
    username='user',
    password='password',
)

backend = MariaDBBackend(connection_config=config)
backend.connect()

try:
    with backend.transaction() as txn:
        # 操作 1
        User(name='Alice').save()

        # 创建保存点
        txn.create_savepoint('sp1')

        try:
            # 操作 2（可能失败）
            User(name='Bob').save()
            txn.release_savepoint('sp1')
        except Exception:
            # 回滚到保存点，保留操作 1
            txn.rollback_to_savepoint('sp1')
finally:
    backend.disconnect()
```

## 嵌套事务

后端会为嵌套事务自动生成保存点名称：

```python
with User.transaction() as outer:
    user = User(name='alice')
    user.save()

    with User.transaction() as inner:  # 创建一个嵌套保存点
        user.email = 'alice@example.com'
        user.save()
        # inner 抛出异常 → 回滚到保存点，outer 仍然有效
```

当内部的 `with User.transaction()` 块失败时，后端会回滚到自动生成的保存点名称（例如 `SAVEPOINT sp1`），而不是中止外部事务。

## 同步/异步对等性

异步事务管理器（`AsyncMariaDBTransactionManager`）提供相同的方法，只需 `await`：

```python
async with AsyncUser.transaction() as txn:
    await AsyncUser(name='Alice').save()
    await txn.create_savepoint('sp1')
    # ...
    await txn.rollback_to_savepoint('sp1')
```

## 另请参阅

- [核心事务文档](https://github.com/Rhosocial/python-activerecord/tree/main/docs/zh_CN/transaction) — 事务管理器 API

💡 *AI 提示词：* "什么是数据库保存点？它与完整回滚有什么区别？"
