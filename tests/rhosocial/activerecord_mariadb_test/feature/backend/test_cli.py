# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_cli.py
"""
Tests for MariaDB backend CLI (cli/ subpackage).

Tests argument parsing, help output, and basic CLI functionality.
"""

import pytest
import sys
from unittest.mock import patch


class TestCLIParseArgs:
    """Tests for CLI argument parsing."""

    def test_parse_args_default_values(self):
        """Test default argument values for info subcommand."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'info']):
            args = parse_args()

            assert args.command == 'info'
            assert args.host == 'localhost'
            assert args.port == 3306
            assert args.user == 'root'
            assert args.password == ''
            assert args.charset == 'utf8mb4'
            assert args.output == 'table'
            assert args.is_async is False
            assert args.verbose == 0

    def test_parse_args_custom_values(self):
        """Test custom argument values for query subcommand."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', [
            'mysql', 'query',
            '--host', 'db.example.com',
            '--port', '3307',
            '--user', 'admin',
            '--password', 'secret',
            '--database', 'testdb',
            '--charset', 'latin1',
            '--output', 'json',
            '--log-level', 'DEBUG',
            'SELECT 1',
        ]):
            args = parse_args()

            assert args.command == 'query'
            assert args.host == 'db.example.com'
            assert args.port == 3307
            assert args.user == 'admin'
            assert args.password == 'secret'
            assert args.database == 'testdb'
            assert args.charset == 'latin1'
            assert args.output == 'json'
            assert args.log_level == 'DEBUG'

    def test_parse_args_query_subcommand(self):
        """Test query subcommand parsing."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'query', 'SELECT 1']):
            args = parse_args()

            assert args.command == 'query'
            assert args.sql == 'SELECT 1'

    def test_parse_args_query_with_file(self):
        """Test query subcommand with file option."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'query', '-f', 'test.sql']):
            args = parse_args()

            assert args.command == 'query'
            assert args.file == 'test.sql'
            assert args.sql is None

    def test_parse_args_introspect_subcommand(self):
        """Test introspect subcommand parsing."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'introspect', 'tables']):
            args = parse_args()

            assert args.command == 'introspect'
            assert args.type == 'tables'

    def test_parse_args_introspect_with_name(self):
        """Test introspect subcommand with table name."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'introspect', 'table', 'users']):
            args = parse_args()

            assert args.command == 'introspect'
            assert args.type == 'table'
            assert args.name == 'users'

    def test_parse_args_introspect_valid_types(self):
        """Test all valid introspect types."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import INTROSPECT_TYPES

        for introspect_type in INTROSPECT_TYPES:
            with patch.object(sys, 'argv', ['mysql', 'introspect', introspect_type]):
                args = parse_args()
                assert args.type == introspect_type

    def test_parse_args_async(self):
        """Test --async flag in query subcommand."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'query', '--async', 'SELECT 1']):
            args = parse_args()

            assert args.command == 'query'
            assert args.is_async is True

    def test_parse_args_verbose(self):
        """Test verbose flags with subcommand."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'info', '-v']):
            args = parse_args()
            assert args.verbose == 1

        with patch.object(sys, 'argv', ['mysql', 'info', '-vv']):
            args = parse_args()
            assert args.verbose == 2

    def test_parse_args_info_command(self):
        """Test info subcommand."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'info']):
            args = parse_args()

            assert args.command == 'info'

    def test_parse_args_version(self):
        """Test --version option in info subcommand."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'info', '--version', '5.7.0']):
            args = parse_args()

            assert args.command == 'info'
            assert args.version == '5.7.0'


class TestCLISerialization:
    """Tests for CLI output serialization."""

    def test_serialize_none(self):
        """Test serializing None."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        assert _serialize_for_output(None) is None

    def test_serialize_string(self):
        """Test serializing string."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        assert _serialize_for_output("test") == "test"

    def test_serialize_int(self):
        """Test serializing integer."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        assert _serialize_for_output(42) == 42

    def test_serialize_float(self):
        """Test serializing float."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        assert _serialize_for_output(3.14) == 3.14

    def test_serialize_bool(self):
        """Test serializing boolean."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        assert _serialize_for_output(True) is True
        assert _serialize_for_output(False) is False

    def test_serialize_list(self):
        """Test serializing list."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        result = _serialize_for_output([1, "two", None])
        assert result == [1, "two", None]

    def test_serialize_dict(self):
        """Test serializing dict."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        result = _serialize_for_output({"key": "value", "num": 42})
        assert result == {"key": "value", "num": 42}

    def test_serialize_nested(self):
        """Test serializing nested structures."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        result = _serialize_for_output({
            "list": [1, 2, 3],
            "nested": {"a": "b"}
        })
        assert result == {"list": [1, 2, 3], "nested": {"a": "b"}}

    def test_serialize_enum(self):
        """Test serializing Enum."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output
        from enum import Enum

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        assert _serialize_for_output(Color.RED) == "red"
        assert _serialize_for_output(Color.BLUE) == "blue"

    def test_serialize_fallback(self):
        """Test fallback serialization for unknown types."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        class CustomObject:
            def __str__(self):
                return "custom"

        result = _serialize_for_output(CustomObject())
        assert result == "custom"


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_help(self, capsys):
        """Test main help output doesn't crash."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', '--help']):
            with pytest.raises(SystemExit):
                parse_args()

        captured = capsys.readouterr()
        assert 'Execute SQL queries' in captured.out or 'usage:' in captured.out.lower()

    def test_query_help(self, capsys):
        """Test query subcommand help."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'query', '--help']):
            with pytest.raises(SystemExit):
                parse_args()

        captured = capsys.readouterr()
        assert 'query' in captured.out.lower() or 'sql' in captured.out.lower()

    def test_introspect_help(self, capsys):
        """Test introspect subcommand help."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'introspect', '--help']):
            with pytest.raises(SystemExit):
                parse_args()

        captured = capsys.readouterr()
        assert 'introspect' in captured.out.lower() or 'type' in captured.out.lower()


class TestCLIUtilityFunctions:
    """Tests for CLI utility functions."""

    def test_parse_version(self):
        """Test parse_version function."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import parse_version

        assert parse_version('8.0.0') == (8, 0, 0)
        assert parse_version('5.7.8') == (5, 7, 8)
        assert parse_version('9') == (9, 0, 0)
        assert parse_version('8.0') == (8, 0, 0)

    def test_get_status_style(self):
        """Test _get_status_style function."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import _get_status_style

        # 100% coverage
        color, symbol = _get_status_style(100)
        assert color == 'green'
        assert '[OK]' in symbol

        # 75% coverage
        color, symbol = _get_status_style(75)
        assert color == 'yellow'
        assert '[~]' in symbol

        # 50% coverage
        color, symbol = _get_status_style(50)
        assert color == 'yellow'
        assert '[~]' in symbol

        # 25% coverage
        color, symbol = _get_status_style(25)
        assert color == 'red'
        assert '[~]' in symbol

        # 0% coverage
        color, symbol = _get_status_style(0)
        assert color == 'red'
        assert '[X]' in symbol

    def test_format_method_display(self):
        """Test format_method_display function."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import _format_method_display as format_method_display

        assert format_method_display('supports_window_function') == 'window function'
        assert format_method_display('is_cte_available') == 'is cte available'
        assert format_method_display('supports_explain_format') == 'explain format'

    def test_calculate_protocol_stats(self):
        """Test _calculate_protocol_stats function."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import _calculate_protocol_stats

        # All boolean True
        stats = {'method1': True, 'method2': True}
        supported, total = _calculate_protocol_stats(stats)
        assert supported == 2
        assert total == 2

        # Mixed boolean
        stats = {'method1': True, 'method2': False}
        supported, total = _calculate_protocol_stats(stats)
        assert supported == 1
        assert total == 2

        # With dict values (parameterized methods)
        stats = {
            'method1': True,
            'method2': {'supported': 3, 'total': 5, 'args': {}}
        }
        supported, total = _calculate_protocol_stats(stats)
        assert supported == 4
        assert total == 6

    def test_get_protocol_support_methods(self):
        """Test get_protocol_support_methods function."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import get_protocol_support_methods
        from rhosocial.activerecord.backend.dialect.protocols import WindowFunctionSupport

        methods = get_protocol_support_methods(WindowFunctionSupport)
        assert 'supports_window_functions' in methods
        assert 'supports_window_frame_clause' in methods

    def test_serialize_pydantic_model(self):
        """Test serializing Pydantic model."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            value: int

        result = _serialize_for_output(TestModel(name="test", value=42))
        assert result == {'name': 'test', 'value': 42}

    def test_serialize_dataclass(self):
        """Test serializing dataclass."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output
        from dataclasses import dataclass

        @dataclass
        class TestData:
            name: str
            value: int

        result = _serialize_for_output(TestData(name="test", value=42))
        assert result == {'name': 'test', 'value': 42}

    def test_serialize_tuple(self):
        """Test serializing tuple."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.introspect import _serialize_for_output

        result = _serialize_for_output((1, 2, 3))
        assert result == [1, 2, 3]


class TestCLIProviderFactory:
    """Tests for CLI output provider factory."""

    def test_get_provider_json(self):
        """Test create_provider returns JsonOutputProvider for json output."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.output import create_provider

        provider = create_provider('json')
        assert provider.__class__.__name__ == 'JsonOutputProvider'

    def test_get_provider_csv(self):
        """Test create_provider returns CsvOutputProvider for csv output."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.output import create_provider

        provider = create_provider('csv')
        assert provider.__class__.__name__ == 'CsvOutputProvider'

    def test_get_provider_tsv(self):
        """Test create_provider returns TsvOutputProvider for tsv output."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.output import create_provider

        provider = create_provider('tsv')
        assert provider.__class__.__name__ == 'TsvOutputProvider'


class TestCLICheckProtocolSupport:
    """Tests for check_protocol_support function."""

    def test_check_protocol_support_basic(self):
        """Test check_protocol_support with basic protocol."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import check_protocol_support
        from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
        from rhosocial.activerecord.backend.dialect.protocols import WindowFunctionSupport

        dialect = MariaDBDialect(version=(10, 11, 0))

        results = check_protocol_support(dialect, WindowFunctionSupport)
        assert 'supports_window_functions' in results
        assert results['supports_window_functions'] is True
        assert 'supports_window_frame_clause' in results

    def test_check_protocol_support_with_params(self):
        """Test check_protocol_support with parameterized methods."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import check_protocol_support
        from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
        from rhosocial.activerecord.backend.dialect.protocols import ExplainSupport

        dialect = MariaDBDialect(version=(10, 11, 0))

        results = check_protocol_support(dialect, ExplainSupport)
        assert 'supports_explain_format' in results
        # Should return dict with args for parameterized methods
        if isinstance(results['supports_explain_format'], dict):
            assert 'supported' in results['supports_explain_format']
            assert 'total' in results['supports_explain_format']
            assert 'args' in results['supports_explain_format']


class TestCLIBuildProtocolInfo:
    """Tests for _build_protocol_info function."""

    def test_build_protocol_info_verbose_0(self):
        """Test _build_protocol_info with verbose=0."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import (
            _build_protocol_info, PROTOCOL_FAMILY_GROUPS
        )
        from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

        dialect = MariaDBDialect(version=(10, 11, 0))
        group_name = "Query Features"
        protocols = PROTOCOL_FAMILY_GROUPS[group_name]

        result = _build_protocol_info(dialect, group_name, protocols, verbose=0)

        assert isinstance(result, dict)
        for protocol_name, stats in result.items():
            assert 'supported' in stats
            assert 'total' in stats
            assert 'percentage' in stats
            assert 'methods' not in stats  # verbose < 2

    def test_build_protocol_info_verbose_2(self):
        """Test _build_protocol_info with verbose=2."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import (
            _build_protocol_info, PROTOCOL_FAMILY_GROUPS
        )
        from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

        dialect = MariaDBDialect(version=(10, 11, 0))
        group_name = "Query Features"
        protocols = PROTOCOL_FAMILY_GROUPS[group_name]

        result = _build_protocol_info(dialect, group_name, protocols, verbose=2)

        assert isinstance(result, dict)
        for protocol_name, stats in result.items():
            assert 'supported' in stats
            assert 'total' in stats
            assert 'percentage' in stats
            assert 'methods' in stats  # verbose >= 2


class TestCLIHandleInfo:
    """Tests for handle_info function."""

    def test_handle_info_json_output(self, capsys):
        """Test handle_info with JSON output (no database required)."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import handle
        from rhosocial.activerecord.backend.impl.mariadb.cli.output import create_provider
        from unittest.mock import MagicMock

        args = MagicMock()
        args.output = 'json'
        args.database = None
        args.host = 'localhost'
        args.port = 3306
        args.user = 'root'
        args.password = ''
        args.charset = 'utf8mb4'
        args.version = '8.0.0'
        args.verbose = 0
        args.named_connection = None

        # Create a JSON provider
        args.rich_ascii = False
        provider = create_provider(args.output, ascii_borders=args.rich_ascii)

        handle(args)

        captured = capsys.readouterr()
        # Should output JSON
        import json
        output = json.loads(captured.out)
        assert 'database' in output
        assert 'features' in output
        assert 'protocols' in output
        assert output['database']['type'] == 'mariadb'


class TestCLIDisplayFunctions:
    """Tests for CLI display helper functions."""

    def test_display_method_details_bool(self):
        """Test _display_method_details with boolean value."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import _display_method_details

        # Mock console
        class MockConsole:
            def print(self, msg):
                self.output = getattr(self, 'output', '') + msg + '\n'

        console = MockConsole()
        _display_method_details(console, 'supports_test', True)

        # Should contain OK marker
        assert '[OK]' in console.output or 'test' in console.output.lower()

    def test_display_method_details_dict(self):
        """Test _display_method_details with dict value (parameterized method)."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import _display_method_details

        class MockConsole:
            def print(self, msg):
                self.output = getattr(self, 'output', '') + msg + '\n'

        console = MockConsole()
        value = {'args': {'JSON': True, 'XML': False}}
        _display_method_details(console, 'supports_format', value)

        # Should contain the args
        assert 'JSON' in console.output or 'XML' in console.output

    def test_display_protocol_item_verbose_0(self):
        """Test _display_protocol_item with verbose=0."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import _display_protocol_item

        class MockConsole:
            def print(self, msg):
                self.output = getattr(self, 'output', '') + msg + '\n'

        console = MockConsole()
        stats = {'supported': 5, 'total': 10, 'percentage': 50.0}

        _display_protocol_item(console, 'TestProtocol', stats, verbose=0)

        # Should show 50%
        assert '50%' in console.output or '5/10' in console.output

    def test_display_protocol_item_verbose_2(self):
        """Test _display_protocol_item with verbose=2 and methods."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import _display_protocol_item

        class MockConsole:
            def print(self, msg):
                self.output = getattr(self, 'output', '') + msg + '\n'

        console = MockConsole()
        stats = {
            'supported': 1,
            'total': 1,
            'percentage': 100.0,
            'methods': {'supports_test': True}
        }

        _display_protocol_item(console, 'TestProtocol', stats, verbose=2)

        # Should show 100% and method details
        assert '100%' in console.output

    def test_display_protocol_group(self):
        """Test _display_protocol_group."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import _display_protocol_group

        class MockConsole:
            def print(self, msg):
                self.output = getattr(self, 'output', '') + msg + '\n'

        console = MockConsole()
        protocols = {
            'TestProtocol': {'supported': 5, 'total': 10, 'percentage': 50.0}
        }

        _display_protocol_group(console, 'Test Group', protocols, verbose=0)

        # Should contain group name
        assert 'Test Group' in console.output

    def test_display_protocol_group_dialect_specific(self):
        """Test _display_protocol_group with dialect-specific group."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import (
            _display_protocol_group, DIALECT_SPECIFIC_GROUPS
        )

        class MockConsole:
            def print(self, msg):
                self.output = getattr(self, 'output', '') + msg + '\n'

        console = MockConsole()
        protocols = {
            'TestProtocol': {'supported': 5, 'total': 10, 'percentage': 50.0}
        }

        # Use a dialect-specific group name
        group_name = list(DIALECT_SPECIFIC_GROUPS)[0] if DIALECT_SPECIFIC_GROUPS else "MariaDB-specific"
        _display_protocol_group(console, group_name, protocols, verbose=0)

        # Should contain dialect-specific marker
        assert group_name in console.output


class TestCLIHandleInfoVerbose:
    """Tests for handle_info with different verbosity levels."""

    def test_handle_info_verbose_1(self, capsys):
        """Test handle_info with verbose=1."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import handle
        from rhosocial.activerecord.backend.impl.mariadb.cli.output import create_provider
        from unittest.mock import MagicMock

        args = MagicMock()
        args.output = 'json'
        args.database = None
        args.version = '8.0.0'
        args.verbose = 1
        args.rich_ascii = False
        args.named_connection = None

        provider = create_provider(args.output, ascii_borders=args.rich_ascii)
        handle(args)

        captured = capsys.readouterr()
        import json
        output = json.loads(captured.out)
        assert 'protocols' in output

    def test_handle_info_verbose_2(self, capsys):
        """Test handle_info with verbose=2."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import handle
        from rhosocial.activerecord.backend.impl.mariadb.cli.output import create_provider
        from unittest.mock import MagicMock

        args = MagicMock()
        args.output = 'json'
        args.database = None
        args.version = '8.0.0'
        args.verbose = 2
        args.rich_ascii = False
        args.named_connection = None

        provider = create_provider(args.output, ascii_borders=args.rich_ascii)
        handle(args)

        captured = capsys.readouterr()
        import json
        output = json.loads(captured.out)
        assert 'protocols' in output

        # With verbose >= 2, methods should be included
        for group_name, protocols in output['protocols'].items():
            for protocol_name, stats in protocols.items():
                assert 'methods' in stats

    def test_handle_info_with_version(self, capsys):
        """Test handle_info with custom version."""
        from rhosocial.activerecord.backend.impl.mariadb.cli.info import handle
        from rhosocial.activerecord.backend.impl.mariadb.cli.output import create_provider
        from unittest.mock import MagicMock

        args = MagicMock()
        args.output = 'json'
        args.database = None
        args.version = '5.7.0'
        args.verbose = 0
        args.rich_ascii = False
        args.named_connection = None

        provider = create_provider(args.output, ascii_borders=args.rich_ascii)
        handle(args)

        captured = capsys.readouterr()
        import json
        output = json.loads(captured.out)
        assert output['database']['version'] == '5.7.0'
        assert output['database']['version_tuple'] == [5, 7, 0]


class TestCLIIntrospectArgParsing:
    """Tests for introspect argument parsing edge cases."""

    def test_introspect_with_schema(self):
        """Test introspect with --schema option."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'introspect', 'tables', '--schema', 'mydb']):
            args = parse_args()

            assert args.command == 'introspect'
            assert args.type == 'tables'
            assert args.schema == 'mydb'

    def test_introspect_with_include_system(self):
        """Test introspect with --include-system flag."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'introspect', 'tables', '--include-system']):
            args = parse_args()

            assert args.command == 'introspect'
            assert args.include_system is True

    def test_introspect_all_types_with_name(self):
        """Test introspect types that require name parameter."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        # table type with name
        with patch.object(sys, 'argv', ['mysql', 'introspect', 'table', 'users']):
            args = parse_args()
            assert args.type == 'table'
            assert args.name == 'users'

        # columns type with name
        with patch.object(sys, 'argv', ['mysql', 'introspect', 'columns', 'orders']):
            args = parse_args()
            assert args.type == 'columns'
            assert args.name == 'orders'

        # indexes type with name
        with patch.object(sys, 'argv', ['mysql', 'introspect', 'indexes', 'products']):
            args = parse_args()
            assert args.type == 'indexes'
            assert args.name == 'products'

        # foreign-keys type with name
        with patch.object(sys, 'argv', ['mysql', 'introspect', 'foreign-keys', 'items']):
            args = parse_args()
            assert args.type == 'foreign-keys'
            assert args.name == 'items'


class TestCLIQueryArgParsing:
    """Tests for query argument parsing edge cases."""

    def test_query_with_all_connection_options(self):
        """Test query with all connection options."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', [
            'mysql', 'query',
            '--host', 'db.example.com',
            '--port', '3307',
            '--user', 'admin',
            '--password', 'secret',
            '--database', 'testdb',
            '--charset', 'utf8mb4',
            '--output', 'json',
            '--log-level', 'DEBUG',
            '--async',
            '--rich-ascii',
            'SELECT 1'
        ]):
            args = parse_args()

            assert args.command == 'query'
            assert args.host == 'db.example.com'
            assert args.port == 3307
            assert args.user == 'admin'
            assert args.password == 'secret'
            assert args.database == 'testdb'
            assert args.charset == 'utf8mb4'
            assert args.output == 'json'
            assert args.log_level == 'DEBUG'
            assert args.is_async is True
            assert args.rich_ascii is True
            assert args.sql == 'SELECT 1'

    def test_query_output_formats(self):
        """Test query with different output formats."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        for output_format in ['table', 'json', 'csv', 'tsv']:
            with patch.object(sys, 'argv', ['mysql', 'query', '-o', output_format, 'SELECT 1']):
                args = parse_args()
                assert args.output == output_format


class TestCLINamedExpressionArgs:
    """Tests for named-expression subcommand argument parsing."""

    def test_parse_args_named_expression_basic(self):
        """Test basic named-expression parsing."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-expression', 'myapp.queries.users.active_users']):
            args = parse_args()

            assert args.command == 'named-expression'
            assert args.qualified_name == 'myapp.queries.users.active_users'

    def test_parse_args_named_expression_with_params(self):
        """Test named-expression with parameters."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', [
            'mysql', 'named-expression', 'myapp.queries.users.active_users',
            '--param', 'limit=50',
            '--param', 'status=active',
        ]):
            args = parse_args()

            assert args.command == 'named-expression'
            assert args.params == ['limit=50', 'status=active']

    def test_parse_args_named_expression_dry_run(self):
        """Test named-expression with --dry-run."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-expression', 'myapp.queries.test', '--dry-run']):
            args = parse_args()

            assert args.command == 'named-expression'
            assert args.dry_run is True

    def test_parse_args_named_expression_describe(self):
        """Test named-expression with --describe."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-expression', 'myapp.queries.test', '--describe']):
            args = parse_args()

            assert args.command == 'named-expression'
            assert args.describe is True

    def test_parse_args_named_expression_list(self):
        """Test named-expression with --list."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-expression', 'myapp.queries', '--list']):
            args = parse_args()

            assert args.command == 'named-expression'
            assert args.list_queries is True

    def test_parse_args_named_expression_async(self):
        """Test named-expression with --async."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-expression', 'myapp.queries.test', '--async']):
            args = parse_args()

            assert args.command == 'named-expression'
            assert args.is_async is True


class TestCLINamedProcedureArgs:
    """Tests for named-procedure subcommand argument parsing."""

    def test_parse_args_named_procedure_basic(self):
        """Test basic named-procedure parsing."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-procedure', 'myapp.procedures.monthly_cleanup']):
            args = parse_args()

            assert args.command == 'named-procedure'
            assert args.qualified_name == 'myapp.procedures.monthly_cleanup'

    def test_parse_args_named_procedure_with_params(self):
        """Test named-procedure with parameters."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', [
            'mysql', 'named-procedure', 'myapp.procedures.monthly_cleanup',
            '--param', 'month=2026-03',
        ]):
            args = parse_args()

            assert args.command == 'named-procedure'
            assert args.params == ['month=2026-03']

    def test_parse_args_named_procedure_transaction_auto(self):
        """Test named-procedure with --transaction auto."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-procedure', 'myapp.procedures.test', '--transaction', 'auto']):
            args = parse_args()

            assert args.command == 'named-procedure'
            assert args.transaction == 'auto'

    def test_parse_args_named_procedure_transaction_step(self):
        """Test named-procedure with --transaction step."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-procedure', 'myapp.procedures.test', '--transaction', 'step']):
            args = parse_args()

            assert args.command == 'named-procedure'
            assert args.transaction == 'step'

    def test_parse_args_named_procedure_transaction_none(self):
        """Test named-procedure with --transaction none."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-procedure', 'myapp.procedures.test', '--transaction', 'none']):
            args = parse_args()

            assert args.command == 'named-procedure'
            assert args.transaction == 'none'

    def test_parse_args_named_procedure_dry_run(self):
        """Test named-procedure with --dry-run."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-procedure', 'myapp.procedures.test', '--dry-run']):
            args = parse_args()

            assert args.command == 'named-procedure'
            assert args.dry_run is True

    def test_parse_args_named_procedure_describe(self):
        """Test named-procedure with --describe."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-procedure', 'myapp.procedures.test', '--describe']):
            args = parse_args()

            assert args.command == 'named-procedure'
            assert args.describe is True

    def test_parse_args_named_procedure_list(self):
        """Test named-procedure with --list."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-procedure', 'myapp.procedures', '--list']):
            args = parse_args()

            assert args.command == 'named-procedure'
            assert args.list_procedures is True

    def test_parse_args_named_procedure_async(self):
        """Test named-procedure with --async."""
        from rhosocial.activerecord.backend.impl.mariadb.__main__ import parse_args

        with patch.object(sys, 'argv', ['mysql', 'named-procedure', 'myapp.procedures.test', '--async']):
            args = parse_args()

            assert args.command == 'named-procedure'
            assert args.is_async is True
