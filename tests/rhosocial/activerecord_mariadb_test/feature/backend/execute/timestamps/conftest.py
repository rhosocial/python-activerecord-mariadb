# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/timestamps/conftest.py
"""The table this directory reproduces the implicit-TIMESTAMP behaviour with.

Two properties matter, and both are the reason the table is declared this way:

* ``first_ts`` is a bare ``TIMESTAMP`` -- no ``NULL``, no default. That is
  exactly the shape a server with ``explicit_defaults_for_timestamp`` OFF
  decorates with ``DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP``;
  declaring it nullable would suppress the rule and the reproduction would
  prove nothing.
* ``second_ts`` is declared ``NULL`` so the server leaves it alone: only the
  table's **first** TIMESTAMP column takes the implicit behaviour, and the
  contrast is what the test asserts.

The directory exists to reproduce that behaviour, so a server without it has
nothing to reproduce here and skips the whole directory -- the mirror image of
the shared suite, which skips itself on the servers that do have it. That is why
MariaDB 11.8.9 (which reports ON) skips here while 10.2-10.6 do not.
"""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

from datetime import datetime
from types import SimpleNamespace

import pytest

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


DECLARATION = Declaration(
    parallel=True,
    purpose="MariaDB backend tests (timestamps) against the directory-owned database.",
    passes_means="the live-database contract of this directory holds on MariaDB",
    fails_means="the directory-owned database is corrupted or a backend behavior is wrong",
)

_DDL = ExecutionOptions(stmt_type=StatementType.DDL)
_DML = ExecutionOptions(stmt_type=StatementType.DML)

_TABLE = "implicit_first_timestamp"

#: The seed both columns start from; a rewrite is visible as a different value.
_SEED = datetime(2020, 1, 1, 0, 0, 1)


@pytest.fixture
def implicit_timestamp_table(mariadb_backend):
    """Create and seed the reproduction table on a server that needs it."""
    backend = mariadb_backend
    if backend.dialect.explicit_defaults_for_timestamp():
        pytest.skip(
            "explicit_defaults_for_timestamp is ON on this server: it keeps "
            "a bare TIMESTAMP column to what was written, so there is no "
            "implicit rewrite to reproduce"
        )
    backend.execute(f"DROP TABLE IF EXISTS {_TABLE}", (), options=_DDL)
    backend.execute(
        f"CREATE TABLE {_TABLE} ("
        " id INT NOT NULL PRIMARY KEY,"
        " first_ts TIMESTAMP,"
        " second_ts TIMESTAMP NULL)",
        (),
        options=_DDL,
    )
    try:
        backend.execute(
            f"INSERT INTO {_TABLE} (id, first_ts, second_ts) VALUES "
            "(1, '2020-01-01 00:00:01', '2020-01-01 00:00:01')",
            (),
            options=_DML,
        )
        yield SimpleNamespace(
            backend=backend, table=_TABLE, seed=_SEED, dml=_DML
        )
    finally:
        backend.execute(f"DROP TABLE IF EXISTS {_TABLE}", (), options=_DDL)
