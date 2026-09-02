"""
CREATE UNIQUE INDEX - MariaDB.

This example demonstrates:
1. CREATE UNIQUE INDEX
2. CREATE INDEX with multiple columns
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    database=os.getenv('MYSQL_DATABASE', 'test'),
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
)
backend = MariaDBBackend(connection_config=config)
backend.connect()
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import CreateTableExpression, DropTableExpression
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

# Drop dependent tables first for clean setup
drop_orders = DropTableExpression(dialect=dialect, table='orders', if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_table = DropTableExpression(dialect=dialect, table='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table='users',
    columns=[
        ColumnDefinition('id', 'INT', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
        ]),
        ColumnDefinition('email', 'VARCHAR(100)'),
        ColumnDefinition('name', 'VARCHAR(100)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: CREATE UNIQUE INDEX
# ============================================================
from rhosocial.activerecord.backend.expression import CreateIndexExpression, DropIndexExpression

# Drop index first if exists (MariaDB does not support IF NOT EXISTS in CREATE INDEX)
try:
    drop_idx = DropIndexExpression(dialect=dialect, index='idx_users_email_unique')
    sql, params = drop_idx.to_sql()
    backend.execute(sql, params)
except Exception:
    pass

unique_idx = CreateIndexExpression(
    dialect=dialect,
    index='idx_users_email_unique',
    table='users',
    columns=['email'],
    unique=True,
)
sql, params = unique_idx.to_sql()
print(f"CREATE UNIQUE INDEX SQL: {sql}")
print(f"Params: {params}")
backend.execute(sql, params)

# ============================================================
# SECTION: CREATE INDEX with multiple columns
# ============================================================
# Drop composite index first if exists
try:
    drop_idx2 = DropIndexExpression(dialect=dialect, index='idx_users_name_email')
    sql, params = drop_idx2.to_sql()
    backend.execute(sql, params)
except Exception:
    pass

composite_idx = CreateIndexExpression(
    dialect=dialect,
    index='idx_users_name_email',
    table='users',
    columns=['name', 'email'],
)
sql, params = composite_idx.to_sql()
print(f"CREATE INDEX multi-col SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Teardown
# ============================================================
drop_orders = DropTableExpression(dialect=dialect, table='orders', if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_table = DropTableExpression(dialect=dialect, table='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use CreateIndexExpression with unique=True
# 2. Use columns=[col1, col2] for composite index
# 3. Use DropIndexExpression to drop