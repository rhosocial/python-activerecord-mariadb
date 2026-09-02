"""
Schema diff: detect index changes (drop one index, add another).

Builds a ``SchemaSnapshot`` before and after dropping an existing index and
creating a new one (via standalone ``DropIndexExpression`` /
``CreateIndexExpression``), then uses ``MariaDBSchemaDiffer`` to report the
added/removed indexes.

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
    DropTableExpression, CreateTableExpression, ColumnDefinition,
    ColumnConstraint, ColumnConstraintType, IndexDefinition,
)
from rhosocial.activerecord.backend.expression.types import (  # noqa: E402
    IntegerType, VarCharType,
)

expr = DropTableExpression(dialect, "users", if_exists=True)
sql, params = expr.to_sql()
backend.execute(sql, params)

# Baseline table with a non-unique index on `email`
expr = CreateTableExpression(
    dialect=dialect, table="users", columns=[
        ColumnDefinition("id", IntegerType(),
            constraints=[
                ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL),
                ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True),
            ]),
        ColumnDefinition("email", VarCharType(length=255)),
    ],
    indexes=[IndexDefinition("idx_email", ["email"])],
)
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
from rhosocial.activerecord.backend.expression.statements.ddl_index import (  # noqa: E402
    CreateIndexExpression, DropIndexExpression,
)

builder = SyncSchemaSnapshotBuilder(backend.introspector, dialect)
snapshot_before = builder.build()

# Drop the non-unique `idx_email` and add a unique `idx_email_unique`
# via standalone DROP INDEX / CREATE INDEX statements.
backend.execute(*DropIndexExpression(
    dialect, index="idx_email", table="users"
).to_sql())
backend.execute(*CreateIndexExpression(
    dialect, index="idx_email_unique", table="users",
    columns=["email"], unique=True,
).to_sql())

snapshot_after = builder.build()

differ = MariaDBSchemaDiffer()
diff = differ.compare(snapshot_before, snapshot_after)

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
print(f"Modified tables: {diff.modified_tables}")

if "users" in diff.table_diffs:
    td = diff.table_diffs["users"]
    for idx in td.added_indexes:
        print(f"  Added index:   {idx.name} unique={idx.is_unique} columns={idx.columns}")
    for idx in td.removed_indexes:
        print(f"  Removed index: {idx.name} unique={idx.is_unique} columns={idx.columns}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
expr = DropTableExpression(dialect, "users", if_exists=True)
sql, params = expr.to_sql()
backend.execute(sql, params)
backend.disconnect()
