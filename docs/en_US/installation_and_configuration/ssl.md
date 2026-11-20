<!-- docs/en_US/installation_and_configuration/ssl.md -->
# SSL/TLS

The MariaDB backend asks the connector for TLS by default: `ssl_disabled`
defaults to `False`, and `get_connection_params()` sets `ssl=True` unless it is
explicitly disabled.

## Basic TLS

```python
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host="db.example.com",
    port=3306,
    database="myapp",
    username="app",
    password="secret",
    tls_version="TLSv1.3",
    ssl_verify_cert=True,
    ssl_verify_identity=True,
)
```

The fields map onto connector keywords as follows:

| Config field | Connector keyword |
|--------------|-------------------|
| `tls_version` | `tls_version` |
| `ssl_verify_cert` | `ssl_verify_cert` |
| `ssl_verify_identity` | `ssl_verify_identity` |
| `ssl_ca` | `ssl_ca` |
| `ssl_cert` | `ssl_cert` |
| `ssl_key` | `ssl_key` |
| `ssl_ciphers` | `ssl_cipher` |

## Mutual TLS

Supply a client certificate and key together with the CA:

```python
config = MariaDBConnectionConfig(
    host="db.example.com",
    database="myapp",
    username="app",
    password="secret",
    ssl_ca="/etc/ssl/mariadb/ca.pem",
    ssl_cert="/etc/ssl/mariadb/client-cert.pem",
    ssl_key="/etc/ssl/mariadb/client-key.pem",
    ssl_verify_cert=True,
)
```

## Disabling TLS

Only for a trusted local socket or a private network:

```python
config = MariaDBConnectionConfig(
    host="localhost",
    database="myapp",
    username="app",
    password="secret",
    ssl_disabled=True,
)
```

With `ssl_disabled=True` none of the `ssl_*` or `tls_version` values are passed
to the driver.

## Environment

`from_env()` reads `MARIADB_SSL_DISABLED`, `MARIADB_TLS_VERSION`,
`MARIADB_SSL_CA`, `MARIADB_SSL_CERT`, `MARIADB_SSL_KEY`, `MARIADB_SSL_CIPHERS`,
`MARIADB_SSL_VERIFY_CERT` and `MARIADB_SSL_VERIFY_IDENTITY`. Boolean values are
parsed as `true` / `yes` / `1` / `on`.

> If the server rejects the handshake, check the server's `have_ssl` and the
> exact CA/certificate paths before changing SQL. See
> [Connection errors](../troubleshooting/connection.md).
