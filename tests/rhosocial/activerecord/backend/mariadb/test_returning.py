import pytest
from unittest.mock import patch, MagicMock

from src.rhosocial.activerecord.backend.errors import ReturningNotSupportedError, QueryError, OperationalError
from src.rhosocial.activerecord.backend.impl.mysql.dialect import MySQLReturningHandler
from src.rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from src.rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBReturningHandler
from src.rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from src.rhosocial.activerecord.backend.typing import ConnectionConfig


def test_mysql_returning_not_supported():
    """Test RETURNING clause not supported in any MySQL version"""
    # Test with various MySQL versions
    for version in [(5, 7, 0), (8, 0, 0), (8, 0, 21), (8, 4, 0), (9, 2, 0)]:
        handler = MySQLReturningHandler(version)

        # Test is_supported property - should always be False for MySQL
        assert not handler.is_supported

        # Test format_clause raises ReturningNotSupportedError
        with pytest.raises(ReturningNotSupportedError) as exc_info:
            handler.format_clause()
        assert "MySQL does not support RETURNING" in str(exc_info.value)

        # Test with specific columns
        with pytest.raises(ReturningNotSupportedError) as exc_info:
            handler.format_clause(columns=["id", "name"])
        assert "MySQL does not support RETURNING" in str(exc_info.value)


def test_mariadb_returning_supported():
    """Test RETURNING clause supported in MariaDB 10.5+"""
    # Test with MariaDB versions before 10.5
    for version in [(10, 3, 0), (10, 4, 99)]:
        handler = MariaDBReturningHandler(version)

        # Test is_supported property
        assert not handler.is_supported

        # Test format_clause raises ReturningNotSupportedError
        with pytest.raises(ReturningNotSupportedError) as exc_info:
            handler.format_clause()
        assert "MariaDB version does not support RETURNING" in str(exc_info.value)

    # Test with MariaDB versions 10.5+
    for version in [(10, 5, 0), (10, 6, 0), (11, 0, 0)]:
        handler = MariaDBReturningHandler(version)

        # Test is_supported property
        assert handler.is_supported

        # Test single column
        result = handler.format_clause(columns=["id"])
        assert result == "RETURNING id"

        # Test multiple columns
        result = handler.format_clause(columns=["id", "name", "created_at"])
        assert result == "RETURNING id, name, created_at"

        # Test without columns (should return all columns)
        result = handler.format_clause()
        assert result == "RETURNING *"


@pytest.mark.mysql_version("any")
def test_mysql_backend_returning_not_supported(mysql_backend):
    """
    Test MySQL backend RETURNING functionality - should always fail
    as MySQL doesn't support RETURNING in any version.
    """
    # Test supports_returning property
    assert not mysql_backend.supports_returning

    # Test execute with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        mysql_backend.execute(
            "INSERT INTO users (name) VALUES (?)",
            params=("test",),
            returning=True
        )
    assert "MySQL does not support RETURNING" in str(exc_info.value)

    # Test insert with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        mysql_backend.insert(
            "users",
            {"name": "test"},
            returning=True
        )
    assert "MySQL does not support RETURNING" in str(exc_info.value)


@pytest.mark.mariadb_version("10.5+")
def test_mariadb_returning_with_columns(mariadb_backend):
    """
    Test MariaDB backend RETURNING functionality with specified columns.
    Uses MariaDB 10.5+ which supports RETURNING.
    """
    # Test supports_returning property
    assert mariadb_backend.supports_returning

    # Setup cursor behavior for create table
    if hasattr(mariadb_backend, '_connection') and hasattr(mariadb_backend._connection, 'cursor_mock'):
        cursor_mock = mariadb_backend._connection.cursor_mock
    else:
        pytest.skip("Test requires mock backend")

    # Create a test table
    mariadb_backend.execute("""
        CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            created_at TIMESTAMP
        )
    """)

    # Setup cursor behavior for insert with returning
    cursor_mock.fetchall.return_value = [{"id": 1, "name": "test"}]

    # Test insert with specific RETURNING columns
    result = mariadb_backend.insert(
        "users",
        {
            "name": "test",
            "email": "test@example.com",
            "created_at": "2024-02-11 10:00:00"
        },
        returning=True,
        returning_columns=["id", "name"]
    )
    assert result.data
    assert len(result.data) == 1
    assert "id" in result.data[0]
    assert "name" in result.data[0]
    assert result.data[0]["id"] == 1
    assert result.data[0]["name"] == "test"

# Add more tests for MariaDB RETURNING functionality