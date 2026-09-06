# 常见连接错误

## 概述

本节介绍常见的 MariaDB 连接错误及其解决方案。

## 连接被拒绝

### 错误信息
```
ERROR 2003 (HY000): Can't connect to MariaDB server
```

### 原因
- MariaDB 服务未运行
- 端口不正确
- 防火墙阻止

### 解决方案
```bash
# 检查 MariaDB 是否正在运行
sudo systemctl status mariadb

# 检查端口
telnet localhost 3306
```

## 认证失败

### 错误信息
```
ERROR 1045 (28000): Access denied for user 'root'@'localhost'
```

### 原因
- 用户名或密码错误
- 用户没有远程访问权限

### 解决方案
```sql
-- 在 MariaDB 服务器上执行
CREATE USER 'user'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON database.* TO 'user'@'%';
FLUSH PRIVILEGES;
```

## 连接超时

### 错误信息
```
ERROR 2003: Can't connect to MariaDB server (110)
```

### 原因
- 网络问题
- connect_timeout 设置过短

### 解决方案
```python
config = MariaDBConnectionConfig(
    host='remote.host.com',
    connect_timeout=30,  # 增加超时时间
)
```

## 连接丢失与自动恢复

在长时间运行的应用程序中，数据库连接可能因各种原因而断开。MariaDB 后端在连接丢失时实现了自动恢复。

### 常见的连接丢失场景

| 场景 | 原因 | 错误代码 |
|----------|-------|-------------|
| `wait_timeout` 到期 | 连接空闲时间超过 `wait_timeout` | 2006, 2013 |
| 连接被终止 | DBA 执行 `KILL CONNECTION` | 2013 |
| 网络不稳定 | TCP 连接断开 | 2003, 2055 |
| 服务器重启 | MariaDB 重启或崩溃 | 2006, 2013 |
| 防火墙超时 | 防火墙关闭长时间空闲的 TCP 连接 | 2013 |

### 自动恢复

后端在每次查询前检查连接状态，并在连接丢失时透明地重新连接。当查询因连接错误而失败时，会自动重试（最多 2 次），仅在连接错误时重试，其他错误则直接抛出。

### 手动保活

如需主动维护连接，可使用 `ping()` 方法：

```python
# 检查连接状态而不自动重连
is_alive = backend.ping(reconnect=False)

# 检查连接状态，断开时自动重连
is_alive = backend.ping(reconnect=True)
```

### 异步后端支持

异步后端（`AsyncMariaDBBackend`）提供相同的恢复机制：

```python
# 异步 ping
is_alive = await async_backend.ping(reconnect=True)

# 异步查询也会自动重连
result = await async_backend.execute("SELECT 1")
```

### 最佳实践

1. **适当配置 MariaDB 超时参数**：

```sql
-- 查看当前设置
SHOW VARIABLES LIKE 'wait_timeout';
SHOW VARIABLES LIKE 'interactive_timeout';

-- 推荐设置（按需调整）
SET GLOBAL wait_timeout = 28800;        -- 8 小时
SET GLOBAL interactive_timeout = 28800; -- 8 小时
```

2. **多进程工作器场景**：每个工作进程应有自己的后端实例。`mariadb` 驱动是 `threadsafety=1`，因此切勿跨线程共享连接。

```python
def worker_process(worker_id, config):
    # 在进程内创建独立的后端实例
    backend = MariaDBBackend(connection_config=config)
    backend.connect()
    try:
        do_work(backend)
    finally:
        backend.disconnect()
```

### 连接错误代码参考

| 错误代码 | 名称 | 描述 |
|------------|------|-------------|
| 2003 | CR_CONN_HOST_ERROR | 无法连接到 MariaDB 服务器 |
| 2006 | CR_SERVER_GONE_ERROR | MariaDB 服务器已消失 |
| 2013 | CR_SERVER_LOST | 查询期间连接丢失 |
| 2055 | CR_SERVER_LOST_EXTENDED | 扩展连接丢失 |

💡 *AI 提示词：* "如何排查 MariaDB 连接错误？后端如何自动恢复连接？"
