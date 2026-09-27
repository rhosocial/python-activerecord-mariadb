# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_derived_ddl_inline_index.py
"""MariaDB inline-index support for direct DDL expressions.

The DDLSource index declaration is passed directly to CreateTableExpression
on a dialect that advertises ``supports_inline_index()``.
"""

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

from rhosocial.activerecord.base import UseIndex
from rhosocial.activerecord.backend.expression import (
    ColumnDefinition,
    CreateTableExpression,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.model import ActiveRecord


class Indexed(ActiveRecord):
    __table_name__ = "indexed"

    id: int
    email: Annotated[str, UseIndex("idx_indexed_email", unique=True)]


def mariadb_dialect():
    return MariaDBDialect((10, 11, 0))


def _create_indexed_table():
    dialect = mariadb_dialect()
    return CreateTableExpression(
        dialect,
        Indexed.__table_name__,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect)),
            ColumnDefinition(dialect, "email", VarCharType(dialect, 255)),
        ],
        indexes=Indexed.column_indexes("email"),
    )


def test_create_table_renders_inline_index():
    expression = _create_indexed_table()

    assert [index.name for index in expression.indexes] == ["idx_indexed_email"]
    sql, _ = expression.to_sql()
    assert "UNIQUE INDEX `idx_indexed_email` (`email`)" in sql


def test_inline_index_declaration_stays_on_create_table():
    expression = _create_indexed_table()
    assert len(expression.indexes) == 1
    assert expression.indexes[0].unique is True
