# tests/rhosocial/activerecord_mariadb_test/feature/backend/expression/test_expression_signatures.py
"""Tests for MariaDB SET type expression classes.

This module tests the following expression classes:
- MariaDBSetLiteralExpression
- MariaDBFindInSetExpression
- MariaDBSetContainsExpression
"""
import pytest
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBSetLiteralExpression,
    MariaDBFindInSetExpression,
    MariaDBSetContainsExpression,
)


class TestMariaDBSetLiteralExpression:
    """Test MariaDBSetLiteralExpression class."""

    def test_set_literal_basic(self):
        """Test basic SET literal expression."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = MariaDBSetLiteralExpression(dialect, ['read', 'write'])
        sql, params = expr.to_sql()

        assert sql == "%s"
        assert len(params) == 1
        assert params[0] == "read,write"

    def test_set_literal_with_column_values(self):
        """Test SET literal expression with column values validation."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = MariaDBSetLiteralExpression(
            dialect,
            ['read', 'write'],
            column_values=['read', 'write', 'execute']
        )
        sql, params = expr.to_sql()

        assert sql == "%s"
        assert len(params) == 1
        assert params[0] == "read,write"


class TestMariaDBFindInSetExpression:
    """Test MariaDBFindInSetExpression class."""

    def test_find_in_set_basic(self):
        """Test basic FIND_IN_SET expression."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = MariaDBFindInSetExpression(dialect, 'read', 'permissions')
        sql, params = expr.to_sql()

        assert "FIND_IN_SET" in sql
        assert "`permissions`" in sql
        assert params == ('read',)

    def test_find_in_set_with_alias(self):
        """Test FIND_IN_SET expression with alias."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = MariaDBFindInSetExpression(
            dialect, 'read', 'permissions'
        ).as_('has_read')
        sql, params = expr.to_sql()

        assert "FIND_IN_SET" in sql
        assert "AS `has_read`" in sql
        assert params == ('read',)


class TestMariaDBSetContainsExpression:
    """Test MariaDBSetContainsExpression class."""

    def test_set_contains_basic(self):
        """Test basic SET contains expression."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = MariaDBSetContainsExpression(
            dialect, 'permissions', ['read', 'write']
        )
        sql, params = expr.to_sql()

        assert "FIND_IN_SET" in sql
        assert "`permissions`" in sql
        assert params == ('read', 'write')

    def test_set_contains_with_alias(self):
        """Test SET contains expression with alias."""
        dialect = MariaDBDialect(version=(10, 6, 0))

        expr = MariaDBSetContainsExpression(
            dialect, 'permissions', ['read', 'write']
        ).as_('contains_all')
        sql, params = expr.to_sql()

        assert "FIND_IN_SET" in sql
        assert "AS `contains_all`" in sql
        assert params == ('read', 'write')
