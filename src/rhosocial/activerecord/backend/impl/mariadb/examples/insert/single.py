"""
Single row insert - MariaDB.

This example demonstrates:
1. INSERT a single row with explicit column values
2. INSERT with AUTO_INCREMENT primary key
3. Verify inserted data using QueryStatement
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    DropTableStatement,
    QueryStatement,
    InsertStatement,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal, AllColumnsWildcard, Column
from rhosocial.activerecord.backend.expression.statements.dql import OrderByClause
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnNotNullConstraint,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType,
    VarCharType,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.expression.objects import Table

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
drop_orders = DropTableStatement(dialect=dialect, table=Table(dialect, 'orders'), if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop = DropTableStatement(dialect=dialect, table=Table(dialect, 'users'), if_exists=True)
sql, params = drop.to_sql()
backend.execute(sql, params)

create_table = CreateTableStatement(
    dialect=dialect,
    table=Table(dialect, 'users'),
    columns=[
        ColumnDefinition(
            dialect,
            'id',
            IntegerType(dialect),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, 'name', VarCharType(dialect, 100), constraints=[
            ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
        ]),
        ColumnDefinition(dialect, 'email', VarCharType(dialect, 200)),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# 1. Insert a single row with explicit column values
insert_expr = InsertStatement(
    dialect=dialect,
    into=Table(dialect, 'users'),
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
verify_query = QueryStatement(
    dialect=dialect,
    select=[AllColumnsWildcard(dialect)],
    from_=Table(dialect, 'users'),
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
insert_expr2 = InsertStatement(
    dialect=dialect,
    into=Table(dialect, 'users'),
    source=ValuesSource(dialect, [
        [Literal(dialect, 'Bob'), Literal(dialect, 'bob@example.com')],
    ]),
    columns=['name', 'email'],
)
sql, params = insert_expr2.to_sql()
result = backend.execute(sql, params)
print(f"Second insert affected rows: {result.affected_rows}")

# Verify all rows
all_query = QueryStatement(
    dialect=dialect,
    select=[Column(dialect, 'id'), Column(dialect, 'name'), Column(dialect, 'email')],
    from_=Table(dialect, 'users'),
    order_by=OrderByClause(dialect, [Column(dialect, 'id')]),
)
sql, params = all_query.to_sql()
result = backend.execute(sql, params, options=dql_options)
print(f"All rows: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_orders = DropTableStatement(dialect=dialect, table=Table(dialect, 'orders'), if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_table = DropTableStatement(dialect=dialect, table=Table(dialect, 'users'), if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use InsertStatement with ValuesSource containing a single row list
# 2. AUTO_INCREMENT columns are omitted from the insert columns list
# 3. Verify inserts using QueryStatement with WHERE clause
# 4. MariaDB returns affected_rows = 1 for successful single insert
