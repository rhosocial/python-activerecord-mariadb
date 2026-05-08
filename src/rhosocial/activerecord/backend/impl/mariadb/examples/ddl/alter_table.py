"""
Alter table statements - ADD_COLUMN.

Note: MariaDB supports multiple actions in a single ALTER TABLE statement,
but for simplicity we demonstrate individual operations.

Note: MODIFY COLUMN is a MariaDB-specific feature. The MariaDB dialect's
format_modify_column_action is not yet implemented, so this example
only demonstrates ADD_COLUMN.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression, InsertExpression, ValuesSource, DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal
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

drop_orders = DropTableExpression(dialect=dialect, table_name='orders', if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_table = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
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
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['name'],
    source=ValuesSource(
        dialect,
        [[Literal(dialect, 'Alice')]],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['name'],
    source=ValuesSource(
        dialect,
        [[Literal(dialect, 'Alice')]],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import AlterTableExpression
from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddColumn

add_col_action = AddColumn(
    column=ColumnDefinition(
        name='email',
        data_type='VARCHAR(100)',
    ),
)

add_col_expr = AlterTableExpression(
    dialect=dialect,
    table_name='users',
    actions=[add_col_action],
)

sql, params = add_col_expr.to_sql()
print(f"SQL (Add Column email): {sql}")
print(f"Params: {params}")

backend.execute(sql, params)
print("Column email added successfully")

add_age_action = AddColumn(
    column=ColumnDefinition(
        'age',
        'INT',
        constraints=[
            ColumnConstraint(
                ColumnConstraintType.DEFAULT,
                default_value=Literal(dialect, 0),
            ),
        ],
    ),
)

add_age_expr = AlterTableExpression(
    dialect=dialect,
    table_name='users',
    actions=[add_age_action],
)

sql, params = add_age_expr.to_sql()
print(f"SQL (Add Column age): {sql}")
print(f"Params: {params}")

backend.execute(sql, params)
print("Column age added successfully")

# ============================================================
# SECTION: Execution (verify alterations)
# ============================================================

# Verify using introspector
columns = backend.introspector.list_columns('users')
print("Table structure after alterations:")
for col in columns:
    print(f"  {col}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
