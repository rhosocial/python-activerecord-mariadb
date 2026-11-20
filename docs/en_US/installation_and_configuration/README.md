<!-- docs/en_US/installation_and_configuration/README.md -->
# Installation & Configuration

This chapter covers installing the backend distribution, describing a connection
with `MariaDBConnectionConfig`, binding it to a model with `configure()`, and the
connection/SSL/charset behaviour that is specific to this backend.

## Chapters

- [Installation](installation.md)
- [Connection configuration](configuration.md)
- [SSL/TLS](ssl.md)
- [Connection management](pool.md)
- [Character set & collation](charset.md)

A minimal setup:

```python
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host="localhost", port=3306,
    database="myapp", username="app", password="secret",
    charset="utf8mb4",
)
backend = MariaDBBackend(connection_config=config)
backend.connect()  # optional: connections are also opened lazily on use
```
