# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/cli/test_status_offline.py
"""Offline unit tests for ``mariadb.cli.status``.

Every I/O seam is mocked: no MariaDB server, no driver, no network. The tests
pin the parser surface, the pure serialization/format helpers, rich rendering
through injected fake ``rich`` modules, and both the sync and native-async
dispatch/error paths.
"""

import argparse
import json
import sys
import types
from dataclasses import dataclass
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from rhosocial.activerecord.backend.introspection.status import (
    ConnectionInfo,
    DatabaseBriefInfo,
    SessionInfo,
    StatusCategory,
    StatusItem,
    StorageInfo,
    UserInfo,
)

from rhosocial.activerecord.backend.impl.mariadb.cli import status as mod
from rhosocial.activerecord.backend.impl.mariadb.introspection.status_types import (
    MariaDBBinaryLogInfo,
    MariaDBReplicationInfo,
    MariaDBServerOverview,
)


def _args(**overrides):
    values = dict(
        output="json",
        rich_ascii=False,
        type="all",
        verbose=0,
        database="mydb",
        is_async=False,
        named_connection=None,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


# ---------------------------------------------------------------------------
# create_parser
# ---------------------------------------------------------------------------


class TestCreateParser:
    def test_defaults(self):
        subs = argparse.ArgumentParser(prog="x").add_subparsers(dest="command")
        args = mod.create_parser(subs).parse_args([])
        assert args.type == "all"
        assert args.output == "table"
        assert args.verbose == 0
        assert args.rich_ascii is False

    @pytest.mark.parametrize("status_type", mod.STATUS_TYPES)
    def test_every_status_type_is_accepted(self, status_type):
        subs = argparse.ArgumentParser(prog="x").add_subparsers(dest="command")
        assert mod.create_parser(subs).parse_args([status_type]).type == status_type

    def test_unknown_type_is_rejected(self, capsys):
        subs = argparse.ArgumentParser(prog="x").add_subparsers(dest="command")
        with pytest.raises(SystemExit) as exc:
            mod.create_parser(subs).parse_args(["bogus"])
        assert exc.value.code == 2
        assert "invalid choice" in capsys.readouterr().err

    def test_output_choices_and_flags(self):
        subs = argparse.ArgumentParser(prog="x").add_subparsers(dest="command")
        parser = mod.create_parser(subs)
        assert parser.parse_args(["-o", "csv"]).output == "csv"
        assert parser.parse_args(["--output", "tsv"]).output == "tsv"
        assert parser.parse_args(["--rich-ascii"]).rich_ascii is True
        assert parser.parse_args(["--async"]).is_async is True

    @pytest.mark.parametrize("count,expected", [(1, 1), (2, 2), (4, 4)])
    def test_verbose_is_a_count(self, count, expected):
        subs = argparse.ArgumentParser(prog="x").add_subparsers(dest="command")
        assert mod.create_parser(subs).parse_args(["-" + "v" * count]).verbose == expected


# ---------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------


class _Colour(Enum):
    RED = "red"


@dataclass
class _Point:
    x: int
    y: int


class _WithModelDump:
    def model_dump(self, mode="python"):
        return {"a": 1, "mode": mode}


class TestSerializeForOutput:
    @pytest.mark.parametrize(
        "value,expected", [(None, None), ("x", "x"), (3, 3), (1.5, 1.5), (True, True)]
    )
    def test_none_and_scalars(self, value, expected):
        assert mod._serialize_for_output(value) == expected

    def test_enum_value(self):
        assert mod._serialize_for_output(_Colour.RED) == "red"

    def test_dataclass(self):
        assert mod._serialize_for_output(_Point(1, 2)) == {"x": 1, "y": 2}

    def test_dict_and_list_are_recursive(self):
        obj = {"p": _Point(1, 2), "c": _Colour.RED, "items": [_Colour.RED, 2]}
        assert mod._serialize_for_output(obj) == {
            "p": {"x": 1, "y": 2},
            "c": "red",
            "items": ["red", 2],
        }

    def test_tuple_becomes_list(self):
        assert mod._serialize_for_output((1, 2)) == [1, 2]

    def test_model_dump_json_mode(self):
        assert mod._serialize_for_output(_WithModelDump()) == {"a": 1, "mode": "json"}

    def test_model_dump_typeerror_falls_back_to_plain_call(self):
        class NoMode:
            def model_dump(self):
                return {"ok": True}

        assert mod._serialize_for_output(NoMode()) == {"ok": True}

    def test_unknown_object_falls_back_to_str(self):
        class Plain:
            def __str__(self):
                return "fallback"

        assert mod._serialize_for_output(Plain()) == "fallback"

    def test_dataclass_type_is_not_serialized_as_instance(self):
        assert mod._serialize_for_output(_Point) == str(_Point)


class TestFormatSize:
    @pytest.mark.parametrize(
        "size,expected",
        [
            (0, "0.0 B"),
            (512, "512.0 B"),
            (1023, "1023.0 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024**3, "1.0 GB"),
            (1024**4, "1.0 TB"),
            (1024**5, "1.0 PB"),
        ],
    )
    def test_units(self, size, expected):
        assert mod._format_size(size) == expected


class TestFormatSwitch:
    @pytest.mark.parametrize("value,expected", [(None, "N/A"), (True, "Yes"), (False, "No")])
    def test_none_is_not_off(self, value, expected):
        assert mod._format_switch(value) == expected


# ---------------------------------------------------------------------------
# rich rendering with injected fake modules
# ---------------------------------------------------------------------------


class _FakeTable:
    def __init__(self, *args, **kwargs):
        self.columns = []
        self.rows = []

    def add_column(self, *args, **kwargs):
        self.columns.append(args)

    def add_row(self, *args, **kwargs):
        self.rows.append(args)


class _FakeConsole:
    def __init__(self, printed, **kwargs):
        self.printed = printed

    def print(self, *args, **kwargs):
        self.printed.extend(args)


@pytest.fixture
def fake_rich():
    printed = []
    console_mod = types.ModuleType("rich.console")
    console_mod.Console = lambda **kwargs: _FakeConsole(printed)
    table_mod = types.ModuleType("rich.table")
    table_mod.Table = _FakeTable
    rich_mod = types.ModuleType("rich")
    rich_mod.console = console_mod
    rich_mod.table = table_mod
    with patch.dict(
        sys.modules,
        {"rich": rich_mod, "rich.console": console_mod, "rich.table": table_mod},
    ):
        yield printed


def _rendered(printed):
    out = []
    for item in printed:
        if isinstance(item, _FakeTable):
            for args in item.columns:
                out.extend(str(a) for a in args)
            for args in item.rows:
                out.extend(str(a) for a in args)
        else:
            out.append(str(item))
    return out


def _overview(**overrides):
    values = dict(server_version="11.4.0", server_vendor="MariaDB")
    values.update(overrides)
    return MariaDBServerOverview(**values)


class TestDisplayStatusRich:
    def test_header_and_identity_always_rendered(self, fake_rich):
        mod._display_status_rich(_overview())
        text = " ".join(_rendered(fake_rich))
        assert "MariaDB Server Status" in text
        assert "11.4.0" in text
        assert "MariaDB" in text

    def test_session_fields_rendered(self, fake_rich):
        session = SessionInfo(
            user="alice",
            database="shop",
            host="10.0.0.2",
            ssl_enabled=True,
            ssl_version="TLSv1.3",
            ssl_cipher="AES",
            password_used=True,
        )
        mod._display_status_rich(_overview(session=session))
        text = " ".join(_rendered(fake_rich))
        for expected in ("alice", "shop", "10.0.0.2", "Enabled", "TLSv1.3", "AES", "Password"):
            assert expected in text

    def test_disabled_ssl_and_other_auth_rendered(self, fake_rich):
        session = SessionInfo(ssl_enabled=False, password_used=False)
        mod._display_status_rich(_overview(session=session))
        text = " ".join(_rendered(fake_rich))
        assert "Disabled" in text
        assert "Other" in text

    def test_connections_rendered(self, fake_rich):
        conn = ConnectionInfo(active_count=7, max_connections=100)
        mod._display_status_rich(_overview(connections=conn))
        text = " ".join(_rendered(fake_rich))
        assert "7" in text
        assert "100" in text

    def test_storage_table_shows_human_sizes(self, fake_rich):
        storage = StorageInfo(total_size_bytes=2048, data_size_bytes=1024, index_size_bytes=None)
        mod._display_status_rich(_overview(storage=storage))
        text = " ".join(_rendered(fake_rich))
        assert "Storage" in text
        assert "2.0 KB" in text
        assert "1.0 KB" in text
        assert "N/A" in text

    def test_configuration_section_filters_by_category(self, fake_rich):
        items = [
            StatusItem(
                name="max_connections",
                value=151,
                category=StatusCategory.CONFIGURATION,
                description="desc",
                is_readonly=False,
            ),
            StatusItem(name="queries", value=10, category=StatusCategory.PERFORMANCE),
        ]
        mod._display_status_rich(_overview(configuration=items))
        text = " ".join(_rendered(fake_rich))
        assert "Configuration" in text
        assert "max_connections" in text
        assert "queries" in text

    def test_verbose_configuration_adds_description_and_readonly(self, fake_rich):
        item = StatusItem(name="max_connections", value=151, description="desc", is_readonly=True)
        mod._display_status_rich(_overview(configuration=[item]), verbose=1)
        tables = [x for x in fake_rich if isinstance(x, _FakeTable)]
        config_table = next(t for t in tables if "Parameter" in [a[0] for a in t.columns])
        assert [a[0] for a in config_table.columns] == [
            "Parameter",
            "Value",
            "Description",
            "Readonly",
        ]
        assert config_table.rows[0] == ("max_connections", "151", "desc", "Yes")

    def test_verbose_performance_adds_unit(self, fake_rich):
        item = StatusItem(name="uptime", value=42, category=StatusCategory.PERFORMANCE, unit="s")
        mod._display_status_rich(_overview(configuration=[item]), verbose=1)
        tables = [x for x in fake_rich if isinstance(x, _FakeTable)]
        perf_table = next(t for t in tables if "Unit" in [a[0] for a in t.columns])
        assert perf_table.rows[0] == ("uptime", "42", "s")

    def test_databases_and_users_rendered(self, fake_rich):
        db = DatabaseBriefInfo(name="shop", size_bytes=1024, table_count=3, view_count=1)
        user = UserInfo(name="alice", is_superuser=True)
        mod._display_status_rich(_overview(databases=[db], users=[user]), verbose=1)
        text = " ".join(_rendered(fake_rich))
        for expected in ("Databases", "shop", "1.0 KB", "Users", "alice", "Yes"):
            assert expected in text

    def test_binary_log_renders_unreported_as_na(self, fake_rich):
        overview = _overview(binary_log=MariaDBBinaryLogInfo(log_enabled=None, log_format=None))
        mod._display_status_rich(overview)
        tables = [x for x in fake_rich if isinstance(x, _FakeTable)]
        binlog = next(
            t
            for t in tables
            if "Fact" in [a[0] for a in t.columns] and any(r[0] == "Enabled" for r in t.rows)
        )
        assert ("Enabled", "N/A") in binlog.rows
        assert ("Format", "N/A") in binlog.rows

    def test_binary_log_reported_facts_rendered(self, fake_rich):
        blog = MariaDBBinaryLogInfo(
            log_enabled=True,
            log_format="ROW",
            current_log_file="mysql-bin.0001",
            current_log_position=120,
            executed_gtid_set="0-1-5",
        )
        mod._display_status_rich(_overview(binary_log=blog))
        text = " ".join(_rendered(fake_rich))
        for expected in ("Enabled", "Yes", "ROW", "mysql-bin.0001", "120", "0-1-5"):
            assert expected in text

    def test_replication_non_replica_identity_only(self, fake_rich):
        repl = MariaDBReplicationInfo(server_id=1, is_replica=False)
        mod._display_status_rich(_overview(replication=repl))
        tables = [x for x in fake_rich if isinstance(x, _FakeTable)]
        repl_table = next(t for t in tables if any(r[0] == "Server ID" for r in t.rows))
        rows = repl_table.rows
        assert ("Server ID", "1") in rows
        assert ("Replica", "No") in rows
        assert not any(r[0] in ("IO Thread", "SQL Thread") for r in rows)

    def test_replica_thread_and_master_facts_rendered(self, fake_rich):
        repl = MariaDBReplicationInfo(
            server_id=2,
            is_replica=True,
            slave_io_running="Yes",
            slave_sql_running="No",
            master_host="master.local",
            master_port=3306,
        )
        mod._display_status_rich(_overview(replication=repl))
        text = " ".join(_rendered(fake_rich))
        for expected in ("Yes", "No", "master.local:3306", "IO Thread", "SQL Thread"):
            assert expected in text


# ---------------------------------------------------------------------------
# _handle_status_sync
# ---------------------------------------------------------------------------


def _sync_backend(status_introspector, connected=True):
    backend = MagicMock()
    backend._connection = connected
    backend.introspector.status = status_introspector
    return backend


class TestHandleStatusSync:
    @pytest.mark.parametrize(
        "status_type,method,value,expected,title",
        [
            ("config", "list_configuration", [1, 2], [1, 2], "Configuration"),
            ("performance", "list_performance_metrics", [3], [3], "Performance"),
            ("connections", "get_connection_info", {"a": 1}, [{"a": 1}], "Connections"),
            ("storage", "get_storage_info", {"b": 2}, [{"b": 2}], "Storage"),
            ("databases", "list_databases", [{"c": 3}], [{"c": 3}], "Databases"),
            ("users", "list_users", [{"d": 4}], [{"d": 4}], "Users"),
            ("binlog", "get_binary_log_info", {"e": 5}, [{"e": 5}], "Binary Log"),
            ("replication", "get_replication_info", {"f": 6}, [{"f": 6}], "Replication"),
        ],
    )
    def test_each_type_calls_its_method_and_displays(
        self, status_type, method, value, expected, title
    ):
        introspector = MagicMock()
        getattr(introspector, method).return_value = value
        backend = _sync_backend(introspector)
        provider = MagicMock()

        mod._handle_status_sync(_args(type=status_type), backend, provider)

        backend.connect.assert_called_once_with()
        backend.introspect_and_adapt.assert_called_once_with()
        getattr(introspector, method).assert_called_once()
        provider.display_results.assert_called_once_with(expected, title=title)

    def test_configuration_passes_the_category(self):
        introspector = MagicMock()
        introspector.list_configuration.return_value = []
        provider = MagicMock()
        mod._handle_status_sync(_args(type="config"), _sync_backend(introspector), provider)
        introspector.list_configuration.assert_called_once_with(StatusCategory.CONFIGURATION)

    def test_all_prints_overview_as_json(self, capsys):
        introspector = MagicMock()
        introspector.get_overview.return_value = {"server_version": "11.4"}
        mod._handle_status_sync(
            _args(type="all", output="json"), _sync_backend(introspector), MagicMock()
        )
        assert json.loads(capsys.readouterr().out) == {"server_version": "11.4"}

    @pytest.mark.parametrize("output", ["csv", "tsv"])
    def test_all_falls_back_to_json_for_tabular_formats(self, output, capsys):
        introspector = MagicMock()
        introspector.get_overview.return_value = {"k": "v"}
        mod._handle_status_sync(
            _args(type="all", output=output), _sync_backend(introspector), MagicMock()
        )
        assert json.loads(capsys.readouterr().out) == {"k": "v"}

    def test_all_uses_rich_display_when_available(self):
        introspector = MagicMock()
        introspector.get_overview.return_value = {"k": "v"}
        args = _args(type="all", output="table", verbose=2)
        with patch.object(mod, "RICH_AVAILABLE", True), patch.object(
            mod, "_display_status_rich"
        ) as display:
            mod._handle_status_sync(args, _sync_backend(introspector), MagicMock())
        display.assert_called_once_with({"k": "v"}, 2)

    def test_connection_error_exits_via_provider(self, capsys):
        introspector = MagicMock()
        introspector.get_overview.side_effect = ConnectionError("no server")
        backend = _sync_backend(introspector)
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            mod._handle_status_sync(_args(), backend, provider)
        assert exc.value.code == 1
        provider.display_connection_error.assert_called_once()
        assert isinstance(provider.display_connection_error.call_args[0][0], ConnectionError)

    def test_query_error_exits_via_provider(self):
        introspector = MagicMock()
        introspector.list_users.side_effect = QueryError("bad query")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            mod._handle_status_sync(_args(type="users"), _sync_backend(introspector), provider)
        assert exc.value.code == 1
        provider.display_query_error.assert_called_once()

    def test_unexpected_error_exits_with_message(self, capsys):
        introspector = MagicMock()
        introspector.get_overview.side_effect = RuntimeError("bang")
        with pytest.raises(SystemExit) as exc:
            mod._handle_status_sync(_args(), _sync_backend(introspector), MagicMock())
        assert exc.value.code == 1
        assert "Error during status retrieval: bang" in capsys.readouterr().err

    def test_disconnects_when_connection_is_open(self):
        introspector = MagicMock()
        introspector.list_databases.return_value = []
        backend = _sync_backend(introspector, connected=True)
        mod._handle_status_sync(_args(type="databases"), backend, MagicMock())
        backend.disconnect.assert_called_once_with()

    def test_does_not_disconnect_without_connection(self):
        introspector = MagicMock()
        introspector.list_databases.return_value = []
        backend = _sync_backend(introspector, connected=False)
        mod._handle_status_sync(_args(type="databases"), backend, MagicMock())
        backend.disconnect.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_status_async (native async driver)
# ---------------------------------------------------------------------------


def _async_status_introspector(**overrides):
    names = (
        "get_overview",
        "list_configuration",
        "list_performance_metrics",
        "get_connection_info",
        "get_storage_info",
        "list_databases",
        "list_users",
        "get_binary_log_info",
        "get_replication_info",
    )
    introspector = MagicMock()
    for name in names:
        setattr(introspector, name, AsyncMock(return_value=overrides.get(name, [])))
    return introspector


def _async_backend(status_introspector, connected=True):
    backend = MagicMock()
    backend._connection = connected
    backend.connect = AsyncMock()
    backend.introspect_and_adapt = AsyncMock()
    backend.disconnect = AsyncMock()
    backend.introspector.status = status_introspector
    return backend


class TestHandleStatusAsync:
    @pytest.mark.parametrize(
        "status_type,method,expected,title",
        [
            ("config", "list_configuration", [], "Configuration"),
            ("users", "list_users", [], "Users"),
            ("replication", "get_replication_info", [[]], "Replication"),
        ],
    )
    async def test_async_dispatch_awaits_and_displays(self, status_type, method, expected, title):
        introspector = _async_status_introspector()
        backend = _async_backend(introspector)
        provider = MagicMock()

        await mod._handle_status_async(_args(type=status_type), backend, provider)

        backend.connect.assert_awaited_once_with()
        backend.introspect_and_adapt.assert_awaited_once_with()
        getattr(introspector, method).assert_awaited_once()
        provider.display_results.assert_called_once()
        assert provider.display_results.call_args.kwargs["title"] == title

    async def test_all_prints_overview_as_json(self, capsys):
        introspector = _async_status_introspector(get_overview={"server_version": "11.8"})
        await mod._handle_status_async(_args(type="all"), _async_backend(introspector), MagicMock())
        assert json.loads(capsys.readouterr().out) == {"server_version": "11.8"}

    async def test_connection_error_exits_via_provider(self):
        introspector = _async_status_introspector()
        introspector.get_overview.side_effect = ConnectionError("no server")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            await mod._handle_status_async(_args(), _async_backend(introspector), provider)
        assert exc.value.code == 1
        provider.display_connection_error.assert_called_once()

    async def test_query_error_exits_via_provider(self):
        introspector = _async_status_introspector()
        introspector.list_users.side_effect = QueryError("bad query")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            await mod._handle_status_async(
                _args(type="users"), _async_backend(introspector), provider
            )
        assert exc.value.code == 1
        provider.display_query_error.assert_called_once()

    async def test_disconnect_is_awaited_only_when_connected(self):
        introspector = _async_status_introspector()
        backend = _async_backend(introspector, connected=True)
        await mod._handle_status_async(_args(type="databases"), backend, MagicMock())
        backend.disconnect.assert_awaited_once_with()

        backend = _async_backend(introspector, connected=False)
        await mod._handle_status_async(_args(type="databases"), backend, MagicMock())
        backend.disconnect.assert_not_awaited()


# ---------------------------------------------------------------------------
# handle: top-level dispatch
# ---------------------------------------------------------------------------


class TestHandle:
    def test_missing_database_is_rejected(self, capsys):
        with patch.object(mod, "create_provider", return_value=MagicMock()):
            with pytest.raises(SystemExit) as exc:
                mod.handle(_args(database=None))
        assert exc.value.code == 1
        assert "--database is required" in capsys.readouterr().err

    def test_named_connection_bypasses_database_guard(self):
        args = _args(database=None, named_connection="app.conn.prod")
        config = object()
        with patch.object(mod, "create_provider") as provider_factory, patch.object(
            mod, "resolve_connection_config_from_args", return_value=config
        ) as resolve, patch.object(mod, "MariaDBBackend") as backend_cls, patch.object(
            mod, "_handle_status_sync"
        ) as sync:
            mod.handle(args)
        provider_factory.assert_called_once_with("json", ascii_borders=False)
        resolve.assert_called_once_with(args)
        backend_cls.assert_called_once_with(connection_config=config)
        sync.assert_called_once()

    def test_sync_backend_is_constructed_and_dispatched(self):
        args = _args(output="table", rich_ascii=True)
        config = object()
        with patch.object(mod, "create_provider"), patch.object(
            mod, "resolve_connection_config_from_args", return_value=config
        ), patch.object(mod, "MariaDBBackend") as backend_cls, patch.object(
            mod, "_handle_status_sync"
        ) as sync:
            mod.handle(args)
        backend_cls.assert_called_once_with(connection_config=config)
        sync.assert_called_once()

    def test_async_backend_is_constructed_and_run_via_asyncio(self):
        args = _args(is_async=True)
        config = object()
        with patch.object(mod, "create_provider"), patch.object(
            mod, "resolve_connection_config_from_args", return_value=config
        ), patch.object(mod, "AsyncMariaDBBackend") as backend_cls, patch.object(
            mod.asyncio, "run"
        ) as run, patch.object(
            mod, "_handle_status_async", new=MagicMock()
        ) as coro:
            mod.handle(args)
        backend_cls.assert_called_once_with(connection_config=config)
        run.assert_called_once()
        coro.assert_called_once()
