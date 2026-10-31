# tests/rhosocial/activerecord_mariadb_test/feature/backend/dml/test_insert_bare_values_cells.py
"""INSERT VALUES cells that are bare host values, not expressions.

Core has collected the "expression versus bare host value" judgement in the
base ``format_insert_values_source`` (commit 8e2e4d82): a cell that is not
an expression binds behind a placeholder instead of crashing on a missing
``to_sql``. MariaDB's INSERT and REPLACE overrides used to re-implement the
VALUES branch, so a bare cell broke there even though the base had the
answer; both now delegate, and these cases pin that.

The assertions are render-only: the SQL text and the parameter tuple are
the contract being checked, and a live execution would add nothing to it.
"""
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    InsertStatement,
    ValuesSource,
)
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBInsertExpression,
)


class TestInsertBareValuesCells:
    """A bare scalar cell binds; an expression cell renders itself."""

    def test_plain_insert_binds_bare_cells(self, mariadb_dialect):
        table = Table(mariadb_dialect, "probe_bare")
        expr = InsertStatement(
            mariadb_dialect,
            into=table,
            columns=["a", "b"],
            source=ValuesSource(mariadb_dialect, [[1, "x"]]),
        )
        sql, params = expr.to_sql()
        assert sql == "INSERT INTO `probe_bare` (`a`, `b`) VALUES (%s, %s)"
        assert params == (1, "x")

    def test_insert_ignore_keeps_prefix_and_binds_bare_cells(self, mariadb_dialect):
        table = Table(mariadb_dialect, "probe_bare")
        expr = MariaDBInsertExpression(
            mariadb_dialect,
            into=table,
            columns=["a", "b"],
            source=ValuesSource(mariadb_dialect, [[7, "y"]]),
            ignore=True,
        )
        sql, params = expr.to_sql()
        assert sql == "INSERT IGNORE INTO `probe_bare` (`a`, `b`) VALUES (%s, %s)"
        assert params == (7, "y")

    def test_replace_into_binds_bare_cells(self, mariadb_dialect):
        table = Table(mariadb_dialect, "probe_bare")
        expr = MariaDBInsertExpression(
            mariadb_dialect,
            into=table,
            columns=["a", "b"],
            source=ValuesSource(mariadb_dialect, [[9, "z"]]),
            replace=True,
        )
        sql, params = expr.to_sql()
        assert sql == "REPLACE INTO `probe_bare` (`a`, `b`) VALUES (%s, %s)"
        assert params == (9, "z")

    def test_mixed_row_binds_each_cell_by_kind(self, mariadb_dialect):
        table = Table(mariadb_dialect, "probe_bare")
        expr = InsertStatement(
            mariadb_dialect,
            into=table,
            columns=["a", "b", "c"],
            source=ValuesSource(
                mariadb_dialect,
                [[Literal(mariadb_dialect, 3), "w", Column(mariadb_dialect, "d")]],
            ),
        )
        sql, params = expr.to_sql()
        assert (
            sql == "INSERT INTO `probe_bare` (`a`, `b`, `c`) VALUES (%s, %s, `d`)"
        )
        assert params == (3, "w")

    def test_multiple_rows_keep_cell_order(self, mariadb_dialect):
        table = Table(mariadb_dialect, "probe_bare")
        expr = InsertStatement(
            mariadb_dialect,
            into=table,
            columns=["a"],
            source=ValuesSource(mariadb_dialect, [[1], [2], [3]]),
        )
        sql, params = expr.to_sql()
        assert sql == "INSERT INTO `probe_bare` (`a`) VALUES (%s), (%s), (%s)"
        assert params == (1, 2, 3)
