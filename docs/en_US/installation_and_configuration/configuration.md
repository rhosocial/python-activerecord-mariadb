# Connection Configuration

## Basic Configuration

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

## Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | `str` | `'localhost'` | Database server hostname |
| `port` | `int` | `3306` | Database server port |
| `database` | `str` | `None` | Database name |
| `username` | `str` | `None` | Authentication username |
| `password` | `str` | `''` | Authentication password |
| `charset` | `str` | `'utf8mb4'` | Connection character set |
| `collation` | `str` | `None` | Connection collation |
| `autocommit` | `bool` | `False` | Enable autocommit mode |
| `ssl_disabled` | `bool` | `False` | Disable SSL connections |
| `pool_size` | `int` | `None` | Connection pool size (requires DBUtils) |
| `pool_timeout` | `int` | `None` | Pool connection timeout (seconds) |
| `version` | `tuple` | `None` | MariaDB version tuple (major, minor, patch) |
| `options` | `dict` | `{}` | Additional connection parameters |

## Environment Variables

Configuration can be loaded from environment variables with the `MARIADB_` prefix:

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

## Version Specification

The dialect adapts behavior based on the MariaDB version. You can specify the version explicitly or let the backend detect it automatically:

```python
# Explicit version
config = MariaDBConnectionConfig(
    host='localhost',
    database='myapp',
    version=(10, 11, 0),
)

# Auto-detect version (requires connection)
backend = MariaDBBackend(connection_config=config)
backend.connect()
backend.introspect_and_adapt()  # Detects version from server
```

AI Prompt: "How do I configure MariaDB connection pooling?"
