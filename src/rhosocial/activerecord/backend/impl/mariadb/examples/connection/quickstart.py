"""
Quick Start: Connect to MariaDB and execute queries.

This example demonstrates:
1. How to establish a connection to MariaDB
2. How to view connection information
3. How to execute expression-based queries
4. How to access query results and handle transactions
"""

# ============================================================
# SECTION: Connection Setup
# ============================================================
import os

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    InsertExpression,
    QueryExpression,
    TableExpression,
    ValuesSource,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
)
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# Create connection configuration
config = MariaDBConnectionConfig(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    database=os.getenv('MYSQL_DATABASE', 'test_db'),
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
)

# Create backend instance and connect
backend = MariaDBBackend(connection_config=config)
backend.connect()
dialect = backend.dialect

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
ddl_options = ExecutionOptions(stmt_type=StatementType.DDL)


def execute_expression(expression, options=None):
    sql, params = expression.to_sql()
    print(f"SQL: {sql}")
    print(f"Params: {params}")
    return backend.execute(sql, params, options=options)


def create_demo_tables():
    users_table = CreateTableExpression(
        dialect=dialect,
        table_name='quickstart_users',
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
            ColumnDefinition('status', 'VARCHAR(20)'),
        ],
        if_not_exists=True,
    )
    execute_expression(users_table, ddl_options)

    logs_table = CreateTableExpression(
        dialect=dialect,
        table_name='quickstart_logs',
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
                'message',
                'VARCHAR(255)',
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
            ),
        ],
        if_not_exists=True,
    )
    execute_expression(logs_table, ddl_options)


def seed_demo_data():
    insert_users = InsertExpression(
        dialect=dialect,
        into='quickstart_users',
        columns=['name', 'status'],
        source=ValuesSource(
            dialect,
            [
                [Literal(dialect, 'Alice'), Literal(dialect, 'active')],
                [Literal(dialect, 'Bob'), Literal(dialect, 'inactive')],
            ],
        ),
    )
    execute_expression(insert_users)


create_demo_tables()
seed_demo_data()

# ============================================================
# SECTION: View Connection Information
# ============================================================
print(f"Connected to: {config.host}:{config.port}")
print(f"Database: {config.database}")
print(f"User: {config.username}")

# ============================================================
# SECTION: Execute Queries
# ============================================================
query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'status'),
    ],
    from_=TableExpression(dialect, 'quickstart_users'),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            '=',
            Column(dialect, 'status'),
            Literal(dialect, 'active'),
        ),
    ),
)
result = execute_expression(query, dql_options)

# ============================================================
# SECTION: Access Query Results
# ============================================================
print(f"Result data: {result.data}")
print(f"Rows: {result.affected_rows}")
print(f"Duration: {result.duration:.3f}s")
print(f"Last insert ID: {result.last_insert_id}")

if result.data:
    row = result.data[0]
    print(f"Value from first row: {row['name']}")

# ============================================================
# SECTION: Execute Parameterized Queries (Recommended)
# ============================================================
filtered_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'status'),
    ],
    from_=TableExpression(dialect, 'quickstart_users'),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            '=',
            Column(dialect, 'id'),
            Literal(dialect, 1),
        ) & ComparisonPredicate(
            dialect,
            '=',
            Column(dialect, 'status'),
            Literal(dialect, 'active'),
        ),
    ),
)
result = execute_expression(filtered_query, dql_options)
print(f"Parameterized query result: {result.data}")

# ============================================================
# SECTION: Handle Transactions
# ============================================================
with backend.transaction():
    insert_log = InsertExpression(
        dialect=dialect,
        into='quickstart_logs',
        columns=['message'],
        source=ValuesSource(dialect, [[Literal(dialect, 'quickstart transaction')]]),
    )
    execute_expression(insert_log)

logs_query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'id'), Column(dialect, 'message')],
    from_=TableExpression(dialect, 'quickstart_logs'),
)
result = execute_expression(logs_query, dql_options)
print(f"Transaction result: {result.data}")

# ============================================================
# SECTION: Error Handling
# ============================================================
try:
    invalid_query = QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id')],
        from_=TableExpression(dialect, 'nonexistent_table'),
    )
    execute_expression(invalid_query, dql_options)
except Exception as error:
    print(f"Error: {error}")

# ============================================================
# SECTION: Disconnect
# ============================================================
drop_logs = DropTableExpression(dialect=dialect, table_name='quickstart_logs', if_exists=True)
execute_expression(drop_logs, ddl_options)

drop_users = DropTableExpression(dialect=dialect, table_name='quickstart_users', if_exists=True)
execute_expression(drop_users, ddl_options)

backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Create MariaDBConnectionConfig with connection parameters
# 2. Create MariaDBBackend with the config and call backend.connect()
# 3. Use expressions to create schema, insert data, and query data
# 4. Use backend.transaction() for transaction control
# 5. Access QueryResult.data for returned rows
# 6. Disconnect and clean up when done
