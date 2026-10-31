"""
Aggregate queries with GROUP BY and HAVING.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.expression.objects import Table


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

from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    InsertStatement,
    ValuesSource,
    DropTableStatement,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType,
    VarCharType,
    DecimalType,
)

drop_table = DropTableStatement(dialect=dialect, table=Table(dialect, 'sales'), if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableStatement(
    dialect=dialect,
    table=Table(dialect, 'sales'),
    columns=[
        ColumnDefinition(
            dialect,
            'id',
            IntegerType(dialect),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, 'product', VarCharType(dialect, 100)),
        ColumnDefinition(dialect, 'quantity', IntegerType(dialect)),
        ColumnDefinition(dialect, 'price', DecimalType(dialect, 10, 2)),
        ColumnDefinition(dialect, 'region', VarCharType(dialect, 50)),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertStatement(
    dialect=dialect,
    into=Table(dialect, 'sales'),
    columns=['product', 'quantity', 'price', 'region'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'Widget'), Literal(dialect, 10), Literal(dialect, 5.00), Literal(dialect, 'North')],
            [Literal(dialect, 'Widget'), Literal(dialect, 5), Literal(dialect, 5.00), Literal(dialect, 'South')],
            [Literal(dialect, 'Gadget'), Literal(dialect, 8), Literal(dialect, 10.00), Literal(dialect, 'North')],
            [Literal(dialect, 'Gadget'), Literal(dialect, 3), Literal(dialect, 10.00), Literal(dialect, 'South')],
            [Literal(dialect, 'Widget'), Literal(dialect, 7), Literal(dialect, 5.00), Literal(dialect, 'East')],
        ],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryStatement,
    Column,
    GroupByHavingClause,
)
from rhosocial.activerecord.backend.expression import functions as F  # noqa: E402
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
query = QueryStatement(
    dialect=dialect,
    select=[
        Column(dialect, 'product'),
        F.sum_(dialect, Column(dialect, 'quantity'), alias='total_qty'),
        F.avg(dialect, Column(dialect, 'price'), alias='avg_price'),
    ],
    from_=Table(dialect, 'sales'),
    group_by_having=GroupByHavingClause(
        dialect,
        group_by=[Column(dialect, 'product')],
        having=ComparisonPredicate(
            dialect,
            '>',
            F.sum_(dialect, Column(dialect, 'quantity')),
            Literal(dialect, 10),
        ),
    ),
)

sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
