"""
UPSERT (INSERT ... ON DUPLICATE KEY UPDATE) - MariaDB.

This example demonstrates:
1. INSERT ... ON DUPLICATE KEY UPDATE
2. Using OnConflictClause for upsert
3. Affected rows tracking
4. UPSERT with multiple values
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
    DropTableExpression,
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    OnConflictClause,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

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
        ColumnDefinition('id', 'INT', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('username', 'VARCHAR(100)', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
            ColumnConstraint(ColumnConstraintType.UNIQUE),
        ]),
        ColumnDefinition('email', 'VARCHAR(100)', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('login_count', 'INT', constraints=[
            ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0),
        ]),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: INSERT ON DUPLICATE KEY UPDATE
# ============================================================
# MariaDB uses ON DUPLICATE KEY UPDATE, which is handled via OnConflictClause

# Initial insert
insert_expr = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['username', 'email', 'login_count'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'alice'), Literal(dialect, 'alice@example.com'), Literal(dialect, 1)],
    ]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)

# Verify initial insert
query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'username'),
        Column(dialect, 'email'),
        Column(dialect, 'login_count'),
    ],
    from_=TableExpression(dialect, 'users'),
    where=ComparisonPredicate(dialect, '=', Column(dialect, 'username'), Literal(dialect, 'alice')),
)
sql, params = query.to_sql()
result = backend.execute(sql, params, options=dql_options)
print(f"Initial insert: {result.data}")

# Insert again with ON DUPLICATE KEY UPDATE - will update
upsert_expr = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['username', 'email', 'login_count'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'alice'), Literal(dialect, 'alice@example.com'), Literal(dialect, 1)],
    ]),
    on_conflict=OnConflictClause(
        dialect,
        None,
        update_assignments={
            'login_count': Column(dialect, 'login_count'),
        },
    ),
)
sql, params = upsert_expr.to_sql()
print(f"UPSERT SQL: {sql}")
backend.execute(sql, params)

# Verify after upsert
sql, params = query.to_sql()
result = backend.execute(sql, params, options=dql_options)
print(f"After UPSERT: {result.data}")

# ============================================================
# SECTION: UPSERT with affected rows
# ============================================================
# affected_rows: 1 = inserted, 2 = updated

insert_result = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['username', 'email', 'login_count'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'charlie'), Literal(dialect, 'charlie@example.com'), Literal(dialect, 1)],
    ]),
)
sql, params = insert_result.to_sql()
result = backend.execute(sql, params)
print(f"Insert affected_rows: {result.affected_rows}")

upsert_result = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['username', 'email', 'login_count'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'charlie'), Literal(dialect, 'charlie@example.com'), Literal(dialect, 1)],
    ]),
    on_conflict=OnConflictClause(
        dialect,
        None,
        update_assignments={
            'login_count': Column(dialect, 'login_count'),
        },
    ),
)
sql, params = upsert_result.to_sql()
result = backend.execute(sql, params)
print(f"Update affected_rows: {result.affected_rows}")

# ============================================================
# SECTION: Multiple row UPSERT
# ============================================================
# MariaDB supports multiple row VALUES()

multi_upsert = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['username', 'email', 'login_count'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'david'), Literal(dialect, 'david@example.com'), Literal(dialect, 1)],
        [Literal(dialect, 'eve'), Literal(dialect, 'eve@example.com'), Literal(dialect, 1)],
    ]),
    on_conflict=OnConflictClause(
        dialect,
        None,
        update_assignments={
            'login_count': Column(dialect, 'login_count'),
        },
    ),
)
sql, params = multi_upsert.to_sql()
print(f"Multi-row UPSERT SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_orders = DropTableExpression(dialect=dialect, table_name='orders', if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_table = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Requires unique key or primary key for conflict detection
# 2. Use OnConflictClause with update_assignments for ON DUPLICATE KEY UPDATE
# 3. MariaDB auto-detects conflict by unique key (conflict_target=None)
# 4. affected_rows = 1 for insert, 2 for update
# 5. Works with multiple rows at once
