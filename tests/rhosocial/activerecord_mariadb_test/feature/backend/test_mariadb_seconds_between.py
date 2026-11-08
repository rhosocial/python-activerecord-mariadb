# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_seconds_between.py
"""MariaDB's spelling for the signed seconds between two instants.

``seconds_between`` is a duration, so the cases that matter are the ones a
component sum gets wrong: the sign, the zero, the fraction and the boundaries
where a month or a year changes. MariaDB counts in ``MICROSECOND`` and divides
by ``1000000`` so both the direction and the sub-second part survive.

The render tests pin the spelling, the bind order and the alias; the live tests
run the same expression against each configured server and read the number back.
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    QueryStatement,
    SecondsBetweenExpression,
    seconds_between,
)
from rhosocial.activerecord.backend.expression.column_types import TimestampColumn
from rhosocial.activerecord.backend.expression.value_types import NumericValue
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


DQL_OPTIONS = ExecutionOptions(stmt_type=StatementType.DQL)

RENDERED = (
    "(TIMESTAMPDIFF(MICROSECOND, `started_at`, `ended_at`) / 1000000)"
)


class TestMariaDBSecondsBetweenSpelling:
    """The SQL MariaDB's formatter produces, without a server."""

    def test_columns_render_timestampdiff_microseconds(self, mariadb_dialect):
        expr = seconds_between(
            mariadb_dialect,
            Column(mariadb_dialect, "started_at"),
            Column(mariadb_dialect, "ended_at"),
        )

        sql, params = expr.to_sql()

        assert sql == RENDERED
        assert params == ()

    def test_bind_parameters_follow_sql_order(self, mariadb_dialect):
        expr = seconds_between(
            mariadb_dialect,
            Literal(mariadb_dialect, "2026-01-01 00:00:00"),
            Literal(mariadb_dialect, "2026-01-02 00:00:00"),
        )

        sql, params = expr.to_sql()

        assert sql == "(TIMESTAMPDIFF(MICROSECOND, %s, %s) / 1000000)"
        # ``start`` is written first, so its parameter binds first.
        assert params == ("2026-01-01 00:00:00", "2026-01-02 00:00:00")

    def test_alias_is_applied_after_the_division(self, mariadb_dialect):
        expr = seconds_between(
            mariadb_dialect,
            Column(mariadb_dialect, "started_at"),
            Column(mariadb_dialect, "ended_at"),
        ).as_("elapsed")

        sql, params = expr.to_sql()

        assert sql == f"{RENDERED} AS `elapsed`"
        assert params == ()

    def test_factory_coerces_string_to_column(self, mariadb_dialect):
        expr = seconds_between(mariadb_dialect, "started_at", "ended_at")

        sql, params = expr.to_sql()

        assert sql == RENDERED
        assert params == ()

    def test_column_method(self, mariadb_dialect):
        started = TimestampColumn(mariadb_dialect, "started_at")
        ended = TimestampColumn(mariadb_dialect, "ended_at")

        expr = started.seconds_between(ended)

        sql, params = expr.to_sql()

        assert sql == RENDERED
        assert params == ()

    def test_node_is_a_fractional_number(self, mariadb_dialect):
        expr = seconds_between(
            mariadb_dialect,
            Column(mariadb_dialect, "started_at"),
            Column(mariadb_dialect, "ended_at"),
        )

        assert isinstance(expr, SecondsBetweenExpression)
        assert isinstance(expr, NumericValue)
        assert expr.format_method == "format_seconds_between_expression"

    def test_select_keeps_the_authored_alias(self, mariadb_dialect):
        expr = seconds_between(
            mariadb_dialect,
            Column(mariadb_dialect, "started_at"),
            Column(mariadb_dialect, "ended_at"),
        ).as_("queue_seconds")
        query = QueryStatement(mariadb_dialect, select=[expr])

        sql, params = query.to_sql()

        assert sql == (
            "SELECT (TIMESTAMPDIFF(MICROSECOND, `started_at`, `ended_at`) "
            "/ 1000000) AS `queue_seconds`"
        )
        assert params == ()


def _elapsed(backend, start: str, end: str) -> float:
    """Run ``seconds_between(start, end)`` and return the scalar."""
    dialect = backend.dialect
    expr = seconds_between(dialect, Literal(dialect, start), Literal(dialect, end))
    query = QueryStatement(dialect, select=[expr.as_("seconds")])
    sql, params = query.to_sql()
    result = backend.execute(sql, params, options=DQL_OPTIONS)
    return float(result.data[0]["seconds"])


async def _async_elapsed(backend, start: str, end: str) -> float:
    """Run ``seconds_between(start, end)`` asynchronously and return the scalar."""
    dialect = backend.dialect
    expr = seconds_between(dialect, Literal(dialect, start), Literal(dialect, end))
    query = QueryStatement(dialect, select=[expr.as_("seconds")])
    sql, params = query.to_sql()
    result = await backend.execute(sql, params, options=DQL_OPTIONS)
    return float(result.data[0]["seconds"])


class TestMariaDBSecondsBetweenExecution:
    """The value the MariaDB spelling actually produces."""

    @pytest.mark.parametrize(
        "start,end,expected",
        [
            ("2026-06-04 10:00:00", "2026-06-04 10:00:00", 0.0),
            ("2026-06-04 10:00:00", "2026-06-04 11:00:00", 3600.0),
            ("2026-06-04 11:00:00", "2026-06-04 10:00:00", -3600.0),
            ("2026-01-31 23:59:59", "2026-02-01 00:00:00", 1.0),
            ("2025-12-31 12:00:00", "2026-01-01 12:00:00", 86400.0),
            ("2026-06-04 10:00:00.000", "2026-06-04 10:00:00.500", 0.5),
            ("2026-06-04 10:00:00.250", "2026-06-04 10:00:00.000", -0.25),
        ],
    )
    def test_interval(self, mariadb_backend_single, start: str, end: str, expected: float):
        assert _elapsed(mariadb_backend_single, start, end) == pytest.approx(expected, abs=1e-6)

    def test_columns_in_a_row(self, mariadb_backend_single):
        """The same question asked of two columns, not two literals."""
        table = "mariadb_seconds_between_spans"
        mariadb_backend_single.executescript(
            f"""
            DROP TABLE IF EXISTS {table};
            CREATE TABLE {table} (
                id INT PRIMARY KEY,
                started_at DATETIME(6),
                ended_at DATETIME(6)
            );
            INSERT INTO {table} (id, started_at, ended_at) VALUES
                (1, '2026-03-01 00:00:00', '2026-03-02 00:00:00'),
                (2, '2026-03-02 00:00:00', '2026-03-01 00:00:00'),
                (3, '2026-03-01 00:00:00.750', '2026-03-01 00:00:01.000');
            """
        )

        dialect = mariadb_backend_single.dialect
        expr = seconds_between(
            dialect,
            Column(dialect, "started_at"),
            Column(dialect, "ended_at"),
        )
        query = QueryStatement(
            dialect,
            select=[expr.as_("seconds"), Column(dialect, "id")],
            from_=table,
        )
        sql, params = query.to_sql()

        try:
            result = mariadb_backend_single.execute(sql, params, options=DQL_OPTIONS)
            rows = {row["id"]: float(row["seconds"]) for row in result.data}
            assert rows[1] == pytest.approx(86400.0, abs=1e-6)
            assert rows[2] == pytest.approx(-86400.0, abs=1e-6)
            assert rows[3] == pytest.approx(0.25, abs=1e-6)
        finally:
            mariadb_backend_single.execute(f"DROP TABLE IF EXISTS {table}")


class TestAsyncMariaDBSecondsBetweenExecution:
    """The same values, read through the async backend."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "start,end,expected",
        [
            ("2026-06-04 10:00:00", "2026-06-04 10:00:00", 0.0),
            ("2026-06-04 10:00:00", "2026-06-04 11:00:00", 3600.0),
            ("2026-06-04 11:00:00", "2026-06-04 10:00:00", -3600.0),
            ("2026-01-31 23:59:59", "2026-02-01 00:00:00", 1.0),
            ("2025-12-31 12:00:00", "2026-01-01 12:00:00", 86400.0),
            ("2026-06-04 10:00:00.000", "2026-06-04 10:00:00.500", 0.5),
            ("2026-06-04 10:00:00.250", "2026-06-04 10:00:00.000", -0.25),
        ],
    )
    async def test_interval(
        self, async_mariadb_backend_single, start: str, end: str, expected: float
    ):
        assert await _async_elapsed(
            async_mariadb_backend_single, start, end
        ) == pytest.approx(expected, abs=1e-6)

    @pytest.mark.asyncio
    async def test_columns_in_a_row(self, async_mariadb_backend_single):
        table = "mariadb_seconds_between_spans_async"
        await async_mariadb_backend_single.executescript(
            f"""
            DROP TABLE IF EXISTS {table};
            CREATE TABLE {table} (
                id INT PRIMARY KEY,
                started_at DATETIME(6),
                ended_at DATETIME(6)
            );
            INSERT INTO {table} (id, started_at, ended_at) VALUES
                (1, '2026-03-01 00:00:00', '2026-03-02 00:00:00'),
                (2, '2026-03-02 00:00:00', '2026-03-01 00:00:00'),
                (3, '2026-03-01 00:00:00.750', '2026-03-01 00:00:01.000');
            """
        )

        dialect = async_mariadb_backend_single.dialect
        expr = seconds_between(
            dialect,
            Column(dialect, "started_at"),
            Column(dialect, "ended_at"),
        )
        query = QueryStatement(
            dialect,
            select=[expr.as_("seconds"), Column(dialect, "id")],
            from_=table,
        )
        sql, params = query.to_sql()

        try:
            result = await async_mariadb_backend_single.execute(
                sql, params, options=DQL_OPTIONS
            )
            rows = {row["id"]: float(row["seconds"]) for row in result.data}
            assert rows[1] == pytest.approx(86400.0, abs=1e-6)
            assert rows[2] == pytest.approx(-86400.0, abs=1e-6)
            assert rows[3] == pytest.approx(0.25, abs=1e-6)
        finally:
            await async_mariadb_backend_single.execute(f"DROP TABLE IF EXISTS {table}")
