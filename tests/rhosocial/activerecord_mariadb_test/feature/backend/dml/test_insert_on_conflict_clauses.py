# tests/rhosocial/activerecord_mariadb_test/feature/backend/dml/test_insert_on_conflict_clauses.py
"""Tests for MariaDB ON CONFLICT (ON DUPLICATE KEY UPDATE) clause capability.

Covers:
- Capability switches: single clause supported, multiple clauses rejected.
- Single ON DUPLICATE KEY UPDATE rendering (regression for the previous
  infinite-recursion in MariaDBDMLOperationMixin.format_on_conflict_clause).
- Multiple ON CONFLICT clauses rejected by the generic gate.
"""

import pytest

from rhosocial.activerecord.backend.dialect import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    Column,
    InsertExpression,
    Literal,
    OnConflictClause,
    ValuesSource,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


class TestMariaDBOnConflictCapabilities:
    """Capability switch tests."""

    def test_supports_on_conflict_clause(self, dialect):
        assert dialect.supports_on_conflict_clause() is True

    def test_does_not_support_multiple_on_conflict_clauses(self, dialect):
        assert dialect.supports_multiple_on_conflict_clauses() is False

    def test_multiple_on_conflict_clauses_rejected(self, dialect):
        """MariaDB ON DUPLICATE KEY UPDATE allows only one clause per INSERT."""
        source = ValuesSource(dialect, values_list=[[Literal(dialect, 1)]])
        clause1 = OnConflictClause(dialect, conflict_target=["col_a"], do_nothing=True)
        clause2 = OnConflictClause(dialect, conflict_target=["col_b"], do_nothing=True)
        expr = InsertExpression(dialect, into="t", source=source, on_conflict=[clause1, clause2])

        with pytest.raises(UnsupportedFeatureError, match="multiple ON CONFLICT clauses"):
            expr.to_sql()


class TestMariaDBOnConflictRendering:
    """SQL rendering tests for a single ON CONFLICT (ON DUPLICATE KEY) clause."""

    def test_on_duplicate_key_update(self, dialect):
        source = ValuesSource(dialect, values_list=[[Literal(dialect, 1), Literal(dialect, "new")]])
        clause = OnConflictClause(
            dialect,
            conflict_target=["id"],
            update_assignments={"name": Column(dialect, "name", "excluded")},
        )
        expr = InsertExpression(
            dialect, into="users", columns=["id", "name"], source=source, on_conflict=clause
        )
        sql, params = expr.to_sql()
        assert sql == (
            'INSERT INTO `users` (`id`, `name`) VALUES (%s, %s) '
            'ON DUPLICATE KEY UPDATE `name` = `excluded`.`name`'
        )
        assert params == (1, "new")

    def test_on_duplicate_key_do_nothing_noop(self, dialect):
        """do_nothing renders the MariaDB no-op UPDATE id = id."""
        source = ValuesSource(dialect, values_list=[[Literal(dialect, 1)]])
        clause = OnConflictClause(dialect, conflict_target=["id"], do_nothing=True)
        expr = InsertExpression(dialect, into="users", columns=["id"], source=source, on_conflict=clause)
        sql, params = expr.to_sql()
        assert sql == (
            'INSERT INTO `users` (`id`) VALUES (%s) '
            'ON DUPLICATE KEY UPDATE `id` = `id`'
        )
        assert params == (1,)

    def test_insert_ignore_and_replace_still_work(self, dialect):
        """REPLACE INTO / INSERT IGNORE remain unaffected by the capability gate."""
        source = ValuesSource(dialect, values_list=[[Literal(dialect, 1)]])

        expr = InsertExpression(
            dialect, into="users", columns=["id"], source=source, dialect_options={"replace": True}
        )
        sql, _ = expr.to_sql()
        assert sql.startswith('REPLACE INTO `users`')

        expr = InsertExpression(
            dialect, into="users", columns=["id"], source=source, dialect_options={"ignore": True}
        )
        sql, _ = expr.to_sql()
        assert sql.startswith('INSERT IGNORE INTO `users`')
