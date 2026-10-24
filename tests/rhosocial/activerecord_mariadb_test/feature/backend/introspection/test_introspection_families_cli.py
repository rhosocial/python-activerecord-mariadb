# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_introspection_families_cli.py
"""Tests for the ``sequences`` and ``table-options`` CLI subcommands.

Both are exercised through ``main([...])`` rather than through the handler
directly, so argument parsing, backend construction, dispatch to
``backend.introspector`` and rendering by the output provider are all
covered. JSON output is used because it is machine-checkable.

The async branch is reached with the parser's own ``--async`` flag, and
``main`` already wraps it in ``asyncio.run``; nothing is monkeypatched to
get there.
"""

import json

import pytest

from rhosocial.activerecord.backend.impl.mariadb.__main__ import main, parse_args
from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import (
    INTROSPECT_TYPES,
)
from rhosocial.activerecord.backend.impl.mariadb.mixins.introspection import (
    SEQUENCES_SINCE,
)

from mariadb_live_server import mariadb_server_available

pytestmark = pytest.mark.skipif(
    not mariadb_server_available(),
    reason="No MariaDB server reachable from the configured scenarios",
)

SEQUENCE = "intro_seq"


def _cli_args(backend, *rest, is_async: bool = False) -> list:
    """Build CLI arguments that reach the same server as *backend*."""
    config = backend.config
    args = [
        "introspect",
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


class TestIntrospectTypes:
    """The new families are offered by the parser."""

    def test_new_families_are_registered(self):
        assert "sequences" in INTROSPECT_TYPES
        assert "table-options" in INTROSPECT_TYPES

    def test_families_are_accepted_by_the_parser(self):
        for family in ("sequences", "table-options"):
            args = parse_args(["introspect", family, "--database", "db"])
            assert args.type == family
            assert args.is_async is False


class TestVersionGate:
    """A family this server is too old for is refused by capability.

    The refusal has to come after connecting -- that is the first moment the
    version is known -- and it has to name the capability rather than fall
    back to argparse, which would call a valid family an invalid choice.
    """

    def test_sequences_on_a_server_without_them(self, mariadb_backend, capsys):
        version = tuple(
            (getattr(mariadb_backend, "_version", None) or (0, 0, 0))[:3]
        )
        if version >= SEQUENCES_SINCE:
            pytest.skip(
                "MariaDB {} has sequences; this case is the older server".format(
                    ".".join(str(part) for part in version)
                )
            )

        with pytest.raises(SystemExit) as excinfo:
            main(_cli_args(mariadb_backend, "sequences"))

        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "does not support sequences introspection" in err
        assert "invalid choice" not in err


class TestSequencesCommand:
    """Tests for ``introspect sequences``."""

    def test_lists_all_sequences(self, backend_with_sequence, capsys):
        out = _run(capsys, _cli_args(backend_with_sequence, "sequences"))

        payload = json.loads(out)
        assert payload
        names = {row["name"] for row in payload}
        assert SEQUENCE in names

    def test_reports_one_sequence(self, backend_with_sequence, capsys):
        out = _run(capsys, _cli_args(backend_with_sequence, "sequences", SEQUENCE))

        payload = json.loads(out)
        assert len(payload) == 1
        assert payload[0]["name"] == SEQUENCE
        assert payload[0]["schema"] == backend_with_sequence.config.database

    def test_unknown_sequence_exits_non_zero(self, backend_with_sequence, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(_cli_args(backend_with_sequence, "sequences", "no_such_sequence"))

        assert excinfo.value.code == 1
        assert "not found" in capsys.readouterr().err

    def test_async_lists_all_sequences(
        self, async_backend_with_sequence, capsys
    ):
        out = _run(
            capsys,
            _cli_args(async_backend_with_sequence, "sequences", is_async=True),
        )

        payload = json.loads(out)
        assert SEQUENCE in {row["name"] for row in payload}

    def test_async_reports_one_sequence(
        self, async_backend_with_sequence, capsys
    ):
        out = _run(
            capsys,
            _cli_args(
                async_backend_with_sequence, "sequences", SEQUENCE, is_async=True
            ),
        )

        payload = json.loads(out)
        assert [row["name"] for row in payload] == [SEQUENCE]

    def test_async_unknown_sequence_exits_non_zero(
        self, async_backend_with_sequence, capsys
    ):
        with pytest.raises(SystemExit) as excinfo:
            main(
                _cli_args(
                    async_backend_with_sequence,
                    "sequences",
                    "no_such_sequence",
                    is_async=True,
                )
            )

        assert excinfo.value.code == 1
        assert "not found" in capsys.readouterr().err


class TestTableOptionsCommand:
    """Tests for ``introspect table-options``."""

    def test_lists_all_relations(self, backend_with_tables, capsys):
        out = _run(capsys, _cli_args(backend_with_tables, "table-options"))

        payload = json.loads(out)
        assert payload
        names = {row["name"] for row in payload}
        assert "users" in names

    def test_reports_one_table(self, backend_with_tables, capsys):
        out = _run(capsys, _cli_args(backend_with_tables, "table-options", "users"))

        payload = json.loads(out)
        assert len(payload) == 1
        assert payload[0]["name"] == "users"
        assert payload[0]["engine"] == "InnoDB"

    def test_reports_a_view_without_an_engine(self, backend_with_view, capsys):
        """A view has no engine; the row still answers."""
        out = _run(
            capsys, _cli_args(backend_with_view, "table-options", "user_summary")
        )

        payload = json.loads(out)
        assert len(payload) == 1
        assert payload[0]["name"] == "user_summary"
        assert payload[0]["table_type"] == "VIEW"
        assert payload[0]["engine"] is None

    def test_unknown_table_exits_non_zero(self, backend_with_tables, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(_cli_args(backend_with_tables, "table-options", "no_such_table"))

        assert excinfo.value.code == 1
        assert "not found" in capsys.readouterr().err

    def test_async_reports_one_table(self, async_backend_with_tables, capsys):
        out = _run(
            capsys,
            _cli_args(async_backend_with_tables, "table-options", "users",
                      is_async=True),
        )

        payload = json.loads(out)
        assert [row["name"] for row in payload] == ["users"]
        assert payload[0]["engine"] == "InnoDB"

    def test_async_unknown_table_exits_non_zero(
        self, async_backend_with_tables, capsys
    ):
        with pytest.raises(SystemExit) as excinfo:
            main(
                _cli_args(
                    async_backend_with_tables,
                    "table-options",
                    "no_such_table",
                    is_async=True,
                )
            )

        assert excinfo.value.code == 1
        assert "not found" in capsys.readouterr().err
