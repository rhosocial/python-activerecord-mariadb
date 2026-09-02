"""
CREATE VIEW - MariaDB.

This example demonstrates:
1. CREATE VIEW
2. CREATE OR REPLACE VIEW
3. Drop view
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

# Drop dependent tables first for clean setup (orders may reference users via FK)
drop_orders = DropTableExpression(dialect=dialect, table='orders', if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_users = DropTableExpression(dialect=dialect, table='users', if_exists=True)
sql, params = drop_users.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table='users',
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
    ]),
)
sql, params = insert.to_sql()
print(f"Insert SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: CREATE VIEW
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    CreateViewExpression,
    DropViewExpression,
)
from rhosocial.activerecord.backend.expression.core import WildcardExpression

query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'name')],
    from_=TableExpression(dialect, 'users'),
)

view_expr = CreateViewExpression(
    dialect=dialect,
    view_name='user_names',
    query=query,
)
sql, params = view_expr.to_sql()
print(f"CREATE VIEW SQL: {sql}")
print(f"Params: {params}")

options = ExecutionOptions(stmt_type=StatementType.DDL)
backend.execute(sql, params, options=options)

verify_query = QueryExpression(
    dialect=dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, 'user_names'),
)
options = ExecutionOptions(stmt_type=StatementType.DQL)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params, options=options)
print(f"View result: {result.data}")

# ============================================================
# SECTION: CREATE OR REPLACE VIEW
# ============================================================
view_expr_replace = CreateViewExpression(
    dialect=dialect,
    view_name='user_names',
    query=query,
    replace=True,
)
sql, params = view_expr_replace.to_sql()
print(f"CREATE OR REPLACE VIEW SQL: {sql}")
backend.execute(sql, params, options=options)

# ============================================================
# SECTION: DROP VIEW
# ============================================================
drop_view = DropViewExpression(
    dialect=dialect,
    view_name='user_names',
)
sql, params = drop_view.to_sql()
print(f"DROP VIEW SQL: {sql}")
backend.execute(sql, params, options=options)

# ============================================================
# SECTION: Teardown
# ============================================================
drop_orders = DropTableExpression(dialect=dialect, table='orders', if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_expr = DropTableExpression(dialect=dialect, table='users', if_exists=True)
sql, params = drop_expr.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use CreateViewExpression to create views
# 2. Use replace=True to replace existing view
# 3. Use DropViewExpression to drop views