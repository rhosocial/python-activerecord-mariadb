# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/timestamps/test_implicit_first_timestamp.py
"""An UPDATE rewrites the table's first TIMESTAMP column and never the second.

This is the behaviour the shared suite cannot tolerate: it assumes an UPDATE
leaves a TIMESTAMP column it does not name alone, which is why the suite skips
itself on a server whose ``explicit_defaults_for_timestamp`` is OFF. The
directory that reproduces the behaviour runs only on those servers (the fixture
skips the others), and it also checks that the dialect's answer is the session's
real value rather than a guess.
"""


def _session_reports_explicit(backend) -> bool:
    """The session's own answer, read directly for comparison."""
    row = backend.execute(
        "SELECT @@SESSION.explicit_defaults_for_timestamp AS v", ()
    ).data[0]
    return str(row["v"]).strip().upper() in ("ON", "1", "TRUE")


def test_update_rewrites_the_first_timestamp_only(implicit_timestamp_table):
    context = implicit_timestamp_table
    backend = context.backend
    assert backend.dialect.explicit_defaults_for_timestamp() is False
    assert backend.dialect.explicit_defaults_for_timestamp() is (
        _session_reports_explicit(backend)
    ), "the dialect must report the session's real value, not a guess"
    # The statement touches the key and neither timestamp column.
    backend.execute(
        f"UPDATE {context.table} SET id = 2 WHERE id = 1", (), options=context.dml
    )
    row = backend.execute(
        f"SELECT first_ts, second_ts FROM {context.table} WHERE id = 2", ()
    ).data[0]
    assert row["second_ts"] == context.seed, (
        "only the first TIMESTAMP column takes the implicit behaviour"
    )
    assert row["first_ts"] != context.seed, (
        "the first TIMESTAMP column is rewritten by the server on any UPDATE"
    )
