"""
Common Table Expressions (CTE) - MariaDB 8.0+.

This example demonstrates:
1. Basic CTE with WITH clause
2. Recursive CTE for hierarchical data
3. CTE for simplifying complex queries
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

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    DropTableExpression,
    QueryExpression,
    TableExpression,
    CTEExpression,
    WithQueryExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

# Drop table first for clean setup
drop = DropTableExpression(dialect=dialect, table='employees', if_exists=True)
sql, params = drop.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table='employees',
    columns=[
        ColumnDefinition('id', 'INT', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
        ]),
        ColumnDefinition('name', 'VARCHAR(100)'),
        ColumnDefinition('manager_id', 'INT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

delete_sql = "DELETE FROM employees"
backend.execute(delete_sql)

insert_expr = InsertExpression(
    dialect=dialect,
    into='employees',
    columns=['id', 'name', 'manager_id'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 1), Literal(dialect, 'CEO'), Literal(dialect, None)],
        [Literal(dialect, 2), Literal(dialect, 'VP Sales'), Literal(dialect, 1)],
        [Literal(dialect, 3), Literal(dialect, 'VP Engineering'), Literal(dialect, 1)],
        [Literal(dialect, 4), Literal(dialect, 'Sales Manager'), Literal(dialect, 2)],
        [Literal(dialect, 5), Literal(dialect, 'Engineer'), Literal(dialect, 3)],
    ]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Basic CTE
# ============================================================
# CTE simplifies complex queries by defining temporary named result sets

high_earners_cte = CTEExpression(
    dialect=dialect,
    name='high_earners',
    query=QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name')],
        from_=TableExpression(dialect, 'employees'),
        where=ComparisonPredicate(dialect, '>', Column(dialect, 'id'), Literal(dialect, 2)),
    ),
)

cte_query = WithQueryExpression(
    dialect=dialect,
    ctes=[high_earners_cte],
    main_query=QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name')],
        from_=TableExpression(dialect, 'high_earners'),
    ),
)
sql, params = cte_query.to_sql()
print(f"Basic CTE SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"Basic CTE result: {result.data}")

# ============================================================
# SECTION: Recursive CTE
# ============================================================
# Recursive CTE for hierarchical data (organizational chart)

# Base case: top-level employees
base_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'manager_id'),
        Literal(dialect, 1),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=ComparisonPredicate(dialect, 'IS', Column(dialect, 'manager_id'), Literal(dialect, None)),
)

org_cte = CTEExpression(
    dialect=dialect,
    name='org_chart',
    query=base_query,
    columns=['id', 'name', 'manager_id', 'level'],
)

recursive_query = WithQueryExpression(
    dialect=dialect,
    ctes=[org_cte],
    main_query=QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name'), Column(dialect, 'manager_id')],
        from_=TableExpression(dialect, 'org_chart'),
    ),
    recursive=True,
)
sql, params = recursive_query.to_sql()
print(f"Recursive CTE SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print("Recursive CTE result:")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Multiple CTEs
# ============================================================
# Multiple CTEs can be defined in a single WITH clause

active_cte = CTEExpression(
    dialect=dialect,
    name='active_employees',
    query=QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name')],
        from_=TableExpression(dialect, 'employees'),
        where=ComparisonPredicate(dialect, '>', Column(dialect, 'id'), Literal(dialect, 0)),
    ),
)

top_cte = CTEExpression(
    dialect=dialect,
    name='top_employees',
    query=QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name')],
        from_=TableExpression(dialect, 'active_employees'),
        where=ComparisonPredicate(dialect, '>', Column(dialect, 'id'), Literal(dialect, 2)),
    ),
)

multi_cte_query = WithQueryExpression(
    dialect=dialect,
    ctes=[active_cte, top_cte],
    main_query=QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name')],
        from_=TableExpression(dialect, 'top_employees'),
    ),
)
sql, params = multi_cte_query.to_sql()
print(f"Multiple CTEs SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"Multiple CTEs result: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_table = DropTableExpression(dialect=dialect, table='employees', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. CTE requires MariaDB 8.0+
# 2. Use CTEExpression to define CTEs
# 3. Use WithQueryExpression to combine CTEs with a main query
# 4. Set recursive=True for recursive CTEs (hierarchical queries)
# 5. Multiple CTEs can be defined in a single WithQueryExpression
