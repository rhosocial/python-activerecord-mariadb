<!-- docs/examples/chapter_04_ddl/README.md -->
# Chapter 4 — DDL

`ddl.py` builds DDL with statement-level expressions so MariaDB-specific table
options can be shown explicitly: `ENGINE=InnoDB`, `CHARSET=utf8mb4`, an inline
index, an `ALTER TABLE ... ADD COLUMN`, and `DROP TABLE`.

## Run

```powershell
$env:MARIADB_HOST='127.0.0.1'; $env:MARIADB_DATABASE='test_db'
$env:MARIADB_USERNAME='app'; $env:MARIADB_PASSWORD='secret'
python docs/examples/chapter_04_ddl/ddl.py
```

The table is named `docs_example_products` and is dropped at the end (and at
the start, for a clean run).

## What to look for

- `MariaDBCreateTableOptions(dialect, engine=..., charset=...)` supplies the
  MariaDB table suffix.
- `IndexDefinition` adds an inline secondary index inside `CREATE TABLE`.
- `ColumnConstraint` carries `PRIMARY KEY`, `NOT NULL` and `DEFAULT` constraints.
- Every statement is printed via `.to_sql()` before it is executed.
- `backend.introspector.list_columns(...)` verifies what the server stored.
