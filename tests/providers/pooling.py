# tests/providers/pooling.py
"""Database pooling helpers for the MariaDB test providers.

Under parallel (pytest-xdist) runs with a positive pool size the providers
reuse a per-worker pooled database ``{database}_{index}`` on the scenario's
MariaDB server instead of the shared scenario ``database`` schema, so scenario
variants of the same test can run concurrently on different workers without
conflicting. The pool name prefix is derived from the scenario's configured
``database`` (the YAML ``database`` field), so e.g. ``database: test_db``
produces pooled databases ``test_db_0``, ``test_db_1``, ... Serial runs (no
``-n``) keep the previous behaviour: the provider connects to the scenario's
configured ``database``.

The scenario name selects the server (host/port); the pool index selects the
database name. The two are deliberately unrelated.
"""

import mariadb

from rhosocial.activerecord.testsuite.core.pool import (
    pooled_database_name,
    register_base_database,
    register_pool_reset_handler,
)

from .scenarios import SCENARIO_MAP, get_scenario_raw

# Derive each scenario's pooled-database base name from its configured
# ``database`` (YAML ``database`` field). Registered at import time so any
# caller of pooled_database_name() / resolve_database_name() resolves names
# consistent with the scenario configuration.
for _scenario_name, _scenario_config in SCENARIO_MAP.items():
    register_base_database(_scenario_name, _scenario_config["database"])


def resolve_database_name(scenario_name: str):
    """
    Return the pooled database name (e.g. ``test_db_3``) used by a test for
    the given scenario, or ``None`` when pooling is inactive (callers then fall
    back to the scenario's configured database).
    """
    return pooled_database_name(scenario_name)


def _escape_identifier(name: str) -> str:
    """Escape a MySQL/MariaDB identifier for use inside backticks."""
    return name.replace("`", "``")


def _reset_mariadb_database(scenario_name: str, db_name: str) -> None:
    """Ensure the pooled database exists and is empty on the scenario's server.

    Connects to the server selected by ``scenario_name``, creates the pooled
    ``db_name`` database if missing, and drops all leftover tables so the test
    starts from a clean state. Errors are swallowed: a failed reset must not
    hide the underlying test failure.
    """
    if scenario_name not in SCENARIO_MAP:
        return
    _, config = get_scenario_raw(scenario_name)
    conn_kwargs = {
        "host": config.host,
        "port": config.port,
        "user": config.username,
        "password": config.password,
        "connection_timeout": 10,
        "autocommit": True,
    }
    if config.charset:
        conn_kwargs["init_command"] = f"SET NAMES {config.charset}"
    if hasattr(config, "ssl_disabled") and not config.ssl_disabled:
        conn_kwargs["ssl"] = True
        if hasattr(config, "tls_version") and config.tls_version:
            conn_kwargs["tls_version"] = config.tls_version
        if hasattr(config, "ssl_verify_cert") and config.ssl_verify_cert:
            conn_kwargs["ssl_verify_cert"] = config.ssl_verify_cert
        if hasattr(config, "ssl_verify_identity") and config.ssl_verify_identity:
            conn_kwargs["ssl_verify_identity"] = config.ssl_verify_identity
    try:
        conn = mariadb.connect(**conn_kwargs)
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{_escape_identifier(db_name)}` "
                    f"DEFAULT CHARACTER SET {config.charset or 'utf8mb4'}"
                )
                cursor.execute(f"USE `{_escape_identifier(db_name)}`")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                    (db_name,),
                )
                for (table,) in cursor.fetchall():
                    cursor.execute(f"DROP TABLE IF EXISTS `{_escape_identifier(table)}`")
            finally:
                cursor.close()
        finally:
            conn.close()
    except Exception:
        pass


register_pool_reset_handler(_reset_mariadb_database)
