<!-- docs/en_US/ddl/README.md -->
# DDL Operations

DDL is available at two levels:

1. **Model-driven** — declare fields with `UseSqlType(...)` and call
   `Model.create_table()`. The core builds a portable statement and the MariaDB
   dialect renders it.
2. **Statement-level** — build `CreateTableStatement`, `AlterTableStatement`,
   `DropTableStatement`, index and view expressions directly when you need
   MariaDB-specific table options.

Modeling itself belongs to the
[core library manual](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US/modeling);
this page only covers what this backend renders.

## Model-driven DDL

```python
from typing import Annotated, ClassVar

from rhosocial.activerecord.base import FieldProxy, UseSqlType
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.model import ActiveRecord


class Product(ActiveRecord, IntegerPKMixin):
    name: Annotated[str, UseSqlType(VarCharType(length=200))]

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "products"


Product.configure(config, MariaDBBackend)
Product.create_table()
```

The integer primary key becomes `AUTO_INCREMENT`, `name` becomes
`VARCHAR(200)`, and identifiers are quoted with backticks.

## Statement-level DDL with MariaDB options

```python
from rhosocial.activerecord.backend.expression import CreateTableStatement
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.mariadb.expression import MariaDBCreateTableOptions

stmt = CreateTableStatement(
    dialect=dialect,
    table=Table(dialect, "products"),
    columns=columns,
    indexes=indexes,
    if_not_exists=True,
    table_options=MariaDBCreateTableOptions(dialect, engine="InnoDB", charset="utf8mb4"),
)
sql, params = stmt.to_sql()
backend.execute(sql, params)
```

The backend also provides expressions for `ALTER TABLE`, `RENAME TABLE`,
`TRUNCATE`, views, indexes, sequences, routines, trigger and partition DDL
under `...impl.mariadb.expression`.

## DDL and transactions

MariaDB DDL causes an implicit commit. A statement-level report therefore
describes what one statement did, not something that can be rolled back with
the surrounding transaction. See
[Transaction Support](../transaction_support/README.md).

## Runnable example

[`examples/chapter_04_ddl/ddl.py`](../../examples/chapter_04_ddl/ddl.py) creates
and alters a table with the MariaDB backend, then inspects the result.
