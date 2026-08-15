# src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/run_chain.py
"""
Multi-step migration chain example — two migrations with dependency (MariaDB).

This script demonstrates:
  1. Running v001_create_users (creates ``users`` table)
  2. Running v002_create_posts (creates ``posts`` table, depends on v001)
  3. Dependency validation (v002 fails if v001 is not applied)
  4. Rolling back in reverse order
  5. Tracking applied migrations in JSON record store

Usage:
    python -m rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.run_chain
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
    MigrationDependencyError,
    MigrationNotAppliedError,
)

BASE = "rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.migrations"


def main():
    print("=" * 60)
    print("Named Migration Demo — Dependency Chain (MariaDB)")
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

    store_path = Path(tempfile.gettempdir()) / "mig_mariadb_chain.json"
    if store_path.exists():
        store_path.unlink()
    store = JSONFileMigrationRecordStore(store_path)
    print(f"\n[1] Record store: {store_path}")

    r1 = MigrationRunner(f"{BASE}.V001CreateUsers")
    r2 = MigrationRunner(f"{BASE}.V002CreatePosts")

    print("\n[2] Attempt v002 before v001 (should fail) …")
    try:
        r2.run(backend, MigrationDirection.UP, record_store=store)
        print("    ✗ ERROR: should have raised!")
    except MigrationDependencyError as e:
        print(f"    ✓ {e}")

    print("\n[3] Applying v001_create_users …")
    r1.run(backend, MigrationDirection.UP, record_store=store)
    print("    ✓ Table 'users' created.")

    print("\n[4] Applying v002_create_posts …")
    r2.run(backend, MigrationDirection.UP, record_store=store)
    print("    ✓ Table 'posts' created (dependency check passed).")

    print("\n[5] Applied migrations:")
    for rec in store.get_applied():
        print(f"    - {rec.version}")

    print("\n[6] Rolling back v002_create_posts …")
    r2.run(backend, MigrationDirection.DOWN, record_store=store)
    print("    ✓ Table 'posts' dropped; 'users' still exists.")

    print("\n[7] Rolling back v001_create_users …")
    r1.run(backend, MigrationDirection.DOWN, record_store=store)
    print("    ✓ Table 'users' dropped.")

    assert len(store.get_applied()) == 0
    print("\n[8] All migrations rolled back (0 applied).")

    print("\n[9] DOWN on unapplied migration (should fail) …")
    try:
        r1.run(backend, MigrationDirection.DOWN, record_store=store)
        print("    ✗ ERROR: should have raised!")
    except MigrationNotAppliedError as e:
        print(f"    ✓ {e}")

    backend.disconnect()
    if store_path.exists():
        store_path.unlink()
    print("\n=== MariaDB chain migration demo completed ===")


if __name__ == "__main__":
    main()
