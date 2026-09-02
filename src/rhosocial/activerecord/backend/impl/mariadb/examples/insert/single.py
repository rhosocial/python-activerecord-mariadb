"""
Single row insert - MariaDB.

This example demonstrates:
1. INSERT a single row with explicit column values
2. INSERT with AUTO_INCREMENT primary key
3. Verify inserted data using QueryExpression
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    QueryExpression,
    TableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal, WildcardExpression, Column
from rhosocial.activerecord.backend.expression.statements.dql import OrderByClause
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

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

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

# Drop dependent tables first for clean setup
drop_orders = DropTableExpression(dialect=dialect, table='orders', if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop = DropTableExpression(dialect=dialect, table='users', if_exists=True)
sql, params = drop.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table='users',
    columns=[
        ColumnDefinition(
            'id',
            'INT',
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition('name', 'VARCHAR(100)', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('email', 'VARCHAR(200)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# 1. Insert a single row with explicit column values
insert_expr = InsertExpression(
    dialect=dialect,
    into=TableExpression(dialect, 'users'),
    source=ValuesSource(dialect, [
        [Literal(dialect, 'Alice'), Literal(dialect, 'alice@example.com')],
    ]),
    columns=['name', 'email'],
)
sql, params = insert_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print(f"Affected rows: {result.affected_rows}")

# Verify the inserted row
verify_query = QueryExpression(
    dialect=dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, 'users'),
    where=ComparisonPredicate(
        dialect, '=',
        Column(dialect, 'name'),
        Literal(dialect, 'Alice'),
    ),
)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params, options=dql_options)
print(f"Inserted row: {result.data}")

# 2. Insert another row (AUTO_INCREMENT id will be assigned automatically)
insert_expr2 = InsertExpression(
    dialect=dialect,
    into=TableExpression(dialect, 'users'),
    source=ValuesSource(dialect, [
        [Literal(dialect, 'Bob'), Literal(dialect, 'bob@example.com')],
    ]),
    columns=['name', 'email'],
)
sql, params = insert_expr2.to_sql()
result = backend.execute(sql, params)
print(f"Second insert affected rows: {result.affected_rows}")

# Verify all rows
all_query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'id'), Column(dialect, 'name'), Column(dialect, 'email')],
    from_=TableExpression(dialect, 'users'),
    order_by=OrderByClause(dialect, [Column(dialect, 'id')]),
)
sql, params = all_query.to_sql()
result = backend.execute(sql, params, options=dql_options)
print(f"All rows: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
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
# 1. Use InsertExpression with ValuesSource containing a single row list
# 2. AUTO_INCREMENT columns are omitted from the insert columns list
# 3. Verify inserts using QueryExpression with WHERE clause
# 4. MariaDB returns affected_rows = 1 for successful single insert
