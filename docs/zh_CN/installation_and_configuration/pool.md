# 连接管理

## 按需连接生命周期

MariaDB 后端使用按需连接模式。连接在执行第一个查询时延迟建立，并保持打开状态直到显式关闭或后端被垃圾回收。

```python
backend = MariaDBBackend(connection_config=config)
backend.connect()
# 连接已打开
backend.disconnect()
# 连接已关闭
```

## 上下文管理器

使用上下文管理器进行自动连接管理：

```python
with backend:
    # 连接已打开
    pass
# 连接自动关闭
```

## 连接池

通过 DBUtils 包提供可选的连接池功能：

```bash
pip install "rhosocial-activerecord-mariadb[pooling]"
```

这将安装 `DBUtils>=3.0.0`，它提供 `PooledDB`。

### 配置池大小

```python
config = MariaDBConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
    pool_size=10,
    pool_timeout=30,
)
```

## FastAPI 模式

```python
from fastapi import FastAPI
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig

app = FastAPI()

config = MariaDBConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
)

@app.on_event("startup")
async def startup():
    backend = MariaDBBackend(connection_config=config)
    backend.connect()

@app.on_event("shutdown")
async def shutdown():
    backend.disconnect()
```

## 多个后端

您可以为不同数据库或连接配置文件创建多个后端：

```python
# 只读副本
read_config = MariaDBConnectionConfig(
    host='replica-db.example.com',
    port=3306,
    database='myapp',
    username='readonly',
    password='password',
)

# 写入主库
write_config = MariaDBConnectionConfig(
    host='primary-db.example.com',
    port=3306,
    database='myapp',
    username='admin',
    password='password',
)
```

AI Prompt: "如何在 FastAPI 应用程序中管理连接？"
