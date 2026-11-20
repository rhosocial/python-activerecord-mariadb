# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/cli/test_data_commands_cli.py
"""Live CLI integration tests for ``info``, ``query`` and ``status``.

Every case goes through ``main([...])`` so argument parsing, connection
resolution, backend construction and JSON rendering are all exercised against
a real MariaDB server -- nothing here is mocked. The connection flags come from
the same real fixture the backend tests use, so the CLI reaches the very server
the fixture connected to. Only stdout is captured; JSON keeps the assertions
machine-checkable without pinning exact version strings.
"""

import json
from typing import List

import pytest

from rhosocial.activerecord.backend.impl.mariadb.__main__ import main

from mariadb_live_server import mariadb_server_available

pytestmark = pytest.mark.skipif(
    not mariadb_server_available(),
    reason="No MariaDB server reachable from the configured scenarios",
)


def _cli_args(command, backend, *rest, is_async: bool = False) -> List[str]:
    """Build CLI arguments that reach the same server as *backend*."""
    config = backend.config
    args = [
        command,
        *rest,
        "--host",
        config.host,
        "--port",
        str(config.port),
        "--database",
        config.database,
        "--user",
        config.username,
        "--password",
        config.password or "",
        "--charset",
        config.charset or "utf8mb4",
    ]
    if getattr(config, "ssl_disabled", None):
        args.extend(["--ssl", "disabled"])
    if is_async:
        args.append("--async")
    return args + ["-o", "json"]


def _run(capsys, args) -> str:
    main(args)
    return capsys.readouterr().out


class TestInfoCommand:
    """``info`` connects when given a database and reports the live dialect."""

    def test_info_reports_the_connected_dialect(self, mariadb_backend_single, capsys):
        out = _run(capsys, _cli_args("info", mariadb_backend_single))

        payload = json.loads(out)
        assert isinstance(payload, dict)
        assert payload["database"]["type"] == "mariadb"
        assert payload["database"]["connected"] is True
        version = payload["database"]["version_tuple"]
        assert isinstance(version, list) and len(version) >= 2
        assert all(isinstance(part, int) for part in version)
        assert payload["protocols"]


class TestQueryCommand:
    """``query`` returns the server's answer as a JSON record list."""

    def test_query_select_literal(self, mariadb_backend_single, capsys):
        out = _run(capsys, _cli_args("query", mariadb_backend_single, "SELECT 1 AS n"))

        payload = json.loads(out)
        assert isinstance(payload, list) and len(payload) == 1
        assert "n" in payload[0]
        assert int(payload[0]["n"]) == 1

    def test_query_from_a_sql_file(self, mariadb_backend_single, capsys, tmp_path):
        sql_file = tmp_path / "live_query.sql"
        sql_file.write_text("SELECT 2 AS n", encoding="utf-8")

        out = _run(capsys, _cli_args("query", mariadb_backend_single, "-f", str(sql_file)))

        payload = json.loads(out)
        assert isinstance(payload, list) and len(payload) == 1
        assert int(payload[0]["n"]) == 2

    def test_query_select_literal_async(self, mariadb_backend_single, capsys):
        out = _run(
            capsys,
            _cli_args("query", mariadb_backend_single, "SELECT 3 AS n", is_async=True),
        )

        payload = json.loads(out)
        assert isinstance(payload, list) and len(payload) == 1
        assert int(payload[0]["n"]) == 3


class TestStatusCommand:
    """``status`` reads live server facts, not a canned dialect answer."""

    def test_status_all_returns_an_overview(self, mariadb_backend_single, capsys):
        out = _run(capsys, _cli_args("status", mariadb_backend_single, "all"))

        payload = json.loads(out)
        assert isinstance(payload, dict) and payload
        assert {"server_version", "server_vendor", "configuration"} <= payload.keys()
        assert isinstance(payload["configuration"], list)

    def test_status_config_returns_named_items(self, mariadb_backend_single, capsys):
        out = _run(capsys, _cli_args("status", mariadb_backend_single, "config"))

        payload = json.loads(out)
        assert isinstance(payload, list) and payload
        assert {"name", "value"} <= payload[0].keys()


class TestMoreIntrospectFamilies:
    """Two further catalogue families that are safe on any live server."""

    def test_introspect_tables_lists_a_real_table(self, mariadb_backend_single, capsys):
        backend = mariadb_backend_single
        table = "cli_live_tables_probe"
        backend.execute("CREATE TABLE IF NOT EXISTS {} (id INT PRIMARY KEY)".format(table))
        try:
            out = _run(capsys, _cli_args("introspect", backend, "tables"))
        finally:
            backend.execute("DROP TABLE IF EXISTS {}".format(table))

        payload = json.loads(out)
        assert isinstance(payload, list) and payload
        assert table in {row.get("name") for row in payload if isinstance(row, dict)}

    def test_introspect_database_reports_identity(self, mariadb_backend_single, capsys):
        out = _run(capsys, _cli_args("introspect", mariadb_backend_single, "database"))

        payload = json.loads(out)
        assert isinstance(payload, list) and len(payload) == 1
        assert {"name", "version", "vendor"} <= payload[0].keys()
