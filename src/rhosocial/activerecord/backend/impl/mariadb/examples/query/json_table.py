"""
MariaDB JSON_TABLE - Convert JSON data to relational format (MariaDB 8.0+).

Demonstrates using MariaDBJSONTableExpression with QueryExpression to build
a SELECT query that flattens JSON array data into relational rows.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    database=os.getenv("MYSQL_DATABASE", "test"),
    username=os.getenv("MYSQL_USERNAME", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    charset="utf8mb4",
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
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

drop_table = DropTableExpression(dialect=dialect, table="orders", if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table="orders",
    columns=[
        ColumnDefinition(
            "id",
            "INT",
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition("order_data", "JSON"),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into="orders",
    columns=["order_data"],
    source=ValuesSource(
        dialect,
        [
            [
                Literal(
                    dialect,
                    '{"customer": "Alice", "items": '
                    '[{"product": "Widget", "qty": 5, "price": 10.00}, '
                    '{"product": "Gadget", "qty": 3, "price": 15.00}]}',
                )
            ],
            [Literal(dialect, '{"customer": "Bob", "items": [{"product": "Widget", "qty": 2, "price": 10.00}]}')],
        ],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.json_table import (
    MariaDBJSONTableExpression,
    JSONTableColumn,
)

json_table = MariaDBJSONTableExpression(
    dialect=dialect,
    json_doc="o.order_data",
    path="$.items[*]",
    columns=[
        JSONTableColumn(name="product", type="VARCHAR(100)", path="$.product"),
        JSONTableColumn(name="qty", type="INT", path="$.qty"),
        JSONTableColumn(name="price", type="DECIMAL(10,2)", path="$.price"),
    ],
    alias="items",
)

json_table_sql, json_table_params = json_table.to_sql()
print(f"JSON_TABLE SQL: {json_table_sql}")

# Build the query using QueryExpression with a comma-separated FROM clause
# (equivalent to an implicit CROSS JOIN).
# Note: MariaDBJSONTableExpression is not yet in the FromSourceType validation whitelist,
# so we temporarily disable strict validation when generating SQL.
query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, "id", table="o"),
        Column(dialect, "product", table="items"),
        Column(dialect, "qty", table="items"),
        Column(dialect, "price", table="items"),
    ],
    from_=[
        TableExpression(dialect, "orders", alias="o"),
        json_table,
    ],
)

# Temporarily disable strict validation to allow MariaDBJSONTableExpression in FROM
original_strict = dialect.strict_validation
dialect.strict_validation = False
sql, params = query.to_sql()
dialect.strict_validation = original_strict
print(f"Query SQL: {sql}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
