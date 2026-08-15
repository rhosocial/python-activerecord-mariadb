# src/rhosocial/activerecord/backend/impl/mariadb/examples/named_connections/development.py
"""Development environment connection examples."""

from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


def local_dev():
    """Local development MariaDB database connection.

    Connects to localhost with default credentials.
    Useful for local development and testing.

    Returns:
        MariaDBConnectionConfig: Development database configuration.
    """
    return MariaDBConnectionConfig(
        host="localhost",
        port=3306,
        user="root",
        database="dev",
        autocommit=True,
        init_command=None,
    )


def local_dev_no_auth():
    """Local MariaDB connection without authentication.

    For MariaDB installations that don't require passwords.

    Returns:
        MariaDBConnectionConfig: No-auth database configuration.
    """
    return MariaDBConnectionConfig(
        host="localhost",
        port=3306,
        user="root",
        password="",
        database="dev",
        autocommit=True,
        init_command=None,
    )


def test_db():
    """Test database connection.

    Returns:
        MariaDBConnectionConfig: Test database configuration.
    """
    return MariaDBConnectionConfig(
        host="localhost",
        port=3306,
        user="root",
        database="test",
        autocommit=True,
        get_warnings=True,
    )