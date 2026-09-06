# SSL/TLS 配置

## 概述

MariaDB 后端支持 SSL/TLS 连接，用于与数据库服务器的安全通信。

## 启用 SSL

```python
config = MariaDBConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
    ssl_disabled=False,
)
```

## SSL 参数

| 参数 | 类型 | 描述 |
|------|------|------|
| `ssl_disabled` | `bool` | 设为 `False` 以启用 SSL |
| `tls_version` | `str` | 使用的 TLS 版本（如 `'TLSv1.2'`） |
| `options` | `dict` | 传递给驱动的其他 SSL 选项 |

## SSL 连接选项

通过 `options` 字典传递 SSL 特定选项：

```python
config = MariaDBConnectionConfig(
    host='prod-db.example.com',
    port=3306,
    database='myapp',
    username='user',
    password='password',
    ssl_disabled=False,
    options={
        'ssl_ca': '/path/to/ca.pem',
        'ssl_cert': '/path/to/client-cert.pem',
        'ssl_key': '/path/to/client-key.pem',
    },
)
```

## CLI SSL 选项

CLI 通过 `--ssl` 参数支持 SSL：

```bash
rhosocial-activerecord-mariadb query \
    --host localhost --port 3306 --database mydb \
    --ssl require \
    "SELECT * FROM users"
```

可用的 SSL 模式：`auto`、`require`、`verify-ca`、`verify-full`、`disabled`。

AI Prompt: "如何为 MariaDB 连接设置 SSL？"
