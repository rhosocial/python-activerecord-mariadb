<!-- README.md -->
# rhosocial-activerecord-mariadb ($\rho_{\mathbf{AR}\text{-mariadb}}$)

[![PyPI version](https://badge.fury.io/py/rhosocial-activerecord-mariadb.svg)](https://badge.fury.io/py/rhosocial-activerecord-mariadb)
[![Python](https://img.shields.io/pypi/pyversions/rhosocial-activerecord-mariadb.svg)](https://pypi.org/project/rhosocial-activerecord-mariadb/)
[![Tests](https://github.com/rhosocial/python-activerecord-mariadb/actions/workflows/test.yml/badge.svg)](https://github.com/rhosocial/python-activerecord-mariadb/actions)
[![Coverage Status](https://codecov.io/gh/rhosocial/python-activerecord-mariadb/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rhosocial/python-activerecord-mariadb/tree/main)
[![Apache 2.0 License](https://img.shields.io/github/license/rhosocial/python-activerecord-mariadb.svg)](https://github.com/rhosocial/python-activerecord-mariadb/blob/main/LICENSE)
[![Supported MariaDB versions](https://img.shields.io/badge/MariaDB-10.2%7C10.3%7C10.4%7C10.5%7C10.6%7C10.11%7C11.4%7C11.7%7C11.8%7C12.0%7C12.2%7C12.3%7C13.0%7C13.1--rc-blue?logo=mariadb)](https://github.com/rhosocial/python-activerecord/blob/main/docs/en_US/introduction/supported_versions.md)

<div align="center">
    <img src="https://raw.githubusercontent.com/rhosocial/python-activerecord/main/docs/images/logo.svg" alt="rhosocial ActiveRecord Logo" width="200"/>
    <h3>MariaDB Backend for rhosocial-activerecord</h3>
    <p><b>System versioning · RETURNING · Sequences · Sync &amp; async</b></p>
</div>

This is a backend implementation for [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord).
It cannot be used standalone.

**Keywords:** orm, activerecord, pydantic, python, mariadb, async, backend, type-safe

## Why This Project?

- **MariaDB-native, not a lowest-common-denominator layer.** System-versioned tables, sequences, `RETURNING`, full-text search, JSON operators, and MariaDB's type set are first-class.
- **Version-aware SQL.** The dialect checks the connected server version before emitting newer syntax, and resolves the `utf8` alias to a fixed meaning so one DDL statement yields one schema across releases.
- **The same API, sync or async.** `MariaDBBackend` and `AsyncMariaDBBackend` share method names and patterns; the async variant just adds `await`.
- **Declarative models.** Annotate fields with `UseSqlType(...)` and let the core build DDL — no hand-written `CREATE TABLE` expressions needed.

## Quick Start

### Installation

```bash
pip install rhosocial-activerecord-mariadb
```

Requires Python 3.8+, the `mariadb` connector (`>=2.0.0rc2`), and a reachable MariaDB server with an existing database. The example below uses the `MariaDBBackend` shipped by this package.

### End-to-End Example

```python
"""Save as demo.py and run with: python demo.py"""
from typing import Annotated, ClassVar

from rhosocial.activerecord.base import FieldProxy, UseSqlType
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.field import DefaultTimestampMixin, IntegerPKMixin
from rhosocial.activerecord.model import ActiveRecord


class User(
    IntegerPKMixin,         # auto-increment integer primary key (`id`)
    DefaultTimestampMixin,  # injects `created_at` / `updated_at` timestamps
    ActiveRecord,           # persistence, query builder, relations
):
    name: Annotated[str, UseSqlType(VarCharType(length=100))]
    email: Annotated[str, UseSqlType(VarCharType(length=255))]
    age: int = 0

    c: ClassVar[FieldProxy] = FieldProxy()  # enables User.c.<field> expressions

    @classmethod
    def table_name(cls) -> str:
        return "users"


# Configure the backend and create the table from the model declaration
User.configure(
    MariaDBConnectionConfig(
        host="localhost",
        port=3306,
        database="myapp",
        username="user",
        password="password",
    ),
    MariaDBBackend,
)
User.create_table()

# Create
alice = User(name="Alice", email="alice@example.com", age=30)
alice.save()
print(alice.id)  # database-assigned AUTO_INCREMENT primary key

# Query with type-safe expressions
adults = User.query().where(User.c.age >= 18).all()
print([user.name for user in adults])

# Inspect the generated SQL without executing it
sql, params = User.query().where(User.c.age >= 18).to_sql()
print(sql, params)  # SELECT ... FROM `users` WHERE `users`.`age` >= ?   (18,)
```

> **Async parity:** use `AsyncActiveRecord` with `AsyncMariaDBBackend` (from the same
> `rhosocial.activerecord.backend.impl.mariadb.backend` package) — same method names,
> same patterns, just add `await`.

## Project Architecture

```
Your Code
   ↓
Interface      models, field proxies, mixins, query builders, events
   ↓
ActiveRecord   lifecycle, persistence, relations
   ↓
Expressions    backend-agnostic declarations → generic statements
   ↓
Dialect        binds expressions to MariaDB SQL, version-aware
   ↓
Driver         `mariadb` connector → MariaDB server
```

For the full picture, start with the [Documentation](https://github.com/rhosocial/python-activerecord/blob/main/docs/en_US/README.md).

**MariaDB highlights.** The dialect owns MariaDB-specific SQL: `AUTO_INCREMENT`, system versioning, sequences, `RETURNING`, full-text predicates, JSON rendering, and engine/charset table options. It resolves the `utf8` alias before emitting DDL and quotes identifiers against a version-aware reserved-word list, so one declaration produces one predictable schema across server releases. Query structure stays decoupled from SQL generation — nothing is rendered until an explicit `.to_sql()` call, so you can preview and verify every statement before it runs.

**True sync–async parity.** Both implementations are native, not async wrappers around sync code. Method names and patterns are identical; the async variant just adds `await`.

## Backend Support & Progress

This package ships as a separate distribution from the core library. It targets MariaDB 10.2, 10.3, 10.4, 10.5, 10.6, 10.11, 11.4, 11.7, 11.8, 12.0, 12.2, 12.3, 13.0 and 13.1-rc — the releases covered by CI. The full list and the policy behind it are in [Supported MariaDB versions](https://github.com/rhosocial/python-activerecord/blob/main/docs/en_US/introduction/supported_versions.md).

There is no upper bound: the backend does not reject a version it has not seen. Feature gates resolve to *enabled* when the server is newer than a feature's introduction version, so **new syntax is assumed available**; if that assumption is wrong the server rejects the statement. Removals are handled per feature — a function dropped in a later release reports itself unsupported. 12.3 is the recommended baseline (LTS, maintained to June 2029); 13.1 is a release candidate and not recommended for production.

> **⚠️ Development Stage:** This project is under active development. APIs may change, and some features are not yet production-ready.

## Documentation

### Contributing

We welcome contributions! Please see [CONTRIBUTING.md](https://github.com/rhosocial/python-activerecord/blob/main/CONTRIBUTING.md) for guidelines.

### License

[Apache License 2.0](LICENSE) — Copyright © 2026 [vistart](https://github.com/vistart)

### Documentation

* **[Documentation Home](https://github.com/rhosocial/python-activerecord/blob/main/docs/en_US/README.md)** — the full documentation table of contents
* **[Supported MariaDB versions](https://github.com/rhosocial/python-activerecord/blob/main/docs/en_US/introduction/supported_versions.md)** — CI-covered releases and the version policy
* **[Database introspection](docs/introspection.md)** — what this backend answers, where each answer comes from, and its version floors
* **[Architecture notes](.claude/architecture.md)** — backend design decisions
* **[Testing notes](.claude/testing.md)** — running the MariaDB-backed tests
* **[Core library documentation](https://github.com/rhosocial/python-activerecord/tree/main/docs)** — ActiveRecord and the core API
