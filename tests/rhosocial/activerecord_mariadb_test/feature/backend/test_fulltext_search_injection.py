# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_fulltext_search_injection.py
"""
Regression tests for parameterization in the match_against() factory.

Why this file exists
--------------------
``functions.match_against()`` used to build the ``MATCH ... AGAINST`` clause by
interpolating ``search_string`` into an f-string and returning the result as a
``RawSQLExpression`` with no bound parameters::

    against_arg = f"'{search_string}'"
    sql = f"MATCH ({match_args}) AGAINST({against_arg})"

A quote in the input therefore escaped the literal and reached the driver verbatim.
The correct implementation was not missing: ``MariaDBMatchAgainstExpression`` and
the dialect's ``format_match_against`` already existed, already bound the search
string through the dialect placeholder, and were already covered by
``test_fulltext_index.py`` and the protocol-conformance assertion. Only this entry
point bypassed them, and because **no test called the factory**, the divergence
went unnoticed.

These tests pin the factory to the parameterized path so it cannot regress to
hand-assembled SQL again.
"""

import pytest

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBMatchAgainstExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.functions.fulltext import match_against

# Payloads that all escape a naive f"'{search_string}'" literal.
INJECTION_PAYLOADS = [
    "' OR '1'='1",
    '" OR ""="',
    "'; DROP TABLE users; --",
    "' UNION SELECT password FROM credentials -- ",
    "\\' OR 1=1 -- ",
]


def _dialect() -> MariaDBDialect:
    return MariaDBDialect(version=(10, 6, 0))


class TestMatchAgainstParameterization:
    """The search string must be bound, never interpolated."""

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_search_string_not_in_sql_text(self, payload):
        """Injection payloads must not survive into the rendered SQL."""
        sql, params = match_against(_dialect(), "content", payload).to_sql()

        assert payload not in sql
        assert params == (payload,)

    def test_normal_search_string_is_bound(self):
        """An ordinary term is still bound, not inlined."""
        sql, params = match_against(_dialect(), "content", "search term").to_sql()

        assert "search term" not in sql
        assert params == ("search term",)

    @pytest.mark.parametrize(
        "mode", [None, "NATURAL_LANGUAGE", "BOOLEAN", "QUERY_EXPANSION"]
    )
    def test_every_mode_binds_the_search_string(self, mode):
        """Every mode must emit a placeholder and carry the parameter.

        The placeholder spelling is the dialect's business, so this asserts that
        exactly one bind marker appears rather than hard-coding ``?`` or ``%s``.
        """
        sql, params = match_against(_dialect(), "title", "term", mode=mode).to_sql()

        assert params == ("term",)
        assert "term" not in sql
        assert "AGAINST" in sql

    def test_columns_are_quoted_by_the_dialect(self):
        """Column identifiers go through the dialect's own quoting."""
        sql, _ = match_against(_dialect(), ["title", "content"], "x").to_sql()

        assert "`title`" in sql
        assert "`content`" in sql

    def test_single_column_string_is_normalized_to_list(self):
        """A bare string column name is accepted for symmetry with the list form."""
        single = match_against(_dialect(), "title", "x").to_sql()
        listed = match_against(_dialect(), ["title"], "x").to_sql()

        assert single == listed


class TestMatchAgainstRouting:
    """The factory must delegate to the expression, not format SQL itself."""

    def test_factory_returns_the_expression_type(self):
        """The factory returns MariaDBMatchAgainstExpression directly."""
        expr = match_against(_dialect(), "content", "x")

        assert isinstance(expr, MariaDBMatchAgainstExpression)

    def test_factory_does_not_return_raw_sql(self):
        """The raw-SQL escape hatch must not reappear on this path.

        Guarding the concrete type is deliberate: a regression to
        ``RawSQLExpression`` would render valid SQL and pass a naive
        "does it look right" test, so this asserts the routing itself.
        """
        from rhosocial.activerecord.backend.expression.operators import (
            RawSQLExpression,
        )

        assert not isinstance(
            match_against(_dialect(), "content", "x"), RawSQLExpression
        )

    def test_factory_output_matches_direct_construction(self):
        """The factory adds no behaviour beyond normalizing the column argument.

        This is the strongest available check that the factory is now a thin
        adapter: for the same arguments it must render identically to building the
        expression by hand.
        """
        dialect = _dialect()

        via_factory = match_against(dialect, ["title"], "term", mode="BOOLEAN").to_sql()
        direct = MariaDBMatchAgainstExpression(
            dialect, columns=["title"], search_string="term", mode="BOOLEAN"
        ).to_sql()

        assert via_factory == direct