# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/ddl/test_alter_table_index_actions.py
"""MariaDB supports ADD/DROP INDEX through ALTER TABLE on every version.

The core formatter emits ``ALTER TABLE ... ADD INDEX <name> (<cols>)`` and
``ALTER TABLE ... DROP INDEX <name>``, both of which MariaDB accepts; the probe
must therefore answer True rather than inherit core's conservative default.
"""

import pytest

from rhosocial.activerecord.backend.expression.objects import Index, Table
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddIndexAction,
    AlterTableStatement,
    DropIndexAction,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    IndexDefinition,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


@pytest.fixture
def dialect():
    return MariaDBDialect((11, 4, 0))


def test_probe_is_true(dialect):
    assert dialect.supports_alter_table_index_actions() is True


def test_add_index_renders(dialect):
    index = IndexDefinition(dialect, "idx_name", ["a", "b"])
    statement = AlterTableStatement(dialect, Table(dialect, "t"), [AddIndexAction(dialect, index)])
    sql, params = statement.to_sql()
    assert "ADD INDEX `idx_name` (`a`, `b`)" in sql
    assert params == ()


def test_drop_index_renders(dialect):
    statement = AlterTableStatement(
        dialect, Table(dialect, "t"), [DropIndexAction(dialect, Index(dialect, "idx_name"))]
    )
    sql, params = statement.to_sql()
    assert "DROP INDEX `idx_name`" in sql
    assert params == ()
