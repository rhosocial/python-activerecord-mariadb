# docs/examples/migration/02_named_migration_cli.py
"""Class-style migration wiring on MariaDB (the `named-migration` path).

Shows the same objects the backend CLI assembles: a MariaDBBackend, a
MigrationRunner for a NamedMigration class, and a JSON record store. DDL is
implicitly committed by MariaDB, so DOWN runs explicit inverse expressions.

Requires a live MariaDB server and an existing database.

Usage:
    PYTHONPATH=src python docs/examples/migration/02_named_migration_cli.py
"""
import os
import tempfile

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.migration import (
    MigrationDirection,
    MigrationRunner,
    JSONFileMigrationRecordStore,
)

MIGRATIONS_MODULE = (
    "rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.migrations"
)
MIGRATION_FQN = f"{MIGRATIONS_MODULE}.V001CreateUsers"


def make_backend() -> MariaDBBackend:
    # The backend CLI builds the same config from its connection flags.
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
    return backend


def main() -> None:
    backend = make_backend()
    record_path = os.path.join(tempfile.gettempdir(), "docs_named_migration_records.json")
    if os.path.exists(record_path):
        os.remove(record_path)
    store = JSONFileMigrationRecordStore(record_path)
    runner = MigrationRunner(MIGRATION_FQN)

    print("Migration class:", MIGRATION_FQN)
    print("Transactional DDL:", backend.dialect.supports_transactional_ddl())
    print("\nEquivalent CLI commands:")
    print(
        "  python -m rhosocial.activerecord.backend.impl.mariadb named-migration "
        f"{MIGRATIONS_MODULE} --list"
    )
    print(
        "  python -m rhosocial.activerecord.backend.impl.mariadb named-migration "
        f"{MIGRATION_FQN} --host 127.0.0.1 --database test_db "
        "--direction up --dry-run"
    )
    print(
        "  python -m rhosocial.activerecord.backend.impl.mariadb named-migration "
        f"{MIGRATION_FQN} --host 127.0.0.1 --database test_db "
        "--direction up --record-store records.json"
    )

    try:
        print("\n== dry run ==")
        preview = runner.run(backend, MigrationDirection.UP, dry_run=True)
        print("  version:", preview.version, "success:", preview.success)

        print("\n== UP ==")
        up = runner.run(backend, MigrationDirection.UP, record_store=store)
        print("  version:", up.version, "success:", up.success)
        print("  applied versions:", [r.version for r in store.get_applied()])

        print("\n== DOWN ==")
        down = runner.run(backend, MigrationDirection.DOWN, record_store=store)
        print("  version:", down.version, "success:", down.success)
        print("  applied versions:", [r.version for r in store.get_applied()])
    finally:
        backend.disconnect()
        if os.path.exists(record_path):
            os.remove(record_path)


if __name__ == "__main__":
    main()
