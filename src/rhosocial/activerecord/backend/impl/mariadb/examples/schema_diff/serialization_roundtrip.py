"""
Schema diff: snapshot serialization round-trip.

A ``SchemaSnapshot`` can be serialized to a plain dict (JSON-safe) with
``to_dict()`` and reconstructed with ``from_dict()``. This is useful for
persisting a baseline schema to disk and later comparing it against the
live database.

Supported versions: MariaDB 10.2+
"""

import json

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host=os.getenv("MARIADB_HOST", "localhost"),
    port=int(os.getenv("MARIADB_PORT", "3306")),
    database=os.getenv("MARIADB_DATABASE", "test"),
    username=os.getenv("MARIADB_USER", "root"),
    password=os.getenv("MARIADB_PASSWORD", ""),
    charset="utf8mb4",
)
backend = MariaDBBackend(connection_config=config)
backend.connect()
backend.introspect_and_adapt()
dialect = backend.dialect

# Clean up any leftover tables
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    DropTableExpression, CreateTableExpression, ColumnDefinition,
    ColumnConstraint, ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (  # noqa: E402
    IntegerType, VarCharType,
)

expr = DropTableExpression(dialect, "users", if_exists=True)
sql, params = expr.to_sql()
backend.execute(sql, params)

expr = CreateTableExpression(
    dialect=dialect, table="users", columns=[
        ColumnDefinition("id", IntegerType(),
            constraints=[
                ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL),
                ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True),
            ]),
        ColumnDefinition("name", VarCharType(length=100)),
    ]
)
sql, params = expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.schema import (  # noqa: E402
    SyncSchemaSnapshotBuilder, SchemaSnapshot,
)
from rhosocial.activerecord.backend.impl.mariadb.schema.differ import (  # noqa: E402
    MariaDBSchemaDiffer,
)

builder = SyncSchemaSnapshotBuilder(backend.introspector, dialect)
snapshot = builder.build()

# Serialize -> JSON string -> deserialize
payload = snapshot.to_dict()
json_str = json.dumps(payload, default=str, indent=2)
reloaded = json.loads(json_str)
snapshot_restored = SchemaSnapshot.from_dict(reloaded)

# A snapshot compared against itself must produce an empty diff
differ = MariaDBSchemaDiffer()
diff = differ.compare(snapshot, snapshot_restored)

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
print(f"Snapshot tables:       {list(snapshot.tables.keys())}")
print(f"Restored tables:       {list(snapshot_restored.tables.keys())}")
print(f"JSON payload length:   {len(json_str)} bytes")
print(f"Round-trip diff empty: {diff.is_empty}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
expr = DropTableExpression(dialect, "users", if_exists=True)
sql, params = expr.to_sql()
backend.execute(sql, params)
backend.disconnect()
