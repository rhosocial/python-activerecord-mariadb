"""
Window functions - ROW_NUMBER, RANK, and aggregate over windows.
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

drop_table = DropTableExpression(dialect=dialect, table='sales_data', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table='sales_data',
    columns=[
        ColumnDefinition(
            'id',
            'INT',
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition('salesperson', 'VARCHAR(100)'),
        ColumnDefinition('region', 'VARCHAR(50)'),
        ColumnDefinition('amount', 'DECIMAL(10,2)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into='sales_data',
    columns=['salesperson', 'region', 'amount'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'Alice'), Literal(dialect, 'North'), Literal(dialect, 1000)],
            [Literal(dialect, 'Alice'), Literal(dialect, 'North'), Literal(dialect, 1500)],
            [Literal(dialect, 'Bob'), Literal(dialect, 'North'), Literal(dialect, 1200)],
            [Literal(dialect, 'Bob'), Literal(dialect, 'South'), Literal(dialect, 1800)],
            [Literal(dialect, 'Charlie'), Literal(dialect, 'South'), Literal(dialect, 2000)],
        ],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    WindowSpecification,
    OrderByClause,
)
from rhosocial.activerecord.backend.expression.advanced_functions import WindowFunctionCall

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'salesperson'),
        Column(dialect, 'region'),
        Column(dialect, 'amount'),
        WindowFunctionCall(
            dialect,
            'ROW_NUMBER',
            window_spec=WindowSpecification(
                dialect,
                partition_by=[Column(dialect, 'region')],
                order_by=OrderByClause(dialect, expressions=[(Column(dialect, 'amount'), 'DESC')]),
            ),
            alias='row_num',
        ),
        WindowFunctionCall(
            dialect,
            'SUM',
            args=[Column(dialect, 'amount')],
            window_spec=WindowSpecification(
                dialect,
                partition_by=[Column(dialect, 'region')],
            ),
            alias='region_total',
        ),
    ],
    from_=TableExpression(dialect, 'sales_data'),
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
