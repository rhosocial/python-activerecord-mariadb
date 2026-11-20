<!-- docs/en_US/introduction/relationship.md -->
# Relationship with the core library

This backend is a plugin, not a fork. The division of labour is:

| Concern | Owner |
|---------|-------|
| Models, field proxies, mixins, validation | core (`rhosocial-activerecord`) |
| Query builders, relations, events, worker pool | core |
| Expression objects and generic statement classes | core |
| MariaDB rendering of those expressions | this backend's dialect and mixins |
| MariaDB-only expressions (partition, JSON, spatial, sequence, etc.) | this backend |
| Driver connection and result adaptation | this backend (`mariadb` connector) |
| Type adapters for MariaDB column types | this backend |
| Introspector and SHOW/status passthroughs | this backend |

A model declares *what* it stores; the dialect decides *how* MariaDB spells it.
For example, `UseSqlType(VarCharType(length=100))` is a core declaration, while
the `VARCHAR(100)` text, backtick quoting and `ENGINE`/`CHARSET` suffix come
from this backend.

## Wiring a model to the backend

```python
from typing import Annotated, ClassVar

from rhosocial.activerecord.base import FieldProxy, UseSqlType
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.field import DefaultTimestampMixin, IntegerPKMixin
from rhosocial.activerecord.model import ActiveRecord


class User(IntegerPKMixin, DefaultTimestampMixin, ActiveRecord):
    name: Annotated[str, UseSqlType(VarCharType(length=100))]
    email: Annotated[str, UseSqlType(VarCharType(length=255))]
    age: int = 0

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "users"


User.configure(
    MariaDBConnectionConfig(
        host="localhost", port=3306,
        database="myapp", username="app", password="secret",
    ),
    MariaDBBackend,
)
User.create_table()
```

`configure()` binds the model to the backend class; the connection itself is
opened lazily on first use. To make version-gated probes answer for the actual
server before asking them, call `User.__backend__.introspect_and_adapt()`.

## What is intentionally *not* here

Modeling, querying, relationships, serialization and the generic expression
system are documented in the
[core library manual](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US).
This manual links to it where a backend page depends on a core contract rather
than repeating the contract.
