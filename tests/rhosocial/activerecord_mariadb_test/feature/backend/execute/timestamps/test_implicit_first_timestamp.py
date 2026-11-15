# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/timestamps/test_implicit_first_timestamp.py
"""What MariaDB does to the table's first TIMESTAMP column, measured.

``explicit_defaults_for_timestamp`` decides the shape of a declared TIMESTAMP
column: with it OFF the table's **first** TIMESTAMP column carries an implicit
``DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP``, so any UPDATE rewrites
it with the server's clock -- including an UPDATE that never mentions it. The
setting belongs to the server and its operator; the framework does not change
it, so the test states which setting is in force and asserts the behaviour that
follows.

MariaDB 11.8.9 reports ``ON``; ``feature/basic/crud`` asserts the explicit
behaviour ("a field an UPDATE never names keeps its value"), which is why this
repository's root conftest skips that directory on a server that answers OFF.
"""

from datetime import datetime

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

DDL = ExecutionOptions(stmt_type=StatementType.DDL)
DML = ExecutionOptions(stmt_type=StatementType.DML)

SEED = datetime(2020, 1, 1, 0, 0, 1)

TABLE = "implicit_first_timestamp"


def _create(backend) -> None:
    backend.execute(f"DROP TABLE IF EXISTS {TABLE}", (), options=DDL)
    # ``first_ts`` is declared the way the suite declares its timestamps: bare,
    # with no NULL and no default. That is exactly the shape an implicit-default
    # server decorates; declaring NULL would suppress the automatic
    # DEFAULT / ON UPDATE and the measurement would prove nothing.
    backend.execute(
        f"CREATE TABLE {TABLE} ("
        " id INT NOT NULL PRIMARY KEY,"
        " first_ts TIMESTAMP,"
        " second_ts TIMESTAMP NULL)",
        (),
        options=DDL,
    )


def _drop(backend) -> None:
    backend.execute(f"DROP TABLE IF EXISTS {TABLE}", (), options=DDL)


def _dialect_says_explicit(backend) -> bool:
    """The dialect's answer, recorded from the session during adaptation."""
    return backend.dialect.explicit_defaults_for_timestamp()


def _session_reports_explicit(backend) -> bool:
    """The session's own answer, read directly for comparison."""
    row = backend.execute(
        "SELECT @@SESSION.explicit_defaults_for_timestamp AS v", ()
    ).data[0]
    return str(row["v"]).strip().upper() in ("ON", "1", "TRUE")


def test_update_rewrites_the_first_timestamp_only_when_defaults_are_implicit(
    mariadb_backend,
):
    explicit = _dialect_says_explicit(mariadb_backend)
    assert explicit is _session_reports_explicit(mariadb_backend), (
        "the dialect must report the session's real value, not a guess from "
        "the version"
    )
    _create(mariadb_backend)
    try:
        mariadb_backend.execute(
            f"INSERT INTO {TABLE} (id, first_ts, second_ts) VALUES "
            f"(1, '2020-01-01 00:00:01', '2020-01-01 00:00:01')",
            (),
            options=DML,
        )
        # The statement touches the key and neither timestamp column.
        mariadb_backend.execute(
            f"UPDATE {TABLE} SET id = 2 WHERE id = 1", (), options=DML
        )
        row = mariadb_backend.execute(
            f"SELECT first_ts, second_ts FROM {TABLE} WHERE id = 2", ()
        ).data[0]
        assert row["second_ts"] == SEED, (
            "only the first TIMESTAMP column takes the implicit behaviour"
        )
        if explicit:
            assert row["first_ts"] == SEED, (
                "explicit_defaults_for_timestamp is ON: an UPDATE leaves a "
                "column it never names alone"
            )
        else:
            assert row["first_ts"] != SEED, (
                "explicit_defaults_for_timestamp is OFF: the first TIMESTAMP "
                "column is rewritten by the server on any UPDATE"
            )
    finally:
        _drop(mariadb_backend)
