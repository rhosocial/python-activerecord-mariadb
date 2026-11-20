<!-- docs/examples/migration/README.md -->
# Migration examples (MariaDB)

Runnable MariaDB examples for the backend-specific migration notes in
[`docs/en_US/migration/README.md`](../../en_US/migration/README.md). The
migration system itself is documented in the
[core library's migration chapter](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US/migration)
— these scripts only show how this backend is wired into it.

Both scripts require a **live MariaDB server** and an existing database. There is
no portable-database fallback. They are syntax-checked in CI with
`python -m py_compile`, but are not executed there. Set the connection variables
before running:

```powershell
$env:MARIADB_HOST = '127.0.0.1'
$env:MARIADB_PORT = '3306'
$env:MARIADB_DATABASE = 'test_db'
$env:MARIADB_USERNAME = 'app'
$env:MARIADB_PASSWORD = 'secret'
$env:PYTHONPATH = 'src'
python docs/examples/migration/01_function_migration.py
python docs/examples/migration/02_named_migration_cli.py
```

| Script | Demonstrates |
|---|---|
| [`01_function_migration.py`](01_function_migration.py) | `@migration` classmethod, `MariaDBConnectionConfig`, version gates, dry run → UP → DOWN via `run_migration_group` |
| [`02_named_migration_cli.py`](02_named_migration_cli.py) | class-style `MigrationRunner` with the bundled `NamedMigration` class, plus the equivalent `named-migration` CLI commands |

> The scripts create and drop their own tables and write a temporary JSON record
> store. Point them at a dedicated test database, never a production one.

## More class-style demos

The backend ships longer-running named-migration demos under
`src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/`
(`run_basic.py`, `run_chain.py`, `run_basic_async.py`, and the `demo_*.sh` CLI
scripts). They use the same classes and named expressions that
`02_named_migration_cli.py` drives programmatically.
