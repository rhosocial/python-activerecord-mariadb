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


def test_auto_increment_row_format_and_system_versioning():
    from rhosocial.activerecord.backend.impl.mariadb.expression import MariaDBRowFormat

    dialect = MariaDBDialect(version=(10, 6, 0))
    options = MariaDBCreateTableOptions(
        dialect,
        auto_increment=100,
        row_format=MariaDBRowFormat.PAGE,
        with_system_versioning=True,
    )
    expr = CreateTableExpression(
        dialect,
        "t",
        [ColumnDefinition(dialect, "id", IntegerType(dialect))],
        table_options=options,
    )
    sql, _ = expr.to_sql()
    assert "AUTO_INCREMENT=100" in sql
    assert "ROW_FORMAT=PAGE" in sql
    assert "WITH SYSTEM VERSIONING" in sql


def test_system_versioning_gated_below_10_3():
    from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

    dialect = MariaDBDialect(version=(10, 2, 0))
    options = MariaDBCreateTableOptions(dialect, with_system_versioning=True)
    expr = CreateTableExpression(
        dialect,
        "t",
        [ColumnDefinition(dialect, "id", IntegerType(dialect))],
        table_options=options,
    )
    import pytest

    with pytest.raises(UnsupportedFeatureError, match="SYSTEM VERSIONING"):
        expr.to_sql()
