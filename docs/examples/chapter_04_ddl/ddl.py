# docs/examples/chapter_04_ddl/ddl.py
"""Create, alter and drop a table with MariaDB-specific DDL options.

Requires a live MariaDB server and an existing database; see README.md.
"""

import os

from rhosocial.activerecord.backend.expression import (
    AlterTableStatement,
    CreateTableStatement,
    DropTableStatement,
    InsertStatement,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression import functions as F
from rhosocial.activerecord.backend.expression.core import Parameter
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnDefaultConstraint,
    ColumnDefinition,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddColumnAction
from rhosocial.activerecord.backend.expression.statements.ddl_table import IndexDefinition
from rhosocial.activerecord.backend.expression.types import (
    DecimalType,
    IntegerType,
    TimestampType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.impl.mariadb.expression import MariaDBCreateTableOptions
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

TABLE_NAME = "docs_example_products"


def execute(backend, expression, statement_type=None) -> None:
    """Render an expression, print it, and execute it."""
    sql, params = expression.to_sql()
    print("SQL:", sql)
    print("Params:", params)
    options = ExecutionOptions(stmt_type=statement_type) if statement_type else None
    backend.execute(sql, params, options=options)


def column_definitions(dialect):
    return [
        ColumnDefinition(
            dialect,
            name="id",
            data_type=IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))],
        ),
        ColumnDefinition(
            dialect,
            name="name",
            data_type=VarCharType(dialect, 200),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))],
        ),
        ColumnDefinition(dialect, name="price", data_type=DecimalType(dialect, 10, 2)),
        ColumnDefinition(
            dialect,
            name="created_at",
            data_type=TimestampType(dialect),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, F.current_timestamp(dialect)))
            ],
        ),
    ]


def main() -> None:
    config = MariaDBConnectionConfig(
        host=os.getenv("MARIADB_HOST", "localhost"),
        port=int(os.getenv("MARIADB_PORT", "3306")),
        database=os.getenv("MARIADB_DATABASE", "test_db"),
        username=os.getenv("MARIADB_USERNAME", "app"),
        password=os.getenv("MARIADB_PASSWORD", ""),
        charset="utf8mb4",
    )
    backend = MariaDBBackend(connection_config=config)
    backend.connect()
    dialect = backend.dialect

    ddl = StatementType.DDL
    try:
        execute(backend, DropTableStatement(dialect=dialect, table=Table(dialect, TABLE_NAME), if_exists=True), ddl)

        create = CreateTableStatement(
            dialect=dialect,
            table=Table(dialect, TABLE_NAME),
            columns=column_definitions(dialect),
            indexes=[IndexDefinition(dialect, name="idx_docs_products_name", columns=["name"])],
            if_not_exists=True,
            table_options=MariaDBCreateTableOptions(dialect, engine="InnoDB", charset="utf8mb4"),
        )
        execute(backend, create, ddl)

        execute(
            backend,
            InsertStatement(
                dialect=dialect,
                into=Table(dialect, TABLE_NAME),
                columns=["name", "price"],
                source=ValuesSource(dialect, [[Parameter(dialect, "Widget"), Parameter(dialect, 9.99)]]),
            ),
        )

        execute(
            backend,
            AlterTableStatement(
                dialect=dialect,
                table=Table(dialect, TABLE_NAME),
                actions=[
                    AddColumnAction(
                        dialect,
                        column=ColumnDefinition(dialect, name="note", data_type=VarCharType(dialect, 100)),
                    )
                ],
            ),
            ddl,
        )

        for column in backend.introspector.list_columns(TABLE_NAME):
            print("Column:", column.name, column.data_type_full)
    finally:
        execute(backend, DropTableStatement(dialect=dialect, table=Table(dialect, TABLE_NAME), if_exists=True), ddl)
        backend.disconnect()


if __name__ == "__main__":
    main()
