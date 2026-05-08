# src/rhosocial/activerecord/backend/impl/mariadb/examples/named_connections/production.py
"""Production environment connection examples."""

from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


def prod_db():
    """Production MariaDB database connection.

    Connects to production database server with SSL enabled.

    Returns:
        MariaDBConnectionConfig: Production database configuration.
    """
    return MariaDBConnectionConfig(
        host="prod-mariadb.example.com",
        port=3306,
        user="app_user",
        database="production",
        autocommit=True,
        init_command="SET sql_mode='STRICT_TRANS_TABLES'",
        ssl_enabled=True,
    )


def prod_db_ssl():
    """Production MariaDB database with full SSL verification.

    Uses SSL with certificate verification for secure
    production connections.

    Returns:
        MariaDBConnectionConfig: SSL-verified database configuration.
    """
    return MariaDBConnectionConfig(
        host="prod-mariadb.example.com",
        port=3306,
        user="app_user",
        database="production",
        autocommit=True,
        init_command="SET sql_mode='STRICT_TRANS_TABLES'",
        ssl_enabled=True,
        ssl_verify_server_cert=True,
    )


def prod_replica():
    """Production MariaDB read replica connection.

    For read-heavy workloads, connect to a read replica
    to distribute load.

    Returns:
        MariaDBConnectionConfig: Read replica database configuration.
    """
    return MariaDBConnectionConfig(
        host="prod-mariadb-replica.example.com",
        port=3306,
        user="app_user",
        database="production",
        autocommit=True,
    )