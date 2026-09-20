# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_table_option_capabilities.py
"""Explicit MariaDB table-option capability + rendering assertions.

MariaDB carries ENGINE / CHARSET / COLLATE as typed fields on
``MariaDBCreateTableOptions``; this pins the supporting capability bit and
verifies the typed options are rendered.
"""

from rhosocial.activerecord.backend.expression import CreateTableExpression
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBCreateTableOptions,
)


def test_storage_engine_option_supported():
    assert MariaDBDialect(version=(10, 6, 0)).supports_storage_engine_option() is True


def test_engine_and_charset_rendered_from_typed_options():
    dialect = MariaDBDialect(version=(10, 6, 0))
    expr = CreateTableExpression(
        dialect,
        table="t",
        columns=[ColumnDefinition(dialect, "id", IntegerType(dialect))],
        table_options=MariaDBCreateTableOptions(
            dialect, engine="InnoDB", charset="utf8mb4"
        ),
    )
    sql, _ = expr.to_sql()
    assert "ENGINE=" in sql and "InnoDB" in sql
    assert "DEFAULT CHARSET=" in sql and "utf8mb4" in sql
