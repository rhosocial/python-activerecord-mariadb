<!-- docs/en_US/installation_and_configuration/pool.md -->
# Connection management

## Connect-on-use

`MariaDBBackend` opens a driver connection when `connect()` is called, but it
also reconnects lazily: statement execution checks for a live connection and
reopens it when needed. A failed statement triggers one reconnect attempt before
the error is propagated. This makes a backend instance safe to keep around
across idle periods.

```python
backend = MariaDBBackend(connection_config=config)
backend.connect()
result = backend.execute("SELECT 1", ())
backend.disconnect()
```

`disconnect()` closes the active connection; the next statement reconnects on
demand. Transaction state is per connection — a reconnect ends the current
transaction, so keep units of work short.

## Pool fields

`MariaDBConnectionConfig` inherits `ConnectionPoolMixin`, so `pool_size` and
`pool_timeout` are accepted as configuration fields and are read from
`MARIADB_POOL_SIZE` / `MARIADB_POOL_TIMEOUT` by `from_env()`. The backend itself
uses connect-on-use; if your deployment needs a pooled driver connection, use
the optional `DBUtils` extra (`pip install "...[pooling]"`) and manage the pool
through the connector, passing any driver-level settings through `options`.

```python
config = MariaDBConnectionConfig(
    host="localhost",
    database="myapp",
    username="app",
    password="secret",
    pool_size=5,
    pool_timeout=30,
)
```

## Async backend

`AsyncMariaDBBackend` mirrors the same lifecycle with `await`:

```python
from rhosocial.activerecord.backend.impl.mariadb.backend import AsyncMariaDBBackend

backend = AsyncMariaDBBackend(connection_config=config)
await backend.connect()
# ... await backend.execute(...)
await backend.disconnect()
```

Both backends feed the same `get_connection_params()` mapping, so TLS, charset
and the other settings behave identically.

## Worker processes

Connections are not shared across processes. Give each worker its own backend
instance (or configure models in the worker), and let connect-on-use establish
the connection there. See the
[core worker-pool documentation](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US/worker_pool)
for the lifecycle hooks.
