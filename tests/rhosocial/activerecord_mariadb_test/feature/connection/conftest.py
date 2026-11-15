# tests/rhosocial/activerecord_mariadb_test/feature/connection/conftest.py
"""
Pytest configuration for connection pool tests.

This module provides fixtures for testing connection pools with MariaDB backends.
"""

import os
from typing import Dict, Any, Generator

import pytest
import pytest_asyncio
import yaml

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.backend.async_backend import AsyncMariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.connection.pool import (
    PoolConfig,
    BackendPool,
    AsyncBackendPool,
)

from pool_definitions import (
    AsyncConcurrentTestPostsDefinition,
    AsyncConcurrentTestUsersDefinition,
    ConcurrentTestPostsDefinition,
    ConcurrentTestUsersDefinition,
)


def resolve_database_name(scenario_name: str) -> str:
    """Name the database these pool tests own on each scenario's server."""
    return f"test_connection_{scenario_name}"


# No event loop workaround is needed on Windows. This backend's async driver
# (mariadb-connector-python) talks over asyncio streams, which the platform's
# default ProactorEventLoop serves natively; only a driver that registers the
# socket with the loop itself (the way psycopg does) requires a selector
# loop. A `WindowsSelectorEventLoopPolicy` switch used to sit here, copied
# from the postgres suite -- it is deprecated for removal in Python 3.16, and
# switching it would take asyncio subprocess and pipe I/O down with it. Do
# not reintroduce it: if a future driver needs a selector loop, follow the
# postgres suite's pytest_asyncio_loop_factories hook instead, which scopes
# the choice to the tests rather than the process.

# --- Scenario Loading Logic ---

SCENARIO_MAP: Dict[str, Dict[str, Any]] = {}


def register_scenario(name: str, config: Dict[str, Any]):
    SCENARIO_MAP[name] = config


def _load_scenarios_from_config():
    """Load scenarios from a configuration file."""
    config_path = None
    env_config_path = os.getenv("MARIADB_SCENARIOS_CONFIG_PATH")

    if env_config_path and os.path.exists(env_config_path):
        config_path = env_config_path
    else:
        default_path = os.path.join(
            os.path.dirname(__file__), "../../../../config", "mariadb_scenarios.yaml"
        )
        if os.path.exists(default_path):
            config_path = default_path
        elif env_config_path:
            print(
                f"Warning: Scenario file specified in MARIADB_SCENARIOS_CONFIG_PATH not found: {env_config_path}"
            )
            return

    if not config_path:
        raise FileNotFoundError(
            "No MariaDB scenarios configuration file found. "
            "Set MARIADB_SCENARIOS_CONFIG_PATH or place mariadb_scenarios.yaml in tests/config."
        )

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if "scenarios" not in config_data:
            raise ValueError(f"Configuration file {config_path} does not contain 'scenarios' key")

        for scenario_name, config in config_data["scenarios"].items():
            if config:
                register_scenario(scenario_name, config)

    except ImportError:
        raise ImportError("PyYAML is required to load scenario configuration files")  # noqa: B904


_load_scenarios_from_config()

from support.mariadb import scenario as _support_scenario

_PREPARED_DATABASES = set()


def get_scenario_config(name: str) -> Dict[str, Any]:
    if name not in SCENARIO_MAP:
        if SCENARIO_MAP:
            name = next(iter(SCENARIO_MAP))
        else:
            raise ValueError("No scenarios registered or enabled")
    scenario_config = SCENARIO_MAP[name].copy()
    # Apply the pooled database name so parallel workers never share a schema.
    pooled_db = resolve_database_name(name)
    if pooled_db:
        scenario_config["database"] = pooled_db
        if pooled_db not in _PREPARED_DATABASES:
            _support_scenario(name).reset_database(pooled_db)
            _PREPARED_DATABASES.add(pooled_db)
    return scenario_config


def get_scenario_names():
    return list(SCENARIO_MAP.keys())


# --- Pool Fixtures ---


def create_mysql_backend_factory(config_dict: Dict[str, Any]):
    """Create a factory function that produces MariaDBBackend instances."""

    def factory():
        config_copy = config_dict.copy()
        ssl_disabled = config_copy.pop("ssl_disabled", None)
        config = MariaDBConnectionConfig(**config_copy)
        if ssl_disabled is not None:
            config.ssl_disabled = ssl_disabled
        backend = MariaDBBackend(connection_config=config)
        backend.connect()
        return backend

    return factory


def create_async_mysql_backend_factory(config_dict: Dict[str, Any]):
    """Create a factory function that produces AsyncMariaDBBackend instances."""

    def factory():
        config_copy = config_dict.copy()
        ssl_disabled = config_copy.pop("ssl_disabled", None)
        config = MariaDBConnectionConfig(**config_copy)
        if ssl_disabled is not None:
            config.ssl_disabled = ssl_disabled
        backend = AsyncMariaDBBackend(connection_config=config)
        # Note: connect() will be called by the pool when needed
        return backend

    return factory


@pytest.fixture(scope="function")
def mariadb_pool(database_config) -> Generator[BackendPool, None, None]:
    """Create a BackendPool with MariaDB backends for testing."""
    scenario_name = database_config[0].name
    config_dict = get_scenario_config(scenario_name)

    pool_config = PoolConfig(
        min_size=1,
        max_size=5,
        timeout=30.0,
        validate_on_borrow=True,
        validation_query="SELECT 1",
        backend_factory=create_mysql_backend_factory(config_dict),
    )

    pool = BackendPool.create(pool_config)
    yield pool
    pool.close(timeout=5.0, force=True)


@pytest_asyncio.fixture(scope="function")
async def async_mariadb_pool(database_config) -> AsyncBackendPool:
    """Create an AsyncBackendPool with MariaDB backends for testing."""
    scenario_name = database_config[0].name
    config_dict = get_scenario_config(scenario_name)

    pool_config = PoolConfig(
        min_size=1,
        max_size=5,
        timeout=30.0,
        validate_on_borrow=True,
        validation_query="SELECT 1",
        backend_factory=create_async_mysql_backend_factory(config_dict),
    )

    pool = await AsyncBackendPool.create(pool_config)
    yield pool
    await pool.close(timeout=5.0, force=True)


@pytest.fixture(scope="function")
def mariadb_pool_large(database_config) -> Generator[BackendPool, None, None]:
    """Create a larger BackendPool for stress testing."""
    scenario_name = database_config[0].name
    config_dict = get_scenario_config(scenario_name)

    pool_config = PoolConfig(
        min_size=1,
        max_size=5,
        timeout=60.0,
        validate_on_borrow=False,  # Faster for stress tests
        backend_factory=create_mysql_backend_factory(config_dict),
    )

    pool = BackendPool.create(pool_config)
    yield pool
    pool.close(timeout=5.0, force=True)


@pytest_asyncio.fixture(scope="function")
async def async_mariadb_pool_large(database_config) -> AsyncBackendPool:
    """Create a larger AsyncBackendPool for stress testing."""
    scenario_name = database_config[0].name
    config_dict = get_scenario_config(scenario_name)

    pool_config = PoolConfig(
        min_size=1,
        max_size=5,
        timeout=60.0,
        validate_on_borrow=False,
        backend_factory=create_async_mysql_backend_factory(config_dict),
    )

    pool = await AsyncBackendPool.create(pool_config)
    yield pool
    await pool.close(timeout=5.0, force=True)


# --- Table Setup Fixtures ---


@pytest.fixture(scope="function")
def mariadb_pool_with_tables(mariadb_pool: BackendPool) -> Generator[BackendPool, None, None]:
    """Create a pool with test tables initialized."""
    definitions = (
        ConcurrentTestPostsDefinition,
        ConcurrentTestUsersDefinition,
    )
    with mariadb_pool.connection() as backend:
        fixtures = [definition(backend.dialect) for definition in definitions]
        for fixture in fixtures:
            backend.execute(*fixture.drop_table.to_sql())
            backend.execute(*fixture.create_table.to_sql())

    yield mariadb_pool

    with mariadb_pool.connection() as backend:
        for fixture in reversed(fixtures):
            backend.execute(*fixture.drop_table.to_sql())


@pytest_asyncio.fixture(scope="function")
async def async_mariadb_pool_with_tables(async_mariadb_pool: AsyncBackendPool) -> AsyncBackendPool:
    """Create an async pool with test tables initialized."""
    definitions = (
        AsyncConcurrentTestPostsDefinition,
        AsyncConcurrentTestUsersDefinition,
    )
    async with async_mariadb_pool.connection() as backend:
        fixtures = [definition(backend.dialect) for definition in definitions]
        for fixture in fixtures:
            await backend.execute(*fixture.drop_table.to_sql())
            await backend.execute(*fixture.create_table.to_sql())

    yield async_mariadb_pool

    async with async_mariadb_pool.connection() as backend:
        for fixture in reversed(fixtures):
            await backend.execute(*fixture.drop_table.to_sql())


# --- directory contract: this directory's identity for xdist grouping ---
@pytest.fixture(scope="session")
def database_config(backend_scenario):
    """The scenario, its connection configuration, and the directory name.

    The pool fixtures above own their databases (``test_connection_{scenario}``)
    and are deliberately left unchanged, so this directory does not create a
    shared ``database`` backend.  The fixture declares which directory and
    scenario the tests belong to, which is what keeps a directory's tests on one
    worker per scenario.
    """
    name = "test_connection"
    return backend_scenario, backend_scenario.make_config(name), name
