"""
JOIN queries - INNER JOIN and LEFT JOIN.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

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

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

drop_customers = DropTableExpression(dialect=dialect, table_name='customers', if_exists=True)
sql, params = drop_customers.to_sql()
backend.execute(sql, params)

drop_orders = DropTableExpression(dialect=dialect, table_name='orders', if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

create_customers = CreateTableExpression(
    dialect=dialect,
    table_name='customers',
    columns=[
        ColumnDefinition(
            'id',
            'INT',
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition(
            'name',
            'VARCHAR(100)',
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
        ),
        ColumnDefinition('email', 'VARCHAR(100)'),
    ],
    if_not_exists=True,
)
sql, params = create_customers.to_sql()
backend.execute(sql, params)

create_orders = CreateTableExpression(
    dialect=dialect,
    table_name='orders',
    columns=[
        ColumnDefinition(
            'id',
            'INT',
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition('customer_id', 'INT'),
        ColumnDefinition('total', 'DECIMAL(10,2)'),
        ColumnDefinition('status', 'VARCHAR(20)'),
    ],
    if_not_exists=True,
)
sql, params = create_orders.to_sql()
backend.execute(sql, params)

insert_customers = InsertExpression(
    dialect=dialect,
    into='customers',
    columns=['name', 'email'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'Alice'), Literal(dialect, 'alice@example.com')],
            [Literal(dialect, 'Bob'), Literal(dialect, 'bob@example.com')],
        ],
    ),
)
sql, params = insert_customers.to_sql()
backend.execute(sql, params)

insert_orders = InsertExpression(
    dialect=dialect,
    into='orders',
    columns=['customer_id', 'total', 'status'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 1), Literal(dialect, 100.00), Literal(dialect, 'completed')],
            [Literal(dialect, 1), Literal(dialect, 50.00), Literal(dialect, 'pending')],
            [Literal(dialect, 2), Literal(dialect, 75.00), Literal(dialect, 'completed')],
        ],
    ),
)
sql, params = insert_orders.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

customers = TableExpression(dialect, 'customers', alias='c')
orders = TableExpression(dialect, 'orders', alias='o')

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'name', table='c'),
        Column(dialect, 'total', table='o'),
        Column(dialect, 'status', table='o'),
    ],
    from_=[
        customers,
        orders,
    ],
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            'AND',
            ComparisonPredicate(
                dialect,
                '=',
                Column(dialect, 'id', table='c'),
                Column(dialect, 'customer_id', table='o'),
            ),
            ComparisonPredicate(
                dialect,
                '=',
                Column(dialect, 'status', table='o'),
                Literal(dialect, 'completed'),
            ),
        ),
    ),
)

sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
