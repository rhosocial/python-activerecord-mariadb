# BackendGroup 和 BackendManager（MariaDB）

本文档介绍如何将 `BackendGroup` 和 `BackendManager` 与 MariaDB 后端一起使用。有关详细的 API 文档，请参阅[核心库文档](../../../rhosocial-activerecord/docs/zh_CN/connection/connection_management.md)。

## 快速示例

```python
from rhosocial.activerecord.connection import BackendGroup
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    name: str
    email: str


# 使用上下文管理器
with BackendGroup(
    name="main",
    models=[User],
    config=MariaDBConnectionConfig(
        host="localhost",
        port=3306,
        database="myapp",
        username="app",
        password="secret",
    ),
    backend_class=MariaDBBackend,
) as group:
    user = User(name="John", email="john@example.com")
    user.save()

# 通过 BackendManager 使用多个组
from rhosocial.activerecord.connection import BackendManager

manager = BackendManager()
manager.create_group(
    name="main",
    models=[User],
    config=MariaDBConnectionConfig(host="localhost", database="main_db"),
    backend_class=MariaDBBackend,
)
manager.create_group(
    name="stats",
    config=MariaDBConnectionConfig(host="localhost", database="stats_db"),
    backend_class=MariaDBBackend,
)

main_backend = manager.get_group("main").get_backend()
stats_backend = manager.get_group("stats").get_backend()
```

## MariaDB 特定功能

### 连接池配置

MariaDB 后端识别与池相关的配置字段：

```python
config = MariaDBConnectionConfig(
    host="localhost",
    port=3306,
    database="myapp",
    username="app",
    password="secret",
    pool_size=10,          # 需要 DBUtils
    pool_timeout=30,
)
```

> **注意**：`mariadb` Python 驱动程序的 `threadsafety=1`。单个连接不能跨线程共享。对于并发，请使用多进程或请求级别的 `BackendGroup`。

### SSL/TLS 配置

```python
config = MariaDBConnectionConfig(
    host="localhost",
    port=3306,
    database="myapp",
    username="app",
    password="secret",
    ssl_disabled=False,
)
```

## 示例代码

完整示例：[chapter_02_connection_pool/async_connection_pool.py](../examples/chapter_02_connection_pool/async_connection_pool.py)

该示例演示了在多工作器 FastAPI 应用中使用后端连接管理。
