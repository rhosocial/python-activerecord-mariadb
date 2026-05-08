"""
Create an index on an existing table.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.expression import CreateTableExpression, DropTableExpression
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

config = MariaDBConnectionConfig(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    database=os.getenv('MYSQL_DATABASE', 'test'),
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    charset='utf8mb4',
)
backend = MariaDBBackend(connection_config=config)
backend.connect()
dialect = backend.dialect

# Drop table first for clean setup
drop = DropTableExpression(dialect=dialect, table_name='products', if_exists=True)
sql, params = drop.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='products',
    columns=[
        ColumnDefinition(
            'id',
            'INT',
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition('name', 'VARCHAR(100)'),
        ColumnDefinition('category', 'VARCHAR(50)'),
        ColumnDefinition('price', 'DECIMAL(10,2)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import CreateIndexExpression, DropIndexExpression

# Drop index first if exists (MariaDB does not support IF NOT EXISTS in CREATE INDEX)
try:
    drop_idx = DropIndexExpression(dialect=dialect, index_name='idx_category_price')
    sql, params = drop_idx.to_sql()
    backend.execute(sql, params)
except Exception:
    pass

create_idx = CreateIndexExpression(
    dialect=dialect,
    index_name='idx_category_price',
    table_name='products',
    columns=['category', 'price'],
)

sql, params = create_idx.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
backend.execute(sql, params)
print("Index created successfully")

# Verify using introspector
indexes = backend.introspector.list_indexes('products')
target_index = [idx for idx in indexes if 'idx_category_price' in str(idx)]
print(f"Index info: {target_index}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
