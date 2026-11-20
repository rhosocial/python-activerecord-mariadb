<!-- docs/en_US/migration/README.md -->
# Migrations on MariaDB

> **Scope.** This is a *backend addendum*, not the migration system manual. The
> architecture, vocabulary, ordering rules, dry-run capture, record stores,
> exceptions, and the `migrate` CLI are documented in the
> [core migration chapter](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US/migration).
> Read that first. This page only answers: *what is different when the migration
> target is MariaDB?*
>
> Every example here uses the `MariaDBBackend` shipped in this repository and a
> live MariaDB server. Runnable scripts are collected in
> [`docs/examples/migration/`](../../examples/migration/README.md).

## 1. Two APIs, one backend

The two authoring paths described in the core chapter are both available here:

| Path | Entry point | Where to wire this backend |
|---|---|---|
| Function style (recommended) | `@migration` + `run_migration_group()` | pass a connected `MariaDBBackend` as the first argument |
| Class style (legacy-compatible) | `NamedMigration` + `named-migration` CLI | the backend CLI builds `MariaDBBackend` for you |

Do not re-learn the system from this table — it is only a map of *where MariaDB
enters the picture*. Shared pieces (`MigrationContext`, `MigrationDirection`,
`MigrationRecordStore`, the typed exceptions) behave exactly as the core chapter
describes.

## 2. Configuring MariaDB for a migration run

A migration run needs a connected backend whose dialect knows the *connected*
server version. The connection class is `MariaDBConnectionConfig` from this
repository:

```python
import os

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host=os.getenv("MARIADB_HOST", "localhost"),
    port=int(os.getenv("MARIADB_PORT", "3306")),
    database=os.getenv("MARIADB_DATABASE", "test_db"),
    username=os.getenv("MARIADB_USERNAME", "app"),
    password=os.getenv("MARIADB_PASSWORD", ""),
    charset="utf8mb4",
    autocommit=False,
)
backend = MariaDBBackend(connection_config=config)
backend.connect()
backend.introspect_and_adapt()
```

`introspect_and_adapt()` is not optional for migrations: it is the step that
makes version gates and introspection answer for the live server. The class-style
CLI does it inside its backend factory; hand-written scripts must do it
themselves. See [Connection configuration](../installation_and_configuration/configuration.md)
for the full set of options (TLS, pool, timezone, `from_env()`).

For the function path the backend is passed explicitly to
`run_migration_group(backend, ...)`. For the class path the CLI takes connection
flags (`--host`, `--port`, `--database`, `--user`, `--password`) or the matching
`MARIADB_*` environment variables.

## 3. DDL is not transactional — the critical caveat

MariaDB implicitly commits `CREATE`, `ALTER`, `DROP`, and partition-maintenance
statements. This backend reports that fact faithfully:

```python
assert backend.dialect.supports_transactional_ddl() is False
```

Consequences for migrations (all of them follow from that one fact):

- **No DDL rollback.** Wrapping a migration in `backend.transaction()` does not
  make its DDL reversible. A `DOWN` migration must emit explicit inverse
  statements (`DROP TABLE`, `DROP INDEX`, ...) — it is a new forward run in the
  opposite direction, not an undo log replay.
- **Partial application is possible.** If a multi-statement migration fails
  halfway, the earlier statements are already committed. The core writes a
  version record only on success, so the version will *not* be marked applied;
  clean up the leftover objects yourself before retrying. Treat each migration
  as one logical change and keep statement counts small.
- **Prefer idempotent spellings.** `if_exists=True` on a drop statement and
  `IF NOT EXISTS` on a create statement make manual recovery and re-runs safer.
- **Preview before applying.** `dry_run=True` renders every statement without
  touching the server; this is the cheapest way to inspect the DDL a MariaDB
  dialect will actually emit. See the core chapter for what the two capture
  paths cover.
- **Records are the source of truth.** Because there is no transactional guard,
  the `MigrationRecordStore` is what decides whether a version is considered
  applied. Keep it outside the database and back it up with the same care as
  schema state.

This is the same implicit-commit behaviour described in
[DDL Operations](../ddl/README.md) and
[Transaction Support](../transaction_support/README.md); the migration layer
does not override it.

## 4. Version-gated DDL

MariaDB releases do not accept the same DDL on every server, and a migration is
often where an old floor becomes visible. Gates read from the connected dialect,
so call `introspect_and_adapt()` before consulting them:

```python
has_check = backend.dialect.supports_check_constraint()   # floor: 10.2.1
has_json_table = backend.dialect.version_at_least((10, 6, 0))
```

A migration function can branch on `ctx.backend.dialect` to pick the statement
it applies; a renderer that cannot express a feature either falls back to an
equivalent (for example JSON → `LONGTEXT`) or raises `UnsupportedFeatureError`.
Never assume a floor from the client library version — it is a property of the
server you connected to. The complete floor table and adaptation procedure are in
[Version gates](../mariadb_specific_features/version_gates.md); for the DDL
expressions themselves see [Field types](../mariadb_specific_features/field_types.md)
and [Storage engines](../mariadb_specific_features/storage_engine.md).

## 5. Function-style migrations

The decorator, FQN resolution, dependency validation, and result objects belong
to the core chapter. What is specific to this backend is simply the backend you
hand to the group and the dialect it brings:

```python
from rhosocial.activerecord.backend.migration import (
    MigrationDirection,
    run_migration_group,
)
from rhosocial.activerecord.backend.migration.record import JSONFileMigrationRecordStore

store = JSONFileMigrationRecordStore("migration_records.json")
fqn = f"{__name__}:create_users"

preview = run_migration_group(backend, [fqn], dry_run=True)
print(preview.dry_run_total, preview.dry_run_sql)

run_migration_group(backend, [fqn], record_store=store)
run_migration_group(
    backend, [fqn], direction=MigrationDirection.DOWN, record_store=store
)
```

The group calls `backend.introspector.clear_cache()` after a run, so subsequent
introspection sees the new schema. It cannot, however, undo committed DDL —
which is why the `DOWN` function must describe the inverse statement itself.
A complete, runnable version is
[`01_function_migration.py`](../../examples/migration/01_function_migration.py).

## 6. Class-style `named-migration` wiring

The class API (`NamedMigration` / `AsyncNamedMigration`, `MigrationRunner`,
`BatchMigrationRunner`) is unchanged; only the CLI adapter is backend-specific.
`src/rhosocial/activerecord/backend/impl/mariadb/cli/named_migration.py` supplies
a `MariaDBBackend` factory to the shared CLI helper and calls
`introspect_and_adapt()` before any migration runs. Hence the command below is
already bound to MariaDB — no `--backend-class` / `--config-class` needed:

```bash
python -m rhosocial.activerecord.backend.impl.mariadb named-migration \
    rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.migrations \
    --list
python -m rhosocial.activerecord.backend.impl.mariadb named-migration \
    rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.migrations.V001CreateUsers \
    --host 127.0.0.1 --port 3306 --database test_db --user app \
    --direction up --dry-run
python -m rhosocial.activerecord.backend.impl.mariadb named-migration \
    rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.migrations.V001CreateUsers \
    --host 127.0.0.1 --database test_db \
    --direction up --record-store records.json
```

The classes used above live in
`src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/`:

| File | Role |
|---|---|
| `migrations.py` | `NamedMigration` subclasses (`v001_create_users`, `v002_create_posts`, a parameterized one) |
| `expressions.py` | named DDL expressions the classes execute — the only place statement objects are built |
| `run_basic.py`, `run_chain.py`, `run_basic_async.py` | programmatic `MigrationRunner` demos |
| `demo_*.sh` | end-to-end CLI demos (`--list`, `--describe`, `--dry-run`, UP/DOWN, `--all`, `--param`, async) |

Read the core chapter for the meaning of `--direction`, `--record-store`,
`--single-transaction`, `--all`, and the class API generally. Note that
`--single-transaction` cannot make MariaDB DDL atomic: it groups the run, it does
not provide rollback of `CREATE`/`ALTER`/`DROP`. The local python counterpart is
[`02_named_migration_cli.py`](../../examples/migration/02_named_migration_cli.py).

## 7. Local examples

| Script | Demonstrates |
|---|---|
| [`01_function_migration.py`](../../examples/migration/01_function_migration.py) | `@migration` classmethod, MariaDB config, version gate, dry run → UP → DOWN |
| [`02_named_migration_cli.py`](../../examples/migration/02_named_migration_cli.py) | class-style `MigrationRunner` on MariaDB plus the equivalent `named-migration` commands |

Both require a live server (the index lists the environment variables). They are
syntax-checked with `py_compile` but are not executed by CI.

> 📖 For the migration *system* itself — ordering, dependencies, records,
> exceptions, dry-run internals — always return to the
> [core migration chapter](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US/migration).
