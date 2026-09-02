"""
Complex predicates: LIKE, IN, BETWEEN, IS NULL / IS NOT NULL.
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
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

drop_table = DropTableExpression(dialect=dialect, table='employees', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
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
        ColumnDefinition(
            'name',
            'VARCHAR(100)',
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
        ),
        ColumnDefinition('department', 'VARCHAR(50)'),
        ColumnDefinition('salary', 'DECIMAL(10,2)'),
        ColumnDefinition('manager_id', 'INT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into='employees',
    columns=['name', 'department', 'salary', 'manager_id'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'Alice'), Literal(dialect, 'Engineering'),
             Literal(dialect, 95000.00), Literal(dialect, None)],
            [Literal(dialect, 'Bob'), Literal(dialect, 'Engineering'), Literal(dialect, 80000.00), Literal(dialect, 1)],
            [Literal(dialect, 'Charlie'), Literal(dialect, 'Sales'), Literal(dialect, 70000.00), Literal(dialect, 1)],
            [Literal(dialect, 'Diana'), Literal(dialect, 'Sales'), Literal(dialect, 72000.00), Literal(dialect, None)],
            [Literal(dialect, 'Eve'), Literal(dialect, 'Marketing'), Literal(dialect, 68000.00), Literal(dialect, 1)],
            [Literal(dialect, 'Frank'), Literal(dialect, 'Marketing'), Literal(dialect, 65000.00), Literal(dialect, 4)],
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
    WhereClause,
)
from rhosocial.activerecord.backend.expression.predicates import (
    ComparisonPredicate,
    LikePredicate,
    InPredicate,
    BetweenPredicate,
    IsNullPredicate,
    LogicalPredicate,
)

# 1. LIKE predicate - pattern matching
# Find employees whose name starts with 'A'
like_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'department'),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=WhereClause(
        dialect,
        condition=LikePredicate(
            dialect,
            'LIKE',
            Column(dialect, 'name'),
            Literal(dialect, 'A%'),
        ),
    ),
)

sql, params = like_query.to_sql()
print(f"LIKE SQL: {sql}")
print(f"LIKE Params: {params}")

# 2. IN predicate - list membership
# Find employees in Engineering or Sales departments
in_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'department'),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=WhereClause(
        dialect,
        condition=InPredicate(
            dialect,
            Column(dialect, 'department'),
            Literal(dialect, ['Engineering', 'Sales']),
        ),
    ),
)

sql, params = in_query.to_sql()
print(f"IN SQL: {sql}")
print(f"IN Params: {params}")

# 3. BETWEEN predicate - range check
# Find employees with salary between 65000 and 75000
between_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'salary'),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=WhereClause(
        dialect,
        condition=BetweenPredicate(
            dialect,
            Column(dialect, 'salary'),
            Literal(dialect, 65000.00),
            Literal(dialect, 75000.00),
        ),
    ),
)

sql, params = between_query.to_sql()
print(f"BETWEEN SQL: {sql}")
print(f"BETWEEN Params: {params}")

# 4. IS NULL / IS NOT NULL predicates
# Find employees without a manager (manager_id IS NULL)
is_null_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'manager_id'),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=WhereClause(
        dialect,
        condition=IsNullPredicate(
            dialect,
            Column(dialect, 'manager_id'),
        ),
    ),
)

sql, params = is_null_query.to_sql()
print(f"IS NULL SQL: {sql}")
print(f"IS NULL Params: {params}")

# Find employees with a manager (manager_id IS NOT NULL)
is_not_null_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'manager_id'),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=WhereClause(
        dialect,
        condition=IsNullPredicate(
            dialect,
            Column(dialect, 'manager_id'),
            is_not=True,
        ),
    ),
)

sql, params = is_not_null_query.to_sql()
print(f"IS NOT NULL SQL: {sql}")
print(f"IS NOT NULL Params: {params}")

# 5. Combining predicates with AND/OR logic
# Engineering employees earning between 75000 and 100000
combined_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'department'),
        Column(dialect, 'salary'),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=WhereClause(
        dialect,
        condition=LogicalPredicate(
            dialect,
            'AND',
            ComparisonPredicate(
                dialect,
                '=',
                Column(dialect, 'department'),
                Literal(dialect, 'Engineering'),
            ),
            BetweenPredicate(
                dialect,
                Column(dialect, 'salary'),
                Literal(dialect, 75000.00),
                Literal(dialect, 100000.00),
            ),
        ),
    ),
)

sql, params = combined_query.to_sql()
print(f"Combined SQL: {sql}")
print(f"Combined Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
options = ExecutionOptions(stmt_type=StatementType.DQL)

print("\n--- LIKE: Names starting with 'A' ---")
sql, params = like_query.to_sql()
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

print("\n--- IN: Engineering or Sales ---")
sql, params = in_query.to_sql()
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

print("\n--- BETWEEN: Salary 65000-75000 ---")
sql, params = between_query.to_sql()
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

print("\n--- IS NULL: No manager ---")
sql, params = is_null_query.to_sql()
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

print("\n--- IS NOT NULL: Has manager ---")
sql, params = is_not_null_query.to_sql()
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

print("\n--- Combined: Engineering AND salary 75000-100000 ---")
sql, params = combined_query.to_sql()
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
