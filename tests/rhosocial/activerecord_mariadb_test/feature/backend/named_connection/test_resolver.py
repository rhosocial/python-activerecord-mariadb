# tests/rhosocial/activerecord_mariadb_test/feature/backend/named_connection/test_resolver.py
"""
Tests for MariaDB named connection resolver.

This test module covers:
- NamedConnectionResolver with MariaDB backend
- MariaDB-specific connection configurations
- Integration tests using example_connections module
"""
import types
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.named_connection.resolver import (
    NamedConnectionResolver,
    resolve_named_connection,
    list_named_connections_in_module,
)
from rhosocial.activerecord.backend.named_connection.exceptions import (
    NamedConnectionNotFoundError,
    NamedConnectionModuleNotFoundError,
    NamedConnectionInvalidReturnTypeError,
    NamedConnectionNotCallableError,
    NamedConnectionMissingParameterError,
    NamedConnectionInvalidParameterError,
)
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


class TestMariaDBNamedConnectionResolverUnit:
    """Unit tests for NamedConnectionResolver with MariaDB backend."""

    def test_resolve_mariadb_config(self):
        """Test resolving a MariaDB connection config."""
        module = types.ModuleType("test_mariadb_connections")

        def dev_db(database: str = "test_db"):
            return MariaDBConnectionConfig(
                host="localhost",
                port=3306,
                database=database,
                username="root",
                password="password",
            )

        module.dev_db = dev_db
        with patch("importlib.import_module", return_value=module):
            config = NamedConnectionResolver("test_mariadb_connections.dev_db").load().resolve({})
            assert isinstance(config, MariaDBConnectionConfig)
            assert config.host == "localhost"
            assert config.database == "test_db"

    def test_resolve_mariadb_with_custom_database(self):
        """Test resolving MariaDB config with custom database parameter."""
        module = types.ModuleType("test_mariadb_connections")

        def dev_db(database: str = "test_db"):
            return MariaDBConnectionConfig(
                host="localhost",
                port=3306,
                database=database,
                username="root",
                password="password",
            )

        module.dev_db = dev_db
        with patch("importlib.import_module", return_value=module):
            config = NamedConnectionResolver("test_mariadb_connections.dev_db").load().resolve(
                {"database": "my_app_db"}
            )
            assert isinstance(config, MariaDBConnectionConfig)
            assert config.database == "my_app_db"

    def test_resolve_mariadb_missing_required_param(self):
        """Test resolve fails when required MariaDB parameter is missing."""
        module = types.ModuleType("test_mariadb_connections")

        def strict_db(host: str):
            return MariaDBConnectionConfig(host=host)

        module.strict_db = strict_db
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_mariadb_connections.strict_db").load()
            with pytest.raises(NamedConnectionMissingParameterError):
                resolver.resolve({})

    def test_resolve_mariadb_invalid_return_type(self):
        """Test resolve fails when callable returns non-BaseConfig."""
        module = types.ModuleType("test_mariadb_connections")

        def bad_connection():
            return {"host": "localhost"}

        module.bad_connection = bad_connection
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_mariadb_connections.bad_connection").load()
            with pytest.raises(NamedConnectionInvalidReturnTypeError):
                resolver.resolve({})

    def test_list_mariadb_connections(self):
        """Test listing MariaDB connections in a module."""
        module = types.ModuleType("test_mariadb_connections")

        def dev_db(database: str = "test_db"):
            return MariaDBConnectionConfig(host="localhost", database=database)

        def prod_db():
            return MariaDBConnectionConfig(host="prod.example.com", database="prod")

        module.dev_db = dev_db
        module.prod_db = prod_db

        with patch("importlib.import_module", return_value=module):
            connections = list_named_connections_in_module("test_mariadb_connections")
            names = [c["name"] for c in connections]
            assert "dev_db" in names
            assert "prod_db" in names


class TestMariaDBNamedConnectionsIntegration:
    """Integration tests using example_connections loaded from YAML scenarios."""

    def _get_first_scenario_name(self) -> str:
        """Return the name of the first active scenario."""
        connections = list_named_connections_in_module(
            "rhosocial.activerecord_mariadb_test.feature.backend.named_connection.example_connections"
        )
        assert len(connections) > 0, "No scenarios found in example_connections"
        return connections[0]["name"]

    def test_resolve_yaml_scenario(self):
        """Test resolving a YAML-based named connection returns a valid MariaDBConnectionConfig."""
        name = self._get_first_scenario_name()
        config = resolve_named_connection(
            f"rhosocial.activerecord_mariadb_test.feature.backend.named_connection.example_connections.{name}",
            {},
        )
        assert isinstance(config, MariaDBConnectionConfig)
        assert isinstance(config.host, str) and config.host
        assert isinstance(config.port, int)
        assert isinstance(config.database, str) and config.database
        assert config.username is not None

    def test_resolve_with_custom_database(self):
        """Test overriding database parameter on a YAML scenario connection."""
        name = self._get_first_scenario_name()
        config = resolve_named_connection(
            f"rhosocial.activerecord_mariadb_test.feature.backend.named_connection.example_connections.{name}",
            {"database": "my_app"},
        )
        assert isinstance(config, MariaDBConnectionConfig)
        assert config.database == "my_app"

    def test_list_yaml_scenarios(self):
        """Test listing all YAML-loaded connections in example_connections."""
        connections = list_named_connections_in_module(
            "rhosocial.activerecord_mariadb_test.feature.backend.named_connection.example_connections"
        )
        assert len(connections) > 0
        for c in connections:
            assert isinstance(c["name"], str)
            assert c["name"] != ""

    def test_describe_yaml_scenario(self):
        """Test describing a YAML scenario named connection."""
        name = self._get_first_scenario_name()
        resolver = NamedConnectionResolver(
            f"rhosocial.activerecord_mariadb_test.feature.backend.named_connection.example_connections.{name}"
        ).load()
        info = resolver.describe()
        assert info["is_class"] is False
        assert "database" in info["parameters"]
        if info.get("config_preview"):
            assert "password" not in info["config_preview"]
