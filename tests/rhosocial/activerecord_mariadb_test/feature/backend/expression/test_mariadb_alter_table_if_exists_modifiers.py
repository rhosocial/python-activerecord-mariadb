# tests/rhosocial/activerecord_mariadb_test/feature/backend/expression/test_alter_table_if_exists.py
"""Tests for MariaDB ALTER TABLE IF [NOT] EXISTS qualifier rendering.

MariaDB supports the vendor qualifiers since 10.0.2 for ADD COLUMN,
DROP COLUMN, and (named) DROP CONSTRAINT. The special DROP PRIMARY KEY
form never takes IF EXISTS.
"""

import pytest

from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddColumn,
    DropColumn,
    DropTableConstraint,
)
from rhosocial.activerecord.backend.expression.types import TextType
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


class TestMariaDBAlterTableModifierCapabilities:
    def test_supports_switches(self, dialect):
        assert dialect.supports_add_column_if_not_exists() is True
        assert dialect.supports_drop_column_if_exists() is True
        assert dialect.supports_drop_constraint_if_exists() is True


class TestMariaDBAddColumnIfNotExists:
    def test_if_not_exists_renders_qualifier(self, dialect):
        action = AddColumn(
            dialect,
            ColumnDefinition("content", TextType()),
            if_not_exists=True,
        )
        sql, params = action.to_sql()
        assert "ADD COLUMN IF NOT EXISTS `content` TEXT" == sql
        assert params == ()

    def test_none_renders_plain_form(self, dialect):
        action = AddColumn(dialect, ColumnDefinition("content", TextType()))
        sql, params = action.to_sql()
        assert "ADD COLUMN `content` TEXT" == sql
        assert "IF NOT EXISTS" not in sql
        assert params == ()


class TestMariaDBDropColumnIfExists:
    def test_if_exists_renders_qualifier(self, dialect):
        action = DropColumn(dialect, column_name="x", if_exists=True)
        sql, params = action.to_sql()
        assert "DROP COLUMN IF EXISTS `x`" == sql
        assert params == ()

    def test_none_renders_plain_form(self, dialect):
        action = DropColumn(dialect, column_name="x")
        sql, params = action.to_sql()
        assert "DROP COLUMN `x`" == sql
        assert "IF EXISTS" not in sql
        assert params == ()


class TestMariaDBDropConstraintIfExists:
    def test_if_exists_renders_qualifier(self, dialect):
        action = DropTableConstraint(
            dialect, constraint_name="fk", if_exists=True
        )
        sql, params = action.to_sql()
        assert "DROP CONSTRAINT IF EXISTS `fk`" == sql
        assert params == ()

    def test_primary_key_never_has_qualifier(self, dialect):
        action = DropTableConstraint(
            dialect, constraint_name="PRIMARY", if_exists=True
        )
        sql, params = action.to_sql()
        assert "DROP PRIMARY KEY" == sql
        assert "IF EXISTS" not in sql
        assert params == ()

    def test_none_renders_plain_form(self, dialect):
        action = DropTableConstraint(dialect, constraint_name="fk")
        sql, params = action.to_sql()
        assert "DROP CONSTRAINT `fk`" == sql
        assert "IF EXISTS" not in sql
        assert params == ()