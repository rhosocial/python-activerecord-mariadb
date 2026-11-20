<!-- docs/examples/chapter_06_connection/README.md -->
# Chapter 6 — Connection

`connection.py` is the smallest end-to-end example: build a
`MariaDBConnectionConfig`, bind a declarative model to `MariaDBBackend`, create
the table, run CRUD inside a transaction, preview generated SQL, and clean up.

## Run

```powershell
$env:MARIADB_HOST='127.0.0.1'; $env:MARIADB_DATABASE='test_db'
$env:MARIADB_USERNAME='app'; $env:MARIADB_PASSWORD='secret'
python docs/examples/chapter_06_connection/connection.py
```

The model's `table_name()` is `docs_example_users`; the script drops that table
at the end.

## What to look for

- `MariaDBConnectionConfig(...)` carries host/port/database/credentials.
- `User.configure(config, MariaDBBackend)` binds the model to this backend.
- `User.create_table()` renders `AUTO_INCREMENT` and backtick-quoted identifiers.
- `with backend.transaction(): ...` wraps the write; an exception rolls back.
- `.to_sql()` shows the statement before it is executed.
