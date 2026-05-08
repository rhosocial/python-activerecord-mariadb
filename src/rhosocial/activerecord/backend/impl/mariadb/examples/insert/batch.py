"""
Batch insert with multiple rows.
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
)
from rhosocial.activerecord.backend.expression.functions.datetime import current_timestamp
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
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

# Drop table first for clean setup
drop_table = DropTableExpression(dialect=dialect, table_name='logs', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='logs',
    columns=[
        ColumnDefinition(
            'id',
            'INT',
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition('level', 'VARCHAR(20)'),
        ColumnDefinition('message', 'TEXT'),
        ColumnDefinition(
            'created_at',
            'TIMESTAMP',
            constraints=[
                ColumnConstraint(
                    ColumnConstraintType.DEFAULT,
                    default_value=current_timestamp(dialect),
                ),
            ],
        ),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    ValuesSource,
    TableExpression,
    QueryExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, WildcardExpression, Column
from rhosocial.activerecord.backend.expression.statements.dql import OrderByClause

insert_expr = InsertExpression(
    dialect=dialect,
    into=TableExpression(dialect, 'logs'),
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'INFO'), Literal(dialect, 'System started')],
            [Literal(dialect, 'DEBUG'), Literal(dialect, 'Loading configuration')],
            [Literal(dialect, 'INFO'), Literal(dialect, 'Application ready')],
            [Literal(dialect, 'WARNING'), Literal(dialect, 'Memory usage high')],
        ],
    ),
    columns=['level', 'message'],
)

sql, params = insert_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print(f"Affected rows: {result.affected_rows}")

verify_query = QueryExpression(
    dialect=dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, 'logs'),
    order_by=OrderByClause(dialect, [Column(dialect, 'id')]),
)
options = ExecutionOptions(stmt_type=StatementType.DQL)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params, options=options)
print(f"Total rows in table: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
