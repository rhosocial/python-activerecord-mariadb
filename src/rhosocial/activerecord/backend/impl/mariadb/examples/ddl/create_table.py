"""
Create a table with primary key, auto-increment, and MariaDB-specific options.

This example demonstrates:
1. CREATE TABLE with various column types and constraints
2. AUTO_INCREMENT primary key
3. MariaDB-specific ENGINE and CHARSET options
4. Inline index definitions
5. Default values and NOT NULL constraints
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.expression import (
    DropTableExpression,
    CreateTableExpression,
)
from rhosocial.activerecord.backend.expression.functions.datetime import current_timestamp
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    IndexDefinition,
)

config = MariaDBConnectionConfig(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    database=os.getenv('MYSQL_DATABASE', 'test'),
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
)
backend = MariaDBBackend(connection_config=config)
backend.connect()
dialect = backend.dialect

# Drop if exists for clean setup
drop = DropTableExpression(dialect=dialect, table='products', if_exists=True)
sql, params = drop.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

columns = [
    ColumnDefinition(
        name='id',
        data_type='INT',
        constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ],
    ),
    ColumnDefinition(
        name='name',
        data_type='VARCHAR(200)',
        constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ],
    ),
    ColumnDefinition(
        name='price',
        data_type='DECIMAL(10,2)',
        constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ],
    ),
    ColumnDefinition(
        name='category',
        data_type='VARCHAR(100)',
    ),
    ColumnDefinition(
        name='is_active',
        data_type='TINYINT(1)',
        constraints=[
            ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
        ],
    ),
    ColumnDefinition(
        name='created_at',
        data_type='TIMESTAMP',
        constraints=[
            ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=current_timestamp(dialect)),
        ],
    ),
]

indexes = [
    IndexDefinition(
        name='idx_products_category',
        columns=['category'],
    ),
]

# Create table with MariaDB-specific ENGINE and CHARSET options
create_expr = CreateTableExpression(
    dialect=dialect,
    table='products',
    columns=columns,
    indexes=indexes,
    if_not_exists=True,
    dialect_options={
        'engine': 'InnoDB',
        'charset': 'utf8mb4',
    },
)

sql, params = create_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print("Table created: products")

# Verify table structure using introspector
columns_info = backend.introspector.list_columns('products')
print("Columns in 'products':")
for col in columns_info:
    print(f"  {col}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_table = DropTableExpression(dialect=dialect, table='products', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use ColumnConstraint with is_auto_increment=True for AUTO_INCREMENT
# 2. MariaDB dialect_options supports 'engine' and 'charset' keys
# 3. IndexDefinition creates inline indexes within CREATE TABLE
# 4. Use current_timestamp(dialect) for SQL niladic functions (no parentheses)
# 5. Use introspector.get_columns() to verify table structure
