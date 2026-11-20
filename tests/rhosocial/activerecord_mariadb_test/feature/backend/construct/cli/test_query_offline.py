# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/cli/test_query_offline.py
"""Offline unit tests for ``mariadb.cli.query``.

No database and no network are involved: backends, output providers, ``open``
and ``sys.stdin`` are all mocked. Both the sync and the native-async execution
paths are exercised, including every error-to-``SystemExit`` conversion.
"""

import argparse
import sys
import types
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError

from rhosocial.activerecord.backend.impl.mariadb.cli import query as mod
from rhosocial.activerecord.backend.impl.mariadb.cli.output import OUTPUT_CHOICES


def _args(**overrides):
    values = dict(
        sql="SELECT 1",
        file=None,
        output="json",
        rich_ascii=False,
        log_level="INFO",
        database="mydb",
        is_async=False,
        named_connection=None,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def _result(affected_rows=2, duration=0.25, data=None):
    return types.SimpleNamespace(
        affected_rows=affected_rows,
        duration=duration,
        data=[{"id": 1}] if data is None else data,
    )


def _sync_backend(result=None, connected=True):
    backend = MagicMock()
    backend._connection = connected
    backend.execute.return_value = result
    return backend


def _async_backend(result=None, connected=True):
    backend = MagicMock()
    backend._connection = connected
    backend.connect = AsyncMock()
    backend.execute = AsyncMock(return_value=result)
    backend.disconnect = AsyncMock()
    return backend


# ---------------------------------------------------------------------------
# create_parser
# ---------------------------------------------------------------------------


class TestCreateParser:
    def test_defaults(self):
        subs = argparse.ArgumentParser(prog="x").add_subparsers(dest="command")
        args = mod.create_parser(subs).parse_args([])
        assert args.sql is None
        assert args.file is None
        assert args.output == "table"
        assert args.log_level == "INFO"
        assert args.rich_ascii is False
        assert args.is_async is False

    def test_positional_sql_and_file(self):
        subs = argparse.ArgumentParser(prog="x").add_subparsers(dest="command")
        parser = mod.create_parser(subs)
        assert parser.parse_args(["SELECT 1"]).sql == "SELECT 1"
        assert parser.parse_args(["-f", "q.sql"]).file == "q.sql"
        assert parser.parse_args(["--file", "q.sql"]).file == "q.sql"
        assert parser.parse_args(["-f", "q.sql"]).sql is None

    @pytest.mark.parametrize("output", OUTPUT_CHOICES)
    def test_output_choices(self, output):
        subs = argparse.ArgumentParser(prog="x").add_subparsers(dest="command")
        assert mod.create_parser(subs).parse_args(["-o", output]).output == output

    def test_flags_and_log_level(self):
        subs = argparse.ArgumentParser(prog="x").add_subparsers(dest="command")
        args = mod.create_parser(subs).parse_args(
            ["--async", "--rich-ascii", "--log-level", "DEBUG", "SELECT 2"]
        )
        assert args.is_async is True
        assert args.rich_ascii is True
        assert args.log_level == "DEBUG"


# ---------------------------------------------------------------------------
# handle: argument validation and SQL source
# ---------------------------------------------------------------------------


class TestHandleValidation:
    @pytest.mark.parametrize("level", ["NOPE", "verbose", ""])
    def test_invalid_log_level_raises_value_error(self, level):
        with pytest.raises(ValueError, match="Invalid log level"):
            mod.handle(_args(log_level=level))

    def test_no_sql_anywhere_exits(self, capsys):
        args = _args(sql=None)
        tty_stdin = MagicMock()
        tty_stdin.isatty.return_value = True
        with patch.object(mod, "create_provider", return_value=MagicMock()), patch.object(
            mod.logging, "basicConfig"
        ), patch.object(sys, "stdin", tty_stdin):
            with pytest.raises(SystemExit) as exc:
                mod.handle(args)
        assert exc.value.code == 1
        assert "No SQL query provided" in capsys.readouterr().err

    def test_multiple_statements_are_rejected(self, caplog):
        args = _args(sql="SELECT 1; SELECT 2")
        with patch.object(mod, "create_provider", return_value=MagicMock()), patch.object(
            mod.logging, "basicConfig"
        ):
            with pytest.raises(SystemExit) as exc:
                mod.handle(args)
        assert exc.value.code == 1
        assert "Multiple SQL statements" in caplog.text

    def test_single_trailing_semicolon_is_accepted(self):
        args = _args(sql="SELECT 1;")
        with patch.object(mod, "create_provider", return_value=MagicMock()), patch.object(
            mod.logging, "basicConfig"
        ), patch.object(
            mod, "resolve_connection_config_from_args", return_value=object()
        ), patch.object(
            mod, "MariaDBBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ) as execute:
            mod.handle(args)
        execute.assert_called_once()

    def test_missing_file_exits(self, caplog):
        args = _args(sql=None, file="missing.sql")
        with patch.object(mod, "create_provider", return_value=MagicMock()), patch.object(
            mod.logging, "basicConfig"
        ), patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(SystemExit) as exc:
                mod.handle(args)
        assert exc.value.code == 1
        assert "File not found" in caplog.text

    def test_sql_is_read_from_file(self):
        args = _args(sql=None, file="query.sql")
        with patch.object(mod, "create_provider", return_value=MagicMock()), patch.object(
            mod.logging, "basicConfig"
        ), patch.object(
            mod, "resolve_connection_config_from_args", return_value=object()
        ), patch.object(
            mod, "MariaDBBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ) as execute, patch(
            "builtins.open", mock_open(read_data="SELECT 42")
        ) as opened:
            mod.handle(args)
        opened.assert_called_once_with("query.sql", "r", encoding="utf-8")
        assert execute.call_args[0][0] == "SELECT 42"

    def test_sql_is_read_from_stdin_when_not_a_tty(self):
        args = _args(sql=None)
        stdin = MagicMock()
        stdin.isatty.return_value = False
        stdin.read.return_value = "SELECT 7"
        with patch.object(mod, "create_provider", return_value=MagicMock()), patch.object(
            mod.logging, "basicConfig"
        ), patch.object(
            mod, "resolve_connection_config_from_args", return_value=object()
        ), patch.object(
            mod, "MariaDBBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ) as execute, patch.object(
            sys, "stdin", stdin
        ):
            mod.handle(args)
        assert execute.call_args[0][0] == "SELECT 7"

    def test_greeting_is_displayed(self):
        provider = MagicMock()
        with patch.object(mod, "create_provider", return_value=provider), patch.object(
            mod.logging, "basicConfig"
        ), patch.object(
            mod, "resolve_connection_config_from_args", return_value=object()
        ), patch.object(
            mod, "MariaDBBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ):
            mod.handle(_args())
        provider.display_greeting.assert_called_once_with()


@pytest.fixture
def fake_output_rich():
    """Inject fake ``output_rich``/``rich`` modules for the logging branches."""
    output_rich = types.ModuleType("rhosocial.activerecord.backend.output_rich")

    class RichOutputProvider:
        def __init__(self):
            self.display_greeting = MagicMock()

    output_rich.RichOutputProvider = RichOutputProvider
    console_mod = types.ModuleType("rich.console")

    class Console:
        def __init__(self, *args, **kwargs):
            pass

    console_mod.Console = Console
    logging_mod = types.ModuleType("rich.logging")

    class RichHandler:
        def __init__(self, *args, **kwargs):
            pass

    logging_mod.RichHandler = RichHandler
    rich_mod = types.ModuleType("rich")
    rich_mod.console = console_mod
    rich_mod.logging = logging_mod
    with patch.dict(
        sys.modules,
        {
            "rhosocial.activerecord.backend.output_rich": output_rich,
            "rich": rich_mod,
            "rich.console": console_mod,
            "rich.logging": logging_mod,
        },
    ):
        yield RichOutputProvider


class TestHandleLoggingBranches:
    def test_plain_provider_uses_basic_formatter(self):
        with patch.object(mod, "create_provider", return_value=MagicMock()), patch.object(
            mod, "RICH_AVAILABLE", False
        ), patch.object(mod.logging, "basicConfig") as basic, patch.object(
            mod, "resolve_connection_config_from_args", return_value=object()
        ), patch.object(
            mod, "MariaDBBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ):
            mod.handle(_args(log_level="DEBUG"))
        basic.assert_called_once()
        assert basic.call_args.kwargs["level"] == 10
        assert "%(asctime)s" in basic.call_args.kwargs["format"]

    def test_rich_provider_uses_rich_handler(self, fake_output_rich):
        provider = fake_output_rich()
        with patch.object(mod, "create_provider", return_value=provider), patch.object(
            mod, "RICH_AVAILABLE", True
        ), patch.object(mod.logging, "basicConfig") as basic, patch.object(
            mod, "resolve_connection_config_from_args", return_value=object()
        ), patch.object(
            mod, "MariaDBBackend"
        ), patch.object(
            mod, "_execute_query_sync"
        ):
            mod.handle(_args())
        basic.assert_called_once()
        assert "%(message)s" in basic.call_args.kwargs["format"]
        assert len(basic.call_args.kwargs["handlers"]) == 1


# ---------------------------------------------------------------------------
# _execute_query_sync
# ---------------------------------------------------------------------------


class TestExecuteQuerySync:
    def test_success_with_data_displays_everything(self):
        backend = _sync_backend(_result())
        provider = MagicMock()
        mod._execute_query_sync("SELECT 1", backend, provider, use_ascii=True)
        provider.display_query.assert_called_once_with("SELECT 1", is_async=False)
        provider.display_success.assert_called_once_with(2, 0.25)
        provider.display_results.assert_called_once_with([{"id": 1}], use_ascii=True)
        provider.display_no_data.assert_not_called()

    def test_success_without_data(self):
        backend = _sync_backend(_result(data=[]))
        provider = MagicMock()
        mod._execute_query_sync("SELECT 1", backend, provider)
        provider.display_no_data.assert_called_once_with()
        provider.display_results.assert_not_called()

    def test_falsy_result_reports_no_result_object(self):
        backend = _sync_backend(None)
        provider = MagicMock()
        mod._execute_query_sync("SELECT 1", backend, provider)
        provider.display_no_result_object.assert_called_once_with()
        provider.display_success.assert_not_called()

    def test_connection_error_exits_via_provider(self):
        backend = _sync_backend()
        backend.execute.side_effect = ConnectionError("offline")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            mod._execute_query_sync("SELECT 1", backend, provider)
        assert exc.value.code == 1
        provider.display_connection_error.assert_called_once()

    def test_query_error_exits_via_provider(self):
        backend = _sync_backend()
        backend.execute.side_effect = QueryError("bad sql")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            mod._execute_query_sync("SELECT 1", backend, provider)
        assert exc.value.code == 1
        provider.display_query_error.assert_called_once()

    def test_unexpected_error_exits_via_provider(self):
        backend = _sync_backend()
        backend.execute.side_effect = RuntimeError("boom")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            mod._execute_query_sync("SELECT 1", backend, provider)
        assert exc.value.code == 1
        provider.display_unexpected_error.assert_called_once()
        assert provider.display_unexpected_error.call_args.kwargs["is_async"] is False

    def test_disconnect_and_disconnect_message_in_finally(self):
        backend = _sync_backend(_result(), connected=True)
        provider = MagicMock()
        mod._execute_query_sync("SELECT 1", backend, provider)
        backend.disconnect.assert_called_once_with()
        provider.display_disconnect.assert_called_once_with(is_async=False)

    def test_no_disconnect_without_connection(self):
        backend = _sync_backend(_result(), connected=False)
        mod._execute_query_sync("SELECT 1", backend, MagicMock())
        backend.disconnect.assert_not_called()


# ---------------------------------------------------------------------------
# _execute_query_async (native async driver)
# ---------------------------------------------------------------------------


class TestExecuteQueryAsync:
    async def test_success_with_data_displays_everything(self):
        backend = _async_backend(_result())
        provider = MagicMock()
        await mod._execute_query_async("SELECT 1", backend, provider, use_ascii=False)
        backend.execute.assert_awaited_once_with("SELECT 1")
        provider.display_query.assert_called_once_with("SELECT 1", is_async=True)
        provider.display_success.assert_called_once_with(2, 0.25)
        provider.display_results.assert_called_once_with([{"id": 1}], use_ascii=False)

    async def test_success_without_data(self):
        backend = _async_backend(_result(data=[]))
        provider = MagicMock()
        await mod._execute_query_async("SELECT 1", backend, provider)
        provider.display_no_data.assert_called_once_with()
        provider.display_results.assert_not_called()

    async def test_falsy_result_reports_no_result_object(self):
        backend = _async_backend(None)
        provider = MagicMock()
        await mod._execute_query_async("SELECT 1", backend, provider)
        provider.display_no_result_object.assert_called_once_with()

    async def test_connection_error_exits_via_provider(self):
        backend = _async_backend()
        backend.execute.side_effect = ConnectionError("offline")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            await mod._execute_query_async("SELECT 1", backend, provider)
        assert exc.value.code == 1
        provider.display_connection_error.assert_called_once()

    async def test_query_error_exits_via_provider(self):
        backend = _async_backend()
        backend.execute.side_effect = QueryError("bad sql")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            await mod._execute_query_async("SELECT 1", backend, provider)
        assert exc.value.code == 1
        provider.display_query_error.assert_called_once()

    async def test_unexpected_error_is_tagged_async(self):
        backend = _async_backend()
        backend.execute.side_effect = RuntimeError("boom")
        provider = MagicMock()
        with pytest.raises(SystemExit) as exc:
            await mod._execute_query_async("SELECT 1", backend, provider)
        assert exc.value.code == 1
        assert provider.display_unexpected_error.call_args.kwargs["is_async"] is True

    async def test_disconnect_is_awaited_in_finally(self):
        backend = _async_backend(_result(), connected=True)
        provider = MagicMock()
        await mod._execute_query_async("SELECT 1", backend, provider)
        backend.disconnect.assert_awaited_once_with()
        provider.display_disconnect.assert_called_once_with(is_async=True)


# ---------------------------------------------------------------------------
# handle: backend dispatch
# ---------------------------------------------------------------------------


class TestHandleDispatch:
    def test_sync_backend_is_constructed_and_dispatched(self):
        args = _args(rich_ascii=True)
        config = object()
        with patch.object(
            mod, "create_provider", return_value=MagicMock()
        ) as factory, patch.object(mod.logging, "basicConfig"), patch.object(
            mod, "resolve_connection_config_from_args", return_value=config
        ), patch.object(
            mod, "MariaDBBackend"
        ) as backend_cls, patch.object(
            mod, "_execute_query_sync"
        ) as execute:
            mod.handle(args)
        factory.assert_called_once_with("json", ascii_borders=True)
        backend_cls.assert_called_once_with(connection_config=config)
        args_to_execute = execute.call_args[0]
        assert args_to_execute[0] == "SELECT 1"
        assert args_to_execute[2] is factory.return_value
        assert execute.call_args.kwargs == {"use_ascii": True}

    def test_async_backend_is_constructed_and_run_via_asyncio(self):
        args = _args(is_async=True)
        config = object()
        with patch.object(mod, "create_provider", return_value=MagicMock()), patch.object(
            mod.logging, "basicConfig"
        ), patch.object(
            mod, "resolve_connection_config_from_args", return_value=config
        ), patch.object(
            mod, "AsyncMariaDBBackend"
        ) as backend_cls, patch.object(
            mod.asyncio, "run"
        ) as run, patch.object(
            mod, "_execute_query_async", new=MagicMock()
        ) as coro:
            mod.handle(args)
        backend_cls.assert_called_once_with(connection_config=config)
        coro.assert_called_once()
        run.assert_called_once()
