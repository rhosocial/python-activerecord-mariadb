"""
EXPLAIN and Query Plan analysis - MariaDB.

This example demonstrates:
1. Using EXPLAIN to analyze query execution
2. Understanding the EXPLAIN output columns
3. Index usage analysis
4. Interpreting the execution plan
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
    ExplainExpression,
    CreateIndexExpression,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.explain import ExplainOptions
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

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

drop_table = DropTableExpression(dialect=dialect, table='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table='users',
    columns=[
        ColumnDefinition('id', 'INT', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('name', 'VARCHAR(100)', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('email', 'VARCHAR(200)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

create_index = CreateIndexExpression(
    dialect=dialect,
    index='idx_users_email',
    table='users',
    columns=['email'],
    if_not_exists=True,
)
sql, params = create_index.to_sql()
backend.execute(sql, params)

users = [
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com'),
    ('Charlie', 'charlie@example.com'),
]
for name, email in users:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='users',
        columns=['name', 'email'],
        source=ValuesSource(dialect, [[Literal(dialect, name), Literal(dialect, email)]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# 1. EXPLAIN for table scan (no index on name column)
query1 = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, '*')],
    from_=TableExpression(dialect, 'users'),
    where=ComparisonPredicate(
        dialect, '=', Column(dialect, 'name'), Literal(dialect, 'Alice'),
    ),
)
explain_scan = ExplainExpression(
    dialect=dialect,
    statement=query1,
    options=ExplainOptions(),
)
sql, params = explain_scan.to_sql()
print("1. Table SCAN (no index on name):")
print(f"SQL: {sql}")
result = backend.execute(sql, params)
for row in result.data:
    print(f"  {row}")

# 2. EXPLAIN for index search (email has index)
query2 = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, '*')],
    from_=TableExpression(dialect, 'users'),
    where=ComparisonPredicate(
        dialect, '=', Column(dialect, 'email'), Literal(dialect, 'alice@example.com'),
    ),
)
explain_search = ExplainExpression(
    dialect=dialect,
    statement=query2,
    options=ExplainOptions(),
)
sql, params = explain_search.to_sql()
print("\n2. Index SEARCH (using idx_users_email):")
print(f"SQL: {sql}")
result = backend.execute(sql, params)
for row in result.data:
    print(f"  {row}")

# 3. EXPLAIN with FORMAT=JSON for detailed analysis
explain_json = ExplainExpression(
    dialect=dialect,
    statement=query2,
    options=ExplainOptions(format='JSON'),
)
sql, params = explain_json.to_sql()
print("\n3. EXPLAIN FORMAT=JSON:")
print(f"SQL: {sql}")
result = backend.execute(sql, params)
for row in result.data:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_table = DropTableExpression(dialect=dialect, table='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. MariaDB EXPLAIN shows execution plan without executing the query
# 2. "type" column shows access method: ALL=table scan, ref=index lookup
# 3. "key" column shows which index is used
# 4. "rows" column shows estimated rows to examine
# 5. FORMAT=JSON provides detailed cost information