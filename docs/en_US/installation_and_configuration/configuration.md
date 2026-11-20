<!-- docs/en_US/installation_and_configuration/configuration.md -->
# Connection configuration

`MariaDBConnectionConfig` is a dataclass that gathers the core connection fields
and the mixins this backend uses: pool, SSL, charset, timezone, version and
logging.

## Constructing a config

```python
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host="localhost",
    port=3306,
    database="myapp",
    username="app",
    password="secret",
    charset="utf8mb4",
    autocommit=False,
    timezone="UTC",
    ssl_disabled=False,
    tls_version="TLSv1.3",
)
```

### Core connection fields

| Field | Meaning |
|-------|---------|
| `host` | Server host name or socket path |
| `port` | TCP port (default MariaDB port is 3306) |
| `database` | Database selected on connect |
| `username` / `password` | Credentials |

### MariaDB-specific and mixin fields

| Field | Meaning |
|-------|---------|
| `autocommit` | Driver autocommit flag; `False` by default so `transaction()` controls commits |
| `charset` | Emitted as `SET NAMES <charset>` in the driver's `init_command` |
| `collation` | Collation passed through to the connection setup where supported |
| `timezone` | Timezone used when adapting temporal values |
| `pool_size` / `pool_timeout` | Core pool mixin fields (see [Connection management](pool.md)) |
| `ssl_disabled` | `False` by default: the backend asks for TLS unless explicitly disabled |
| `tls_version` | Minimum TLS version passed to the driver |
| `ssl_ca` / `ssl_cert` / `ssl_key` / `ssl_ciphers` | Certificate material for TLS and mutual TLS |
| `ssl_verify_cert` / `ssl_verify_identity` | Peer and host verification switches |
| `options` | Free-form dict for driver-specific options |

`to_dict()` returns the configuration including `autocommit`, `ssl_disabled` and
`tls_version`. `get_connection_params()` builds the driver keyword arguments —
this is the single place where the generic field names are mapped to the
`mariadb` connector's names (`user`, `init_command`, `ssl_ca`, and so on).

## Environment variables

`MariaDBConnectionConfig.from_env()` reads `MARIADB_`-prefixed variables by
default:

```python
config = MariaDBConnectionConfig.from_env()
```

Recognised names include `MARIADB_HOST`, `MARIADB_PORT`, `MARIADB_DATABASE`,
`MARIADB_USERNAME`, `MARIADB_PASSWORD`, `MARIADB_CHARSET`, `MARIADB_COLLATION`,
`MARIADB_AUTOCOMMIT`, `MARIADB_SSL_DISABLED`, `MARIADB_TLS_VERSION`, and the
`MARIADB_SSL_*` certificate variables. Boolean values accept `true`, `yes`, `1`
and `on`. Pass `prefix=` to use a different prefix.

## Binding to models

```python
User.configure(config, MariaDBBackend)
```

For version-gated introspection, make the backend adapt to the connected server
first:

```python
backend = User.__backend__
backend.introspect_and_adapt()
print(backend.dialect.get_server_version())
```

## Direct backend use

When working at the expression layer without models:

```python
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend

backend = MariaDBBackend(connection_config=config)
backend.connect()
# ... backend.execute(sql, params) ...
backend.disconnect()
```

See [SSL/TLS](ssl.md) and [Character set & collation](charset.md) for the
details those fields control.
