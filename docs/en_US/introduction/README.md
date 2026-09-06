# Introduction

## MariaDB Backend Overview

`rhosocial-activerecord-mariadb` is the MariaDB database backend implementation for the rhosocial-activerecord core library. It provides complete ActiveRecord pattern support, optimized specifically for MariaDB database features.

MariaDB is a community-developed fork of MySQL that is API-compatible but introduces unique features at different version boundaries. This backend provides first-class support for MariaDB-specific features such as:

- **RETURNING clause** (since MariaDB 10.5) -- supported for INSERT and DELETE, but not UPDATE
- **SEQUENCE** (since MariaDB 10.3) -- database-level sequence objects
- **INTERSECT / EXCEPT** (since MariaDB 10.3) -- set operations added earlier than MySQL
- **System-versioned tables** (since MariaDB 10.3) -- built-in temporal data support
- **Window functions** (since MariaDB 10.2)
- **Common Table Expressions** (since MariaDB 10.2)

The backend is responsible for three primary tasks:

- **SQL Dialect Generation** -- converting generic query builders into MariaDB-specific SQL statements
- **Data Type Mapping** -- handling MariaDB types including TINYINT through BIGINT, CHAR/VARCHAR/TEXT variants, DATE/TIME/DATETIME/TIMESTAMP, BINARY/VARBINARY/BLOB, JSON, ENUM, SET, and YEAR
- **Connection and Transaction Management** -- establishing TCP connections, executing START TRANSACTION/COMMIT/ROLLBACK, and managing MariaDB-specific behaviors like auto-increment and savepoints

## Synchronous and Asynchronous

The MariaDB backend provides both synchronous and asynchronous APIs that are functionally equivalent. The documentation uses synchronous examples throughout, but the asynchronous API usage is identical -- just replace method calls with their async equivalents.

### Naming Convention

| Component | Sync | Async |
|-----------|------|-------|
| Backend class | `MariaDBBackend` | `AsyncMariaDBBackend` |
| Transaction manager | `MariaDBTransactionManager` | `AsyncMariaDBTransactionManager` |
| Connection config | `MariaDBConnectionConfig` | `MariaDBConnectionConfig` (shared) |
| Dialect | `MariaDBDialect` | `MariaDBDialect` (shared) |

The connection config and dialect are shared between sync and async -- they are pure data objects, not active connections.

### Model Layer

| Operation | `ActiveRecord` (sync) | `AsyncActiveRecord` (async) |
|-----------|----------------------|----------------------------|
| Find one | `find_one()` | `async find_one()` |
| Find all | `find_all()` | `async find_all()` |
| Save | `save()` | `async save()` |
| Delete | `delete()` | `async delete()` |
| Query builder | `.query()` -> `ActiveQuery` | `.query()` -> `AsyncActiveQuery` |

The method names are identical across sync and async -- the distinction is at the class level, not the method level.

### Async Driver

MariaDB uses the same library for both sync and async (v2.0.0+):

| Backend | Sync Driver | Async Driver | Notes |
|---------|-------------|--------------|-------|
| MariaDB | `mariadb` | `mariadb` (asyncConnect) | Same library, v2.0.0+ |

If you import `AsyncMariaDBBackend` and the async driver is not installed, you will get an `ImportError` at import time.

## Quick Start

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, DefaultTimestampMixin
from rhosocial.activerecord.backend.impl.mariadb import (
    MariaDBBackend, AsyncMariaDBBackend, MariaDBConnectionConfig,
)

class User(UUIDMixin, DefaultTimestampMixin, ActiveRecord):
    username: str = Field(..., max_length=50)
    email: str
    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'

# Synchronous
config = MariaDBConnectionConfig(
    host='localhost', port=3306,
    database='myapp', username='user', password='password',
)
User.configure(config, MariaDBBackend)

user = User(username='tom', email='tom@example.com')
user.save()
found = User.query().where(User.c.username == 'tom').one()

# Asynchronous
User.configure(config, AsyncMariaDBBackend)
user = await User(username='tom', email='tom@example.com').save()
```

## Relationship with Core Library

rhosocial-activerecord uses a modular design where the core library provides database-agnostic ActiveRecord implementations, and database backends exist as separate extension packages. The MariaDB backend's namespace is `rhosocial.activerecord.backend.impl.mariadb`, at the same level as other backends.

```
rhosocial.activerecord
├── backend.impl.sqlite      # SQLite backend
├── backend.impl.dummy       # Dummy backend for testing
├── backend.impl.mysql       # MySQL backend
└── backend.impl.mariadb     # MariaDB backend (this package)
    ├── MariaDBBackend
    ├── AsyncMariaDBBackend
    └── ...
```

Backends do not participate in ActiveRecord layer changes -- they strictly follow backend interface protocols. Backend updates are decoupled from the core library's ActiveRecord functionality.

## Differences from MySQL

MariaDB is API-compatible with MySQL but has important differences that affect the backend:

| Feature | MySQL | MariaDB |
|---------|-------|---------|
| RETURNING clause | Not supported | Supported for INSERT/DELETE (10.5+), **not** for UPDATE |
| INTERSECT/EXCEPT | Not supported | Supported since 10.3 |
| SEQUENCE | Not supported | Supported since 10.3 |
| System-versioned tables | Not supported | Supported since 10.3 |
| Window functions | Since 8.0 | Since 10.2 |
| CTE | Since 8.0 | Since 10.2 |
| MERGE statement | Not supported | Not supported |
| `OR REPLACE` DDL | Limited | Supported for tables, triggers, routines |
| `CREATE TABLE ... IF NOT EXISTS` | Yes | Yes |
| `EXPLAIN FORMAT=TREE` | Supported (8.0+) | Not supported |
| `CUBE` / `GROUPING SETS` | Supported | Not supported |
| Schema layer | No (schema = database) | No (schema = database) |
| LATERAL joins | Supported (8.0+) | Supported |
| `FOR UPDATE SKIP LOCKED` | Supported (8.0+) | Supported (10.3+) |

## Known Limitations and Quirks

Every database has behavior that differs from the SQL standard. This section documents MariaDB-specific quirks that may surprise you.

| Quirk | Description |
|-------|-------------|
| RETURNING not for UPDATE | RETURNING works for INSERT/DELETE/REPLACE (10.5+) but NOT for UPDATE |
| REPLACE INTO changes AUTO_INCREMENT | Deletes and re-inserts rows, changing AUTO_INCREMENT values |
| System-versioned tables | 10.3+ supports `WITH SYSTEM VERSIONING` for temporal data |
| OR REPLACE | Supports `CREATE OR REPLACE` for tables, triggers, and routines |
| Version boundaries differ from MySQL | CTEs since 10.2, window functions since 10.2, etc. |
| No MERGE statement | Use `INSERT ... ON DUPLICATE KEY UPDATE` instead |
| No CUBE/GROUPING SETS | MariaDB does not support these grouping operations |
| No materialized CTE | `MATERIALIZED` hint is not supported |
| No QUALIFY clause | Use a subquery or CTE instead |

AI Prompt: "What is the ActiveRecord pattern? How does it differ from DataMapper pattern?"
