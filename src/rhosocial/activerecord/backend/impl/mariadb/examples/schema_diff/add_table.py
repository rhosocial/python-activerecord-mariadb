"""
Schema diff: detect added tables.

Builds a ``SchemaSnapshot`` before and after creating a table, then uses
``MariaDBSchemaDiffer`` to report the change.

Supported versions: MariaDB 10.2+
"""

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
    DropTableExpression,
)
expr = DropTableExpression(dialect, "users", if_exists=True)
sql, params = expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.schema import (  # noqa: E402
    SyncSchemaSnapshotBuilder,
)
from rhosocial.activerecord.backend.impl.mariadb.schema.differ import (  # noqa: E402
    MariaDBSchemaDiffer,
)
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableExpression, ColumnDefinition,
    ColumnConstraint, ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (  # noqa: E402
    IntegerType, VarCharType,
)

builder = SyncSchemaSnapshotBuilder(backend.introspector, dialect)
snapshot_before = builder.build()

# Create a new table
expr = CreateTableExpression(
    dialect=dialect, table="users", columns=[
        ColumnDefinition("id", IntegerType(),
            constraints=[
                ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL),
                ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True),
            ]),
        ColumnDefinition("name", VarCharType(100)),
    ]
)
sql, params = expr.to_sql()
backend.execute(sql, params)

snapshot_after = builder.build()

differ = MariaDBSchemaDiffer()
diff = differ.compare(snapshot_before, snapshot_after)

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
print(f"Added tables:    {diff.added_tables}")
print(f"Removed tables:  {diff.removed_tables}")
print(f"Modified tables: {diff.modified_tables}")
print(f"Diff is empty:   {diff.is_empty}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
expr = DropTableExpression(dialect, "users", if_exists=True)
sql, params = expr.to_sql()
backend.execute(sql, params)
backend.disconnect()
