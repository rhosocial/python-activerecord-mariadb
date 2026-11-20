# docs/examples/migration/01_function_migration.py
"""Function-style migration on MariaDB: dry run -> UP -> DOWN.

Requires a live MariaDB server and an existing database. It demonstrates only
the backend-specific pieces; the migration system itself is documented in the
core library's migration chapter.

Usage:
    PYTHONPATH=src python docs/examples/migration/01_function_migration.py
"""
import os
import tempfile
from typing import Annotated, Optional

from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.migration import (
    MigrationDirection,
    migration,
    run_migration_group,
)
from rhosocial.activerecord.backend.migration.record import JSONFileMigrationRecordStore
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return "docs_migration_users"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


@migration("v001_create_users", description="create the users table on MariaDB")
def create_users(ctx):
    # DDL is implicitly committed by MariaDB; DOWN must describe the inverse
    # statement rather than relying on a transaction rollback.
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(User.create_table_statement(backend=ctx.backend))
    else:
        ctx.apply(User.drop_table_statement(if_exists=True, backend=ctx.backend))


def make_backend() -> MariaDBBackend:
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
    backend.introspect_and_adapt()  # version gates must answer for this server
    return backend


def main() -> None:
    backend = make_backend()
    record_path = os.path.join(tempfile.gettempdir(), "docs_migration_records.json")
    if os.path.exists(record_path):
        os.remove(record_path)
    store = JSONFileMigrationRecordStore(record_path)
    fqn = f"{__name__}:create_users"

    try:
        dialect = backend.dialect
        print("Server:", dialect.get_server_version())
        print("Transactional DDL:", dialect.supports_transactional_ddl())
        print("CHECK constraint (floor 10.2.1):", dialect.supports_check_constraint())
        print("JSON_TABLE (floor 10.6):", dialect.version_at_least((10, 6, 0)))

        print("\n== dry run ==")
        preview = run_migration_group(backend, [fqn], dry_run=True)
        print("  statements:", preview.dry_run_total)
        for label, sql, params in preview.dry_run_sql:
            print(f"  [{label}] {sql}")
        print("  records written:", preview.records_written)

        print("\n== UP ==")
        up = run_migration_group(backend, [fqn], record_store=store)
        print("  applied:", up.applied, "versions:", up.versions)
        print("  applied versions:", [r.version for r in store.get_applied()])

        print("\n== DOWN ==")
        down = run_migration_group(
            backend, [fqn], direction=MigrationDirection.DOWN, record_store=store
        )
        print("  rolled back:", down.rolled_back)
        print("  applied versions:", [r.version for r in store.get_applied()])
    finally:
        backend.disconnect()
        if os.path.exists(record_path):
            os.remove(record_path)


if __name__ == "__main__":
    main()
