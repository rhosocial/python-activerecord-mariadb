"""
Retrieve auto-generated ID after INSERT - MariaDB.

This example demonstrates:
1. INSERT and retrieve auto-generated ID using LAST_INSERT_ID()
2. MariaDB does not support RETURNING clause (unlike PostgreSQL/SQLite 3.35+)
3. Using SELECT LAST_INSERT_ID() as the MariaDB alternative
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
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column, FunctionCall
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
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

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

drop_table = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
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

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# 1. Insert a row
insert_expr = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['name', 'email'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'Alice'), Literal(dialect, 'alice@example.com')],
    ]),
)
sql, params = insert_expr.to_sql()
print(f"INSERT SQL: {sql}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print(f"Affected rows: {result.affected_rows}")

# 2. Retrieve auto-generated ID using LAST_INSERT_ID()
# MariaDB does NOT support RETURNING clause (unlike PostgreSQL/SQLite 3.35+)
# Use SELECT LAST_INSERT_ID() instead
query_id = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'LAST_INSERT_ID').as_('generated_id')],
)
sql, params = query_id.to_sql()
print(f"LAST_INSERT_ID SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"Generated ID: {result.data}")

# 3. Verify by querying the inserted row
verify_query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'id'), Column(dialect, 'name'), Column(dialect, 'email')],
    from_=TableExpression(dialect, 'users'),
)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params, options=dql_options)
print(f"Users: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_table = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. MariaDB does NOT support RETURNING clause (unlike PostgreSQL and SQLite 3.35+)
# 2. Use SELECT LAST_INSERT_ID() to get the auto-generated ID after INSERT
# 3. LAST_INSERT_ID() returns the first auto-generated value of the most recent INSERT
# 4. For batch inserts, LAST_INSERT_ID() returns the first ID; subsequent IDs are consecutive
# 5. Consider using UPSERT (ON DUPLICATE KEY UPDATE) when you need idempotent inserts
