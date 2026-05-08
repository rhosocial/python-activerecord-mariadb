"""
MariaDB-specific full-text search using MATCH...AGAINST.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

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

drop_table = DropTableExpression(dialect=dialect, table_name='articles', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='articles',
    columns=[
        ColumnDefinition(
            'id',
            'INT',
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition('title', 'VARCHAR(200)'),
        ColumnDefinition('content', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into='articles',
    columns=['title', 'content'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'MariaDB Tutorial'),
             Literal(dialect, 'This tutorial covers MariaDB database basics '
                             'and advanced features.')],
            [Literal(dialect, 'PostgreSQL Guide'),
             Literal(dialect, 'Learn PostgreSQL from beginner '
                             'to advanced level.')],
            [Literal(dialect, 'Database Design'),
             Literal(dialect, 'Best practices for designing relational '
                             'databases including MariaDB and PostgreSQL.')],
        ],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

sql = "CREATE FULLTEXT INDEX ft_idx ON articles (title, content)"
backend.execute(sql)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import QueryExpression, Column, TableExpression
from rhosocial.activerecord.backend.impl.mariadb.expression import MariaDBMatchAgainstExpression, MatchAgainstMode

# Use MariaDBMatchAgainstExpression for full-text search
match_expr = MariaDBMatchAgainstExpression(
    dialect=dialect,
    columns=['title', 'content'],
    search_string='MariaDB',
    mode=MatchAgainstMode.NATURAL_LANGUAGE,
)

# Create separate instances - one for SELECT with alias, one for WHERE without alias
match_with_alias = MariaDBMatchAgainstExpression(
    dialect=dialect,
    columns=['title', 'content'],
    search_string='MariaDB',
    mode=MatchAgainstMode.NATURAL_LANGUAGE,
)
match_with_alias = match_with_alias.as_('relevance')

match_for_where = MariaDBMatchAgainstExpression(
    dialect=dialect,
    columns=['title', 'content'],
    search_string='MariaDB',
    mode=MatchAgainstMode.NATURAL_LANGUAGE,
)

# Build query using expression (supports alias via as_)
query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'title'),
        match_with_alias,
    ],
    from_=TableExpression(dialect, 'articles'),
    where=(match_for_where > 0),
)

sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

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
