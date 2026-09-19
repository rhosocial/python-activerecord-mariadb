# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_derived_ddl_inline_index.py
"""MariaDB inline-index support for ActiveRecord-derived DDL (positive path).

SQLite and other SQL-standard dialects cannot inline index definitions, so the
positive rendering path is exercised here on a dialect that supports it
(``supports_inline_index()`` is True).
"""

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

from rhosocial.activerecord.base import UseIndex
from rhosocial.activerecord.base.ddl import TableDDLDeriver
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.model import ActiveRecord


class Indexed(ActiveRecord):
    __table_name__ = "indexed"

    id: int
    email: Annotated[str, UseIndex("idx_indexed_email", unique=True)]


def mariadb_dialect():
    return MariaDBDialect((10, 11, 0))


def test_create_table_renders_inline_index():
    deriver = TableDDLDeriver(Indexed, mariadb_dialect())
    expression = deriver.create_table()

    assert [index.name for index in expression.indexes] == ["idx_indexed_email"]
    sql, _ = expression.to_sql()
    assert "UNIQUE INDEX `idx_indexed_email` (`email`)" in sql


def test_create_indexes_is_empty_when_inline_capable():
    deriver = TableDDLDeriver(Indexed, mariadb_dialect())
    assert deriver.create_indexes() == []


def test_create_schema_is_a_single_statement():
    deriver = TableDDLDeriver(Indexed, mariadb_dialect())
    plan = deriver.create_schema()
    assert len(plan) == 1
    assert isinstance(plan[0], CreateTableExpression)
