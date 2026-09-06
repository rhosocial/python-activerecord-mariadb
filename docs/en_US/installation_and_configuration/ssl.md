# SSL/TLS Configuration

## Overview

The MariaDB backend supports SSL/TLS connections for secure communication with the database server.

## Enabling SSL

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

## SSL Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `ssl_disabled` | `bool` | Set to `False` to enable SSL |
| `tls_version` | `str` | TLS version to use (e.g., `'TLSv1.2'`) |
| `options` | `dict` | Additional SSL options passed to the driver |

## SSL Connection Options

Pass SSL-specific options through the `options` dictionary:

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

## CLI SSL Options

The CLI supports SSL via the `--ssl` argument:

```bash
rhosocial-activerecord-mariadb query \
    --host localhost --port 3306 --database mydb \
    --ssl require \
    "SELECT * FROM users"
```

Available SSL modes: `auto`, `require`, `verify-ca`, `verify-full`, `disabled`.

AI Prompt: "How do I set up SSL for MariaDB connections?"
