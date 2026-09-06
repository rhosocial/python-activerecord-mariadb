# BackendGroup and BackendManager (MariaDB)

This document describes how to use `BackendGroup` and `BackendManager` with the MariaDB backend. For detailed API documentation, refer to the [core library documentation](../../../rhosocial-activerecord/docs/en_US/connection/connection_management.md).

## Quick Example

```python
from rhosocial.activerecord.connection import BackendGroup
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    name: str
    email: str


# Using context manager
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

# Using with multiple groups via BackendManager
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

## MariaDB-Specific Features

### Connection Pool Configuration

The MariaDB backend recognizes pool-related config fields:

```python
config = MariaDBConnectionConfig(
    host="localhost",
    port=3306,
    database="myapp",
    username="app",
    password="secret",
    pool_size=10,          # Requires DBUtils
    pool_timeout=30,
)
```

> **Note**: The `mariadb` Python driver has `threadsafety=1`. A single connection must not be shared across threads. Use multi-process or a request-level `BackendGroup` for concurrency.

### SSL/TLS Configuration

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

## Example Code

Full example: [chapter_02_connection_pool/async_connection_pool.py](../examples/chapter_02_connection_pool/async_connection_pool.py)

This example demonstrates using backend connection management in a multi-worker FastAPI application.
