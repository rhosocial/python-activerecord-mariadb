"""
Schema diff: detect an added column (and ordinal-position shift).

MariaDB column order is significant. Adding a column in the middle of a
table shifts the ordinal position of subsequent columns, which the
``MariaDBSchemaDiffer`` reports.

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
    ColumnConstraint, ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (  # noqa: E402
    IntegerType, VarCharType,
)

expr = DropTableExpression(dialect, "users", if_exists=True)
sql, params = expr.to_sql()
backend.execute(sql, params)

# Baseline table: id, name, email
expr = CreateTableExpression(
    dialect=dialect, table="users", columns=[
        ColumnDefinition("id", IntegerType(),
            constraints=[
                ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL),
                ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True),
            ]),
        ColumnDefinition("name", VarCharType(length=100)),
        ColumnDefinition("email", VarCharType(length=255)),
    ]
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
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (  # noqa: E402
    AlterTableExpression, AddColumn,
)

builder = SyncSchemaSnapshotBuilder(backend.introspector, dialect)
snapshot_before = builder.build()

# Add `age` column between `name` and `email` — shifts email to position 4
add_col = AddColumn(dialect, ColumnDefinition("age", IntegerType()),
                    dialect_options={"after": "name"})
alter_expr = AlterTableExpression(dialect, "users", [add_col])
sql, params = alter_expr.to_sql()
backend.execute(sql, params)

snapshot_after = builder.build()

differ = MariaDBSchemaDiffer()
diff = differ.compare(snapshot_before, snapshot_after)

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
print(f"Modified tables: {diff.modified_tables}")

if "users" in diff.table_diffs:
    td = diff.table_diffs["users"]
    for cd in td.column_diffs:
        kind = "added" if cd.is_added else "modified" if cd.is_modified else "removed"
        old_pos = cd.old.ordinal_position if cd.old else "-"
        new_pos = cd.new.ordinal_position if cd.new else "-"
        print(f"  Column '{cd.column_name}': {kind} (ordinal: {old_pos}->{new_pos})")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
expr = DropTableExpression(dialect, "users", if_exists=True)
sql, params = expr.to_sql()
backend.execute(sql, params)
backend.disconnect()
