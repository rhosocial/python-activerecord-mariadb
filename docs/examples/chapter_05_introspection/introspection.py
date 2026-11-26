# docs/examples/chapter_05_introspection/introspection.py
"""Read MariaDB's own answers through the backend introspector.

Requires a live MariaDB server and an existing database; see README.md.
This script is read-only.
"""

import os

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


def make_backend() -> MariaDBBackend:
    config = MariaDBConnectionConfig(
        host=os.getenv("MARIADB_HOST", "localhost"),
        port=int(os.getenv("MARIADB_PORT", "3306")),
        database=os.getenv("MARIADB_DATABASE", "test_db"),
        username=os.getenv("MARIADB_USERNAME", "app"),
        password=os.getenv("MARIADB_PASSWORD", ""),
    )
    backend = MariaDBBackend(connection_config=config)
    backend.connect()
    # Make the probes answer for the server the handshake reached.
    backend.introspect_and_adapt()
    return backend


def show_probes(dialect) -> None:
    probes = (
        "supports_introspection",
        "supports_runtime_stats",
        "supports_table_stats",
        "supports_index_stats",
        "supports_unused_indexes_detection",
        "supports_object_dependencies",
        "supports_ddl_extraction",
        "supports_column_data_profile",
        "supports_join_coverage",
    )
    print("Capability probes:")
    for name in probes:
        probe = getattr(dialect, name, None)
        if probe is not None:
            print(f"  {name}: {probe()}")


def main() -> None:
    backend = make_backend()
    introspector = backend.introspector
    try:
        show_probes(backend.dialect)

        info = introspector.get_database_info()
        print("\nDatabase:", info.name, info.version, info.encoding, info.collation)

        print("\nTables:")
        for table in introspector.list_tables():
            print(" ", table.name, table.table_type.value)

        for table in introspector.list_tables():
            print(f"\nColumns of {table.name}:")
            for column in introspector.list_columns(table.name):
                print("  ", column.name, column.data_type_full, column.nullable.value)
            print(f"Indexes of {table.name}:")
            for index in introspector.list_indexes(table.name):
                print("  ", index.name, index.columns)

            # MariaDB-only families.
            options = introspector.get_table_options(table.name)
            if options:
                print("  Table options:", options.engine, options.row_format, options.collation)
            state = introspector.get_partition_state(table.name)
            if state.scheme is not None:
                print("  Partitions:", [bound.name for bound in state.bounds])
            constraints = introspector.list_constraints(table.name)
            if constraints:
                print("  CHECK constraints:", [c.name for c in constraints])

        print("\nSequences:")
        for sequence in introspector.list_sequences():
            print("  ", sequence.name, sequence.start_value, sequence.increment)

        print("\nRoutines:")
        for routine in introspector.list_routines():
            print("  ", routine.kind, routine.name, routine.return_type)
    finally:
        backend.disconnect()


if __name__ == "__main__":
    main()
