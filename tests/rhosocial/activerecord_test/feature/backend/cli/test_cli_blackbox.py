# tests/rhosocial/activerecord_test/feature/backend/cli/test_cli_blackbox.py
"""Black-box CLI tests for the MariaDB backend (live scenario server)."""

import io
import json
from contextlib import redirect_stderr, redirect_stdout

import pytest

from rhosocial.activerecord.backend.impl.mariadb.__main__ import main
from providers.scenarios import get_scenario_raw

import socket
COMMANDS = [
    "info", "query", "introspect", "status",
    "named-expression", "named-procedure", "named-procedure-graph",
    "named-migration", "named-connection",
]


@pytest.fixture(scope="module")
def conn_args():
    backend_cls, config = get_scenario_raw("mariadb_122")
    _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _s.settimeout(2)
    try:
        _s.connect((config.host, int(config.port)))
    except OSError:
        pytest.skip(f"Scenario server unreachable: {config.host}:{config.port}")
    finally:
        _s.close()
    args = [
        "--host", config.host,
        "--port", str(config.port),
        "--database", config.database,
        "--user", config.username,
        "--password", config.password,
    ]
    if getattr(config, "ssl_disabled", False):
        args += ["--ssl", "disabled"]
    return args


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    exc = None
    with redirect_stdout(out), redirect_stderr(err):
        try:
            main(argv)
        except SystemExit as e:
            exc = e
    return out.getvalue(), err.getvalue(), exc


class TestCommandSurface:
    def test_help_lists_all_commands(self):
        out, _, _ = run_cli(["--help"])
        for cmd in COMMANDS:
            assert cmd in out

    def test_missing_command_errors(self):
        _, _, exc = run_cli([])
        assert exc is not None and exc.code == 1


class TestQuery:
    def test_query_json(self, conn_args):
        out, err, exc = run_cli(["query"] + conn_args + ["SELECT 1 AS one", "-o", "json"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert json.loads(out) == [{"one": 1}]

    def test_query_async(self, conn_args):
        out, _, exc = run_cli(["query"] + conn_args + ["SELECT 1 AS one", "-o", "json", "--async"])
        assert exc is None
        assert json.loads(out) == [{"one": 1}]


class TestStatus:
    def test_status(self, conn_args):
        out, err, exc = run_cli(["status"] + conn_args + ["-o", "json"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert json.loads(out)

    def test_status_async(self, conn_args):
        out, err, exc = run_cli(["status"] + conn_args + ["-o", "json", "--async"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert json.loads(out)


class TestIntrospect:
    def test_introspect(self, conn_args):
        out, err, exc = run_cli(["introspect", "tables"] + conn_args + ["-o", "json"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_introspect_async(self, conn_args):
        out, err, exc = run_cli(["introspect", "tables"] + conn_args + ["-o", "json", "--async"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)


class TestInfo:
    def test_info(self):
        out, _, exc = run_cli(["info"])
        assert exc is None
        assert "MariaDB" in out or "mariadb" in out


INTROSPECT_TABLE = "cli_introspect_types"


@pytest.fixture(scope="module")
def introspect_table(conn_args):
    run_cli(["query"] + conn_args + [f"DROP TABLE IF EXISTS {INTROSPECT_TABLE}"])
    run_cli(["query"] + conn_args + [
        f"CREATE TABLE {INTROSPECT_TABLE} (id INT, name VARCHAR(50))"
    ])
    yield INTROSPECT_TABLE
    run_cli(["query"] + conn_args + [f"DROP TABLE IF EXISTS {INTROSPECT_TABLE}"])


class TestIntrospectTypes:
    def test_views(self, conn_args):
        out, err, exc = run_cli(["introspect", "views"] + conn_args + ["-o", "json"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_views_async(self, conn_args):
        out, err, exc = run_cli(["introspect", "views"] + conn_args + ["-o", "json", "--async"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_table(self, conn_args, introspect_table):
        out, err, exc = run_cli(
            ["introspect", "table", introspect_table] + conn_args + ["-o", "json"]
        )
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_table_async(self, conn_args, introspect_table):
        out, err, exc = run_cli(
            ["introspect", "table", introspect_table] + conn_args + ["-o", "json", "--async"]
        )
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_columns(self, conn_args, introspect_table):
        out, err, exc = run_cli(
            ["introspect", "columns", introspect_table] + conn_args + ["-o", "json"]
        )
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_columns_async(self, conn_args, introspect_table):
        out, err, exc = run_cli(
            ["introspect", "columns", introspect_table] + conn_args + ["-o", "json", "--async"]
        )
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_indexes(self, conn_args, introspect_table):
        out, err, exc = run_cli(
            ["introspect", "indexes", introspect_table] + conn_args + ["-o", "json"]
        )
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_indexes_async(self, conn_args, introspect_table):
        out, err, exc = run_cli(
            ["introspect", "indexes", introspect_table] + conn_args + ["-o", "json", "--async"]
        )
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_foreign_keys(self, conn_args, introspect_table):
        out, err, exc = run_cli(
            ["introspect", "foreign-keys", introspect_table] + conn_args + ["-o", "json"]
        )
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_foreign_keys_async(self, conn_args, introspect_table):
        out, err, exc = run_cli(
            ["introspect", "foreign-keys", introspect_table] + conn_args + ["-o", "json", "--async"]
        )
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_triggers(self, conn_args):
        out, err, exc = run_cli(["introspect", "triggers"] + conn_args + ["-o", "json"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_triggers_async(self, conn_args):
        out, err, exc = run_cli(["introspect", "triggers"] + conn_args + ["-o", "json", "--async"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_database(self, conn_args):
        out, err, exc = run_cli(["introspect", "database"] + conn_args + ["-o", "json"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)

    def test_database_async(self, conn_args):
        out, err, exc = run_cli(["introspect", "database"] + conn_args + ["-o", "json", "--async"])
        assert exc is None, f"stderr: {err}\nstdout: {out}"
        assert isinstance(json.loads(out), list)
