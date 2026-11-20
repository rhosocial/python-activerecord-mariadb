# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/cli/test_named_expression_offline.py
"""Offline unit tests for ``mariadb.cli.named_expression``.

The module is an adapter over the shared named-expression helper, so the tests
capture the callbacks handed to that helper and invoke them against mocked
backends. No database, driver or network access occurs.
"""

import argparse
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rhosocial.activerecord.backend.impl.mariadb.cli import named_expression as mod

_SHARED = "rhosocial.activerecord.backend.named_expression.cli"
_DIALECT = "rhosocial.activerecord.backend.impl.mariadb.dialect.MariaDBDialect"


def _args(**overrides):
    values = dict(
        output="json",
        rich_ascii=False,
        is_async=False,
        dialect_version=None,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


@contextmanager
def _run_handle(args):
    """Call ``handle`` with collaborators mocked; yield the seams while patched.

    The callbacks close over module globals, so the patches must stay in place
    while a test invokes them -- hence the context manager rather than a helper
    that returns the captured callbacks.
    """
    provider = MagicMock()
    config = object()
    with patch(f"{_SHARED}.handle_named_expression") as handle_nq, patch.object(
        mod, "create_provider", return_value=provider
    ) as provider_factory, patch.object(
        mod, "resolve_connection_config_from_args", return_value=config
    ) as resolve, patch.object(
        mod, "MariaDBBackend"
    ) as backend_cls, patch.object(
        mod, "AsyncMariaDBBackend"
    ) as async_backend_cls, patch(
        _DIALECT
    ) as dialect_cls:
        mod.handle(args)
        handle_nq.assert_called_once()
        yield dict(
            args=args,
            handle_nq=handle_nq,
            callbacks=handle_nq.call_args.kwargs,
            provider=provider,
            provider_factory=provider_factory,
            resolve=resolve,
            config=config,
            backend_cls=backend_cls,
            async_backend_cls=async_backend_cls,
            dialect_cls=dialect_cls,
        )


# ---------------------------------------------------------------------------
# create_parser
# ---------------------------------------------------------------------------


class TestCreateParser:
    def test_delegates_to_shared_helper_with_local_parent_and_epilog(self):
        shared = MagicMock(return_value=argparse.ArgumentParser(prog="x"))
        with patch(f"{_SHARED}.create_named_expression_parser", shared):
            mod.create_parser("SUBS")
        shared.assert_called_once()
        positional, kwargs = shared.call_args
        assert positional[0] == "SUBS"
        assert isinstance(positional[1], argparse.ArgumentParser)
        assert "myapp.queries" in kwargs["epilog"]
        parent_flags = vars(positional[1].parse_args([]))
        for flag in ("host", "port", "database", "output", "rich_ascii"):
            assert flag in parent_flags

    def test_dialect_version_argument_is_added(self):
        shared = MagicMock(return_value=argparse.ArgumentParser(prog="x"))
        with patch(f"{_SHARED}.create_named_expression_parser", shared):
            parser = mod.create_parser("SUBS")
        assert parser.parse_args([]).dialect_version is None
        assert parser.parse_args(["--dialect-version", "11.4.0"]).dialect_version == "11.4.0"


# ---------------------------------------------------------------------------
# handle: provider and callback wiring
# ---------------------------------------------------------------------------


class TestHandleWiring:
    def test_provider_is_created_from_args(self):
        with _run_handle(_args(output="csv", rich_ascii=True)) as seams:
            seams["provider_factory"].assert_called_once_with("csv", ascii_borders=True)

    def test_sync_callbacks_are_supplied(self):
        with _run_handle(_args()) as seams:
            callbacks = seams["callbacks"]
            for name in (
                "backend_factory",
                "get_dialect",
                "execute_query",
                "disconnect",
                "create_dialect",
            ):
                assert name in callbacks
            assert "backend_async_factory" not in callbacks

    def test_async_callbacks_are_supplied(self):
        with _run_handle(_args(is_async=True)) as seams:
            callbacks = seams["callbacks"]
            for name in (
                "backend_async_factory",
                "get_dialect_async",
                "execute_query_async",
                "disconnect_async",
                "create_dialect",
            ):
                assert name in callbacks

    def test_handle_is_called_with_provider(self):
        with _run_handle(_args()) as seams:
            positional = seams["handle_nq"].call_args.args
            assert positional[0] is seams["args"]
            assert positional[1] is seams["provider"]


# ---------------------------------------------------------------------------
# handle: sync factories
# ---------------------------------------------------------------------------


class TestSyncFactories:
    def test_backend_factory_connects_and_adapts(self):
        with _run_handle(_args()) as seams:
            seams["callbacks"]["backend_factory"]()
            seams["backend_cls"].assert_called_once_with(connection_config=seams["config"])
            backend = seams["backend_cls"].return_value
            backend.connect.assert_called_once_with()
            backend.introspect_and_adapt.assert_called_once_with()
            seams["resolve"].assert_called_once_with(seams["args"])

    def test_backend_factory_applies_requested_dialect_version(self):
        with _run_handle(_args(dialect_version="11.4.0")) as seams:
            seams["callbacks"]["backend_factory"]()
            assert seams["backend_cls"].return_value._dialect.version == (11, 4, 0)

    def test_create_dialect_passes_parsed_version(self):
        with _run_handle(_args(dialect_version="10.6.2")) as seams:
            dialect = seams["callbacks"]["create_dialect"]()
            seams["dialect_cls"].assert_called_once_with(version=(10, 6, 2))
            assert dialect is seams["dialect_cls"].return_value

    def test_create_dialect_without_version(self):
        with _run_handle(_args()) as seams:
            seams["callbacks"]["create_dialect"]()
            seams["dialect_cls"].assert_called_once_with(version=None)

    @pytest.mark.parametrize(
        "version,expected", [("11.4.0", (11, 4, 0)), ("10.6", (10, 6)), ("9", (9,))]
    )
    def test_version_strings_are_split_into_integer_tuples(self, version, expected):
        with _run_handle(_args(dialect_version=version)) as seams:
            seams["callbacks"]["create_dialect"]()
            assert seams["dialect_cls"].call_args.kwargs["version"] == expected

    def test_malformed_version_raises_value_error(self):
        with _run_handle(_args(dialect_version="11.x")) as seams:
            with pytest.raises(ValueError):
                seams["callbacks"]["create_dialect"]()

    def test_get_dialect_returns_backend_dialect(self):
        with _run_handle(_args()) as seams:
            backend = MagicMock()
            assert seams["callbacks"]["get_dialect"](backend) is backend.dialect

    def test_execute_query_passes_statement_type_in_options(self):
        with _run_handle(_args()) as seams:
            backend = seams["callbacks"]["backend_factory"]()
            seams["callbacks"]["execute_query"]("SELECT 1", ("p",), "SELECT")
            backend.execute.assert_called_once()
            args, kwargs = backend.execute.call_args
            assert args == ("SELECT 1", ("p",))
            assert kwargs["options"].stmt_type == "SELECT"

    def test_disconnect_only_when_connection_is_open(self):
        with _run_handle(_args()) as seams:
            backend = seams["callbacks"]["backend_factory"]()
            backend._connection = True
            seams["callbacks"]["disconnect"]()
            backend.disconnect.assert_called_once_with()

            backend._connection = False
            seams["callbacks"]["disconnect"]()
            backend.disconnect.assert_called_once_with()


# ---------------------------------------------------------------------------
# handle: async factories (native async driver)
# ---------------------------------------------------------------------------


class TestAsyncFactories:
    def test_async_backend_factory_only_constructs(self):
        with _run_handle(_args(is_async=True)) as seams:
            backend = seams["callbacks"]["backend_async_factory"]()
            seams["async_backend_cls"].assert_called_once_with(connection_config=seams["config"])
            assert backend is seams["async_backend_cls"].return_value
            backend.connect.assert_not_called()

    async def test_async_get_dialect_returns_backend_dialect(self):
        with _run_handle(_args(is_async=True)) as seams:
            backend = MagicMock()
            result = await seams["callbacks"]["get_dialect_async"](backend)
            assert result is backend.dialect

    async def test_async_execute_passes_statement_type_in_options(self):
        with _run_handle(_args(is_async=True)) as seams:
            backend = seams["callbacks"]["backend_async_factory"]()
            backend.execute = AsyncMock(return_value="ok")
            result = await seams["callbacks"]["execute_query_async"]("SELECT 2", (), "SELECT")
            backend.execute.assert_awaited_once()
            args, kwargs = backend.execute.call_args
            assert args == ("SELECT 2", ())
            assert kwargs["options"].stmt_type == "SELECT"
            assert result == "ok"

    async def test_async_disconnect_is_awaited_only_when_connected(self):
        with _run_handle(_args(is_async=True)) as seams:
            backend = seams["callbacks"]["backend_async_factory"]()
            backend.disconnect = AsyncMock()
            backend._connection = True
            await seams["callbacks"]["disconnect_async"]()
            backend.disconnect.assert_awaited_once_with()

            backend.disconnect.reset_mock()
            backend._connection = False
            await seams["callbacks"]["disconnect_async"]()
            backend.disconnect.assert_not_awaited()
