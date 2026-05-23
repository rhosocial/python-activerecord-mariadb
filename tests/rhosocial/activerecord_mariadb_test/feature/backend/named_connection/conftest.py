# tests/rhosocial/activerecord_mariadb_test/feature/backend/named_connection/conftest.py
"""
Test fixtures for MariaDB named connection tests.
"""
import types
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_backend_cls():
    """Create a mock backend class for testing."""
    return MagicMock(name="MockMariaDBBackend")


@pytest.fixture
def connection_module():
    """Create a test module with named connections."""
    from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

    module = types.ModuleType("test_mariadb_connections")

    def dev_db(backend_cls, database: str = "test_db"):
        return MariaDBConnectionConfig(
            host="localhost",
            port=3306,
            database=database,
            username="root",
            password="password",
        )

    module.dev_db = dev_db
    return module


class TestCliArgs:
    """Helper class to create mock CLI args for testing."""

    @staticmethod
    def create(named_connection: str = None, **kwargs):
        """Create a mock args namespace."""
        from argparse import Namespace

        defaults = {
            "named_connection": named_connection,
            "connection_params": [],
        }
        defaults.update(kwargs)
        return Namespace(**defaults)
