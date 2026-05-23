# tests/rhosocial/activerecord_mariadb_test/feature/backend/named_connection/test_named_connection_cli.py
"""
Tests for MariaDB CLI parameter resolution.

This module tests the CLI parameter resolution priority for MariaDB.
"""
import os
import tempfile
import types
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


class MockArgs:
    """Mock arguments for testing."""

    def __init__(
        self,
        host=None,
        port=None,
        database=None,
        user=None,
        password=None,
        charset=None,
        named_connection=None,
        connection_params=None,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.charset = charset
        self.named_connection = named_connection
        self.connection_params = connection_params or []


class TestMariaDBConnectionConfigPriority:
    """Test connection config resolution priority for MariaDB CLI."""

    def test_default_values(self):
        """Test that default MariaDB values are used when no connection specified."""
        args = MockArgs()
        from rhosocial.activerecord.backend.impl.mariadb.cli.connection import resolve_connection_config_from_args

        with patch(
            "rhosocial.activerecord.backend.named_connection.NamedConnectionResolver"
        ):
            config = resolve_connection_config_from_args(args)

        assert config.host == "localhost"
        assert config.port == 3306

    def test_explicit_params_only(self):
        """Test explicit --host, --port, etc. without named connection."""
        args = MockArgs(
            host="myhost",
            port=3307,
            database="mydb",
            user="myuser",
            password="mypass",
        )
        from rhosocial.activerecord.backend.impl.mariadb.cli.connection import resolve_connection_config_from_args

        with patch(
            "rhosocial.activerecord.backend.named_connection.NamedConnectionResolver"
        ):
            config = resolve_connection_config_from_args(args)

        assert config.host == "myhost"
        assert config.port == 3307
        assert config.database == "mydb"
        assert config.username == "myuser"

    def test_named_connection_only(self):
        """Test --named-connection without explicit params."""
        args = MockArgs(
            named_connection="myapp.connections.prod_db",
        )
        from rhosocial.activerecord.backend.impl.mariadb.cli.connection import resolve_connection_config_from_args

        mock_resolver = MagicMock()
        mock_config = MariaDBConnectionConfig(
            host="prod.example.com",
            port=3306,
            database="prod",
        )
        mock_resolver.load.return_value = mock_resolver
        mock_resolver.resolve.return_value = mock_config

        with patch(
            "rhosocial.activerecord.backend.named_connection.NamedConnectionResolver",
            return_value=mock_resolver,
        ):
            config = resolve_connection_config_from_args(args)

        mock_resolver.load.assert_called_once()
        assert config.host == "prod.example.com"

    def test_named_connection_with_params(self):
        """Test --named-connection with --conn-param overrides."""
        args = MockArgs(
            named_connection="myapp.connections.prod_db",
            connection_params=["database=custom_db", "charset=utf8mb4"],
        )
        from rhosocial.activerecord.backend.impl.mariadb.cli.connection import resolve_connection_config_from_args

        mock_resolver = MagicMock()
        mock_config = MariaDBConnectionConfig(host="prod.example.com")
        mock_resolver.load.return_value = mock_resolver
        mock_resolver.resolve.return_value = mock_config

        with patch(
            "rhosocial.activerecord.backend.named_connection.NamedConnectionResolver",
            return_value=mock_resolver,
        ):
            config = resolve_connection_config_from_args(args)

        mock_resolver.resolve.assert_called_once_with(
            {"database": "custom_db", "charset": "utf8mb4"}
        )

    def test_explicit_params_override_named_connection(self):
        """Test explicit params should NOT override named connection (MariaDB uses different approach).

        Note: Unlike SQLite where --db-file overrides named connection's database,
        MariaDB/PostgreSQL use --conn-param for overrides, not explicit host/port.
        """
        args = MockArgs(
            host="myhost",
            named_connection="myapp.connections.prod_db",
        )
        from rhosocial.activerecord.backend.impl.mariadb.cli.connection import resolve_connection_config_from_args

        mock_resolver = MagicMock()
        mock_config = MariaDBConnectionConfig(host="prod.example.com")
        mock_resolver.load.return_value = mock_resolver
        mock_resolver.resolve.return_value = mock_config

        with patch(
            "rhosocial.activerecord.backend.named_connection.NamedConnectionResolver",
            return_value=mock_resolver,
        ):
            config = resolve_connection_config_from_args(args)

        # Named connection is used, explicit host is ignored when named_connection present
        assert config.host == "prod.example.com"
