# Test Configuration

## Overview

This section describes how to configure the testing environment for the MariaDB backend.

For general testing strategies (DummyBackend, SQLite integration testing), see the [Core Backend Testing Guide](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/testing/backend_testing.md).

## End-to-End Testing with MariaDB Backend

For complete MariaDB behavior testing, use the MariaDB backend:

```python
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig


class User(ActiveRecord):
    name: str
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'


# Read configuration from environment variables
config = MariaDBConnectionConfig(
    host=os.environ.get('MARIADB_HOST', 'localhost'),
    port=int(os.environ.get('MARIADB_PORT', 3306)),
    database=os.environ.get('MARIADB_DATABASE', 'test'),
    username=os.environ.get('MARIADB_USERNAME', 'root'),
    password=os.environ.get('MARIADB_PASSWORD', ''),
)
User.configure(config, MariaDBBackend)
```

## Test Fixtures

```python
import pytest
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig


@pytest.fixture
def mariadb_config():
    return MariaDBConnectionConfig(
        host='localhost',
        port=3306,
        database='test',
        username='root',
        password='password',
    )


@pytest.fixture
def mariadb_backend(mariadb_config):
    backend = MariaDBBackend(connection_config=mariadb_config)
    backend.connect()
    yield backend
    backend.disconnect()


def test_connection(mariadb_backend):
    version = mariadb_backend.get_server_version()
    assert version is not None
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MARIADB_HOST` | `localhost` | Server host |
| `MARIADB_PORT` | `3306` | Server port |
| `MARIADB_DATABASE` | `test` | Database name |
| `MARIADB_USERNAME` | `root` | Username |
| `MARIADB_PASSWORD` | `` | Password |

💡 *AI Prompt:* "What is the difference between unit tests, integration tests, and end-to-end tests?"
