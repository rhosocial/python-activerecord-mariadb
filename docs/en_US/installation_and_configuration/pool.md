# Connection Management

## Connect-on-Use Lifecycle

The MariaDB backend uses a connect-on-use pattern. Connections are established lazily when the first query is executed and remain open until explicitly closed or the backend is garbage collected.

```python
backend = MariaDBBackend(connection_config=config)
backend.connect()
# Connection is now open
backend.disconnect()
# Connection is closed
```

## Context Manager

Use the context manager for automatic connection management:

```python
with backend:
    # Connection is open
    pass
# Connection is automatically closed
```

## Connection Pooling

Connection pooling is available as an optional feature via the DBUtils package:

```bash
pip install "rhosocial-activerecord-mariadb[pooling]"
```

This installs `DBUtils>=3.0.0` which provides `PooledDB`.

### Configuring Pool Size

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

## FastAPI Pattern

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

## Multiple Backends

You can create multiple backends for different databases or connection profiles:

```python
# Read replica
read_config = MariaDBConnectionConfig(
    host='replica-db.example.com',
    port=3306,
    database='myapp',
    username='readonly',
    password='password',
)

# Write primary
write_config = MariaDBConnectionConfig(
    host='primary-db.example.com',
    port=3306,
    database='myapp',
    username='admin',
    password='password',
)
```

AI Prompt: "How do I manage connections in a FastAPI application?"
