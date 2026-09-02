"""
Subquery expressions - WHERE and FROM subqueries.
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

drop_departments = DropTableExpression(dialect=dialect, table='departments', if_exists=True)
sql, params = drop_departments.to_sql()
backend.execute(sql, params)

drop_employees = DropTableExpression(dialect=dialect, table='employees', if_exists=True)
sql, params = drop_employees.to_sql()
backend.execute(sql, params)

create_departments = CreateTableExpression(
    dialect=dialect,
    table='departments',
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
        ColumnDefinition('budget', 'DECIMAL(15,2)'),
    ],
    if_not_exists=True,
)
sql, params = create_departments.to_sql()
backend.execute(sql, params)

create_employees = CreateTableExpression(
    dialect=dialect,
    table='employees',
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
        ColumnDefinition('salary', 'DECIMAL(10,2)'),
        ColumnDefinition('department_id', 'INT'),
    ],
    if_not_exists=True,
)
sql, params = create_employees.to_sql()
backend.execute(sql, params)

insert_departments = InsertExpression(
    dialect=dialect,
    into='departments',
    columns=['name', 'budget'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'Engineering'), Literal(dialect, 1000000)],
            [Literal(dialect, 'Sales'), Literal(dialect, 500000)],
        ],
    ),
)
sql, params = insert_departments.to_sql()
backend.execute(sql, params)

insert_employees = InsertExpression(
    dialect=dialect,
    into='employees',
    columns=['name', 'salary', 'department_id'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'Alice'), Literal(dialect, 80000), Literal(dialect, 1)],
            [Literal(dialect, 'Bob'), Literal(dialect, 90000), Literal(dialect, 1)],
            [Literal(dialect, 'Charlie'), Literal(dialect, 60000), Literal(dialect, 2)],
            [Literal(dialect, 'David'), Literal(dialect, 70000), Literal(dialect, 2)],
        ],
    ),
)
sql, params = insert_employees.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    WhereClause,
    Subquery,
)
from rhosocial.activerecord.backend.expression.core import FunctionCall
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

subquery_query = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'AVG', Column(dialect, 'salary'))],
    from_=TableExpression(dialect, 'employees'),
)
sql, params = subquery_query.to_sql()
subquery = Subquery(dialect, sql, params)

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'name'),
        Column(dialect, 'salary'),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            '>',
            Column(dialect, 'salary'),
            subquery,
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
