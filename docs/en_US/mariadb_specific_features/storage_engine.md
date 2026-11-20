<!-- docs/en_US/mariadb_specific_features/storage_engine.md -->
# Storage engines

A MariaDB table's storage engine determines its transaction, locking and
indexing behaviour. The backend exposes the engine as a table option in both
declarative DDL and hand-written `CREATE TABLE` expressions.

## Choosing an engine

- **InnoDB** — the default and the right choice for almost all application
  tables: transactions, row-level locking, foreign keys and crash recovery.
- **MyISAM / Aria / MEMORY** — available for read-heavy, temporary or special
  workloads, but they do not provide InnoDB's transactional guarantees. Choose
  them deliberately.

`ENGINE` is rendered by the backend's table-option formatter. Query the server
for the engines it actually has with `SHOW ENGINES` (`introspector.show`) — a
plugin may not be installed on every deployment.

## Table options in declarative DDL

```python
from rhosocial.activerecord.backend.impl.mariadb.expression import MariaDBCreateTableOptions

options = MariaDBCreateTableOptions(
    dialect,
    engine="InnoDB",
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
)
```

The same options object is accepted by `CreateTableStatement`:

```python
from rhosocial.activerecord.backend.expression import CreateTableStatement
from rhosocial.activerecord.backend.expression.objects import Table

stmt = CreateTableStatement(
    dialect=dialect,
    table=Table(dialect, "orders"),
    columns=columns,
    indexes=indexes,
    if_not_exists=True,
    table_options=options,
)
sql, params = stmt.to_sql()
# CREATE TABLE IF NOT EXISTS `orders` (...) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ...
```

## Inspecting the engine in use

`get_table_options("orders")` reports the engine, row format, collation and
auto-increment counter from `information_schema.TABLES`:

```python
options = backend.introspector.get_table_options("orders")
if options:
    print(options.engine, options.row_format, options.collation, options.auto_increment)
```

For a view or a sequence the same accessor answers too — the record carries
`table_type`, so the caller can decide whether the answer is the one wanted.

## Transactions and engine choice

`transaction()` controls commits at the SQL layer, but an engine that does not
support transactions cannot honour a rollback. Keep tables that participate in
units of work on InnoDB, and see
[Transaction Support](../transaction_support/README.md).
