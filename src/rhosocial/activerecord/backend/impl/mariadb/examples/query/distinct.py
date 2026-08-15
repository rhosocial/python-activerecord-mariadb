"""
DISTINCT using SelectModifier - MariaDB.

This example demonstrates:
1. SELECT DISTINCT
2. SELECT DISTINCT with multiple columns
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
)
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
)

# Drop dependent tables first for clean setup
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
        ColumnDefinition('id', 'INT'),
        ColumnDefinition('name', 'VARCHAR(100)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['id', 'name'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 1), Literal(dialect, 'Alice')],
        [Literal(dialect, 2), Literal(dialect, 'Bob')],
        [Literal(dialect, 3), Literal(dialect, 'Alice')],
    ]),
)
sql, params = insert.to_sql()
print(f"Insert SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: SELECT DISTINCT
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    SelectModifier,
)

query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'name')],
    from_=TableExpression(dialect, 'users'),
    select_modifier=SelectModifier.DISTINCT,
)
sql, params = query.to_sql()
print(f"SELECT DISTINCT SQL: {sql}")
print(f"Params: {params}")

options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"DISTINCT result: {result.data}")

# ============================================================
# SECTION: SELECT DISTINCT with multiple columns
# ============================================================
query_distinct = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'id'), Column(dialect, 'name')],
    from_=TableExpression(dialect, 'users'),
    select_modifier=SelectModifier.DISTINCT,
)
sql, params = query_distinct.to_sql()
print(f"SELECT DISTINCT multi-col SQL: {sql}")
result = backend.execute(sql, params, options=options)
print(f"Multi-col result: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_orders = DropTableExpression(dialect=dialect, table_name='orders', if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_expr = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_expr.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use SelectModifier.DISTINCT in QueryExpression
# 2. SELECT DISTINCT removes duplicate rows
# 3. Works with multiple columns (distinct combo)