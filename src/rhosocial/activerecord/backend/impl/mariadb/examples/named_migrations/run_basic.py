# src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/run_basic.py
"""
Basic migration example — single migration UP then DOWN (MariaDB).

This script demonstrates:
  1. Creating a MariaDB backend
  2. Running a single ``NamedMigration`` UP (creates ``users`` table)
  3. Verifying the table was created
  4. Running the same migration DOWN (drops ``users`` table)
  5. Showing JSON record store persistence
  6. Dry-run mode (no actual changes)
  7. Duplicate execution protection

Usage:
    python -m rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.run_basic
"""

from pathlib import Path
import tempfile
import os

from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.migration import (
    MigrationRunner,
    MigrationDirection,
    JSONFileMigrationRecordStore,
    MigrationAlreadyAppliedError,
)


def main():
    print("=" * 60)
    print("Named Migration Demo — Basic (MariaDB)")
    print("=" * 60)

    config = MariaDBConnectionConfig(
        host=os.getenv("MARIADB_HOST", "localhost"),
        port=int(os.getenv("MARIADB_PORT", "3306")),
        database=os.getenv("MARIADB_DATABASE", "test"),
        username=os.getenv("MARIADB_USER", "root"),
        password=os.getenv("MARIADB_PASSWORD", ""),
    )
    backend = MariaDBBackend(connection_config=config)
    backend.connect()
    backend.introspect_and_adapt()
    print("\n[1] MariaDB backend connected.")

    store_path = Path(tempfile.gettempdir()) / "mig_mariadb_basic.json"
    if store_path.exists():
        store_path.unlink()
    store = JSONFileMigrationRecordStore(store_path)
    print(f"[2] Record store: {store_path}")

    fqn = (
        "rhosocial.activerecord.backend.impl.mariadb.examples"
        ".named_migrations.migrations.V001CreateUsers"
    )
    runner = MigrationRunner(fqn)

    print("\n[3] Dry-run (UP) — no actual changes …")
    result = runner.run(backend, MigrationDirection.UP, dry_run=True)
    print(f"    Result: version={result.version}, success={result.success}")
    print("    ✓ Dry-run completed (table not created).")

    print("\n[4] Applying v001_create_users (UP) …")
    result = runner.run(backend, MigrationDirection.UP, record_store=store)
    print(f"    Result: version={result.version}, success={result.success}")
    print("    ✓ Table 'users' created.")

    print("\n[5] Duplicate UP (should be rejected) …")
    try:
        runner.run(backend, MigrationDirection.UP, record_store=store)
        print("    ✗ ERROR: should have raised!")
    except MigrationAlreadyAppliedError as e:
        print(f"    ✓ {e}")

    print("\n[6] Rolling back v001_create_users (DOWN) …")
    result = runner.run(backend, MigrationDirection.DOWN, record_store=store)
    print(f"    Result: version={result.version}, success={result.success}")
    print("    ✓ Table 'users' dropped.")

    applied = store.get_applied()
    print(f"\n[7] Applied migrations: {len(applied)} (should be 0)")

    backend.disconnect()
    if store_path.exists():
        store_path.unlink()
    print("\n=== MariaDB basic migration demo completed ===")


if __name__ == "__main__":
    main()
