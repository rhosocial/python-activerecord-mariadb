from unittest.mock import patch, MagicMock
import pytest

from src.rhosocial.activerecord.backend.errors import ReturningNotSupportedError
from src.rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from src.rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBReturningHandler
from src.rhosocial.activerecord.backend.typing import ConnectionConfig


def test_returning_support_detection():
    """Test RETURNING clause support detection based on version"""
    # Test with different MariaDB versions
    versions = [(10, 3, 0), (10, 4, 0), (10, 5, 0), (10, 5, 1), (10, 6, 0)]

    for version in versions:
        handler = MariaDBReturningHandler(version)

        # MariaDB 10.5+ should support RETURNING
        if version >= (10, 5, 0):
            assert handler.is_supported, f"MariaDB {version} should support RETURNING"
        else:
            assert not handler.is_supported, f"MariaDB {version} should not support RETURNING"


def test_returning_format_clause():
    """Test RETURNING clause formatting"""
    # Create a handler for MariaDB 10.5+
    handler = MariaDBReturningHandler((10, 5, 0))

    # Test basic RETURNING with no columns (should return all columns)
    assert handler.format_clause() == "RETURNING *"

    # Test RETURNING with specific columns
    assert handler.format_clause(["id", "name"]) == "RETURNING id, name"

    # Test with quoted column names
    assert handler.format_clause(["`id`", "`name`"]) == "RETURNING id, name"

    # Test with complex column names
    assert handler.format_clause(["user.id", "user name"]) == "RETURNING `user.id`, `user name`"


def test_returning_not_supported_error():
    """Test ReturningNotSupportedError is raised for older versions"""
    # Create handler for MariaDB 10.4 (which doesn't support RETURNING)
    handler = MariaDBReturningHandler((10, 4, 0))

    # Verify format_clause raises error
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        handler.format_clause()
    assert "MariaDB version does not support RETURNING" in str(exc_info.value)


@pytest.fixture
def mock_mariadb_backend():
    """Create mock MariaDB backend with specific version"""
    config = ConnectionConfig(host="localhost", database="test", username="test", password="test")

    # Test both with version that supports and doesn't support RETURNING
    backends = []
    for version in [(10, 4, 0), (10, 5, 0)]:
        config.version = version

        # Create mock backend
        with patch("mariadb.connect") as mock_connect:
            conn_mock = MagicMock()
            cursor_mock = MagicMock()
            conn_mock.cursor.return_value = cursor_mock
            mock_connect.return_value = conn_mock

            backend = MariaDBBackend(connection_config=config)
            backend._connection = conn_mock
            backend._server_version_cache = version

            # Add cursor_mock for test access
            conn_mock.cursor_mock = cursor_mock

            backends.append(backend)

    return backends


def test_backend_returning_support(mock_mariadb_backend):
    """Test MariaDB backend RETURNING functionality based on version"""
    # Test with MariaDB 10.4 (shouldn't support RETURNING)
    backend_10_4 = mock_mariadb_backend[0]
    # Test with MariaDB 10.5 (should support RETURNING)
    backend_10_5 = mock_mariadb_backend[1]

    # Check supports_returning property
    assert not backend_10_4.supports_returning
    assert backend_10_5.supports_returning

    # Test execute with RETURNING on version that doesn't support it
    with pytest.raises(ReturningNotSupportedError):
        backend_10_4.execute(
            "INSERT INTO users (name) VALUES (?)",
            params=("test",),
            returning=True
        )

    # Test insert with RETURNING on version that doesn't support it
    with pytest.raises(ReturningNotSupportedError):
        backend_10_4.insert(
            "users",
            {"name": "test"},
            returning=True
        )


def test_returning_version_specific_behavior(mock_mariadb_backend):
    """Test version-specific behavior for RETURNING clause"""
    backend_10_5 = mock_mariadb_backend[1]  # MariaDB 10.5

    # Setup mock cursor to return data for RETURNING clause
    cursor_mock = backend_10_5._connection.cursor_mock
    cursor_mock.fetchall.return_value = [{"id": 1, "name": "test"}]

    # Should be able to use RETURNING with MariaDB 10.5+
    try:
        result = backend_10_5.insert(
            "users",
            {"name": "test"},
            returning=True
        )
        # Verify RETURNING data is returned
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["id"] == 1
    except ReturningNotSupportedError:
        pytest.fail("RETURNING should be supported in MariaDB 10.5+")