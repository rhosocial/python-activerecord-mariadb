<!-- docs/examples/README.md -->
# Example scripts

Runnable MariaDB examples for the documentation. Each script uses the MariaDB
backend from this repository and a real MariaDB server — no portable-database
fallback.

They are syntax-checked in CI with `python -m py_compile`, but they need a live
server and credentials to execute. Set the connection variables before running:

```powershell
$env:MARIADB_HOST = '127.0.0.1'
$env:MARIADB_PORT = '3306'
$env:MARIADB_DATABASE = 'test_db'
$env:MARIADB_USERNAME = 'app'
$env:MARIADB_PASSWORD = 'secret'
python docs/examples/chapter_06_connection/connection.py
```

> The scripts create and drop their own tables, using a dedicated test database.
> Do not point them at a production database.

## Chapters

| Directory | What it demonstrates |
|-----------|----------------------|
| [chapter_06_connection](chapter_06_connection/README.md) | Connection config, declarative model, CRUD, transaction, SQL preview |
| [chapter_04_ddl](chapter_04_ddl/README.md) | `CREATE`/`ALTER`/`DROP` table with MariaDB table options and indexes |
| [chapter_05_introspection](chapter_05_introspection/README.md) | Schema, operational and MariaDB-specific introspection families |

These scripts illustrate backend-specific behaviour. For modeling and querying
patterns, see the
[core library documentation](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US).
