# 连接配置

## 基本配置

```python
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
)

backend = MariaDBBackend(connection_config=config)
backend.connect()
```

## 配置选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `host` | `str` | `'localhost'` | 数据库服务器主机名 |
| `port` | `int` | `3306` | 数据库服务器端口 |
| `database` | `str` | `None` | 数据库名称 |
| `username` | `str` | `None` | 认证用户名 |
| `password` | `str` | `''` | 认证密码 |
| `charset` | `str` | `'utf8mb4'` | 连接字符集 |
| `collation` | `str` | `None` | 连接排序规则 |
| `autocommit` | `bool` | `False` | 启用自动提交模式 |
| `ssl_disabled` | `bool` | `False` | 禁用 SSL 连接 |
| `pool_size` | `int` | `None` | 连接池大小（需要 DBUtils） |
| `pool_timeout` | `int` | `None` | 池连接超时（秒） |
| `version` | `tuple` | `None` | MariaDB 版本元组（主要、次要、补丁） |
| `options` | `dict` | `{}` | 其他连接参数 |

## 环境变量

可以使用 `MARIADB_` 前缀从环境变量加载配置：

```bash
export MARIADB_HOST=localhost
export MARIADB_PORT=3306
export MARIADB_DATABASE=myapp
export MARIADB_USERNAME=user
export MARIADB_PASSWORD=password
export MARIADB_CHARSET=utf8mb4
```

```python
config = MariaDBConnectionConfig.from_env()
backend = MariaDBBackend(connection_config=config)
```

## 版本指定

方言根据 MariaDB 版本调整行为。您可以显式指定版本或让后端自动检测：

```python
# 显式版本
config = MariaDBConnectionConfig(
    host='localhost',
    database='myapp',
    version=(10, 11, 0),
)

# 自动检测版本（需要连接）
backend = MariaDBBackend(connection_config=config)
backend.connect()
backend.introspect_and_adapt()  # 从服务器检测版本
```

AI Prompt: "如何配置 MariaDB 连接池？"
