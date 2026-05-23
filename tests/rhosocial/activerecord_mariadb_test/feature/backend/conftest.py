# tests/rhosocial/activerecord_mariadb_test/feature/backend/conftest.py
"""
Pytest fixtures for MariaDB backend tests.

This module provides fixtures for testing MariaDB backend functionality
including introspection, SHOW commands, and CRUD operations.
"""
import os
import pytest
import pytest_asyncio
import yaml
from typing import Dict, Any, Tuple, Type

from rhosocial.activerecord.backend.impl.mariadb import (
    MariaDBBackend,
    AsyncMariaDBBackend,
    MariaDBConnectionConfig,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

# --- Scenario Loading Logic ---

SCENARIO_MAP: Dict[str, Dict[str, Any]] = {}


def register_scenario(name: str, config: Dict[str, Any]):
    SCENARIO_MAP[name] = config


def _load_scenarios_from_config():
    """
    Load scenarios from a configuration file with the following priority:
    1. Environment variable specified path (highest priority)
    2. Default path tests/config/mariadb_scenarios.yaml (lowest priority)
    If no valid configuration file is found, use default configuration.
    """
    config_path = None
    env_config_path = os.getenv("MARIADB_SCENARIOS_CONFIG_PATH")

    if env_config_path and os.path.exists(env_config_path):
        print(f"Loading MariaDB scenarios from environment-specified path: {env_config_path}")
        config_path = env_config_path

    if not config_path:
        # Try multiple possible default paths
        default_paths = [
            os.path.join(os.path.dirname(__file__), "../../../../config", "mariadb_scenarios.yaml"),
            os.path.join(os.path.dirname(__file__), "../../../../../config", "config.yml"),
            os.path.join(os.path.dirname(__file__), "../../../../../config", "mariadb_scenarios.yaml"),
        ]
        for path in default_paths:
            if os.path.exists(path):
                config_path = path
                break

    if not config_path:
        # Use default configuration if no file found
        print("No MariaDB scenarios configuration file found, using default configuration")
        register_scenario('default', {
            'host': '127.0.0.1',
            'port': 3307,
            'database': 'test',
            'username': 'root',
            'password': '',
        })
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # Handle both 'scenarios' and 'databases.mariadb.versions' formats
        if 'scenarios' in config_data:
            for scenario_name, config in config_data['scenarios'].items():
                register_scenario(scenario_name, config)
        elif 'databases' in config_data and 'mariadb' in config_data['databases']:
            versions = config_data['databases']['mariadb'].get('versions', [])
            for i, version_config in enumerate(versions):
                label = version_config.get('label', f"mariadb_{i}")
                register_scenario(label, version_config)
        else:
            # Use the entire config as a single scenario
            register_scenario('default', config_data)

        _apply_scenario_filter()

    except ImportError:
        raise ImportError("PyYAML is required to load MariaDB scenario configuration files")


def _apply_scenario_filter():
    """Filter SCENARIO_MAP based on MARIADB_ACTIVE_SCENARIOS env var.

    The env var is set by the --scenarios pytest option in the root conftest.
    It contains comma-separated full scenario names (e.g., "mariadb_102,mariadb_122").
    """
    filter_str = os.getenv("MARIADB_ACTIVE_SCENARIOS")
    if not filter_str:
        return

    allowed = set(s.strip() for s in filter_str.split(',') if s.strip())
    if not allowed:
        return

    to_remove = [name for name in SCENARIO_MAP if name not in allowed]
    for name in to_remove:
        del SCENARIO_MAP[name]

    if to_remove:
        print(f"Filtered scenarios: kept {list(SCENARIO_MAP.keys())}, "
              f"removed {to_remove} (--scenarios={filter_str})")


_load_scenarios_from_config()


def get_scenario(name: str) -> Tuple[Type[MariaDBBackend], MariaDBConnectionConfig]:
    if name not in SCENARIO_MAP:
        if SCENARIO_MAP:
            name = next(iter(SCENARIO_MAP))
        else:
            raise ValueError("No scenarios registered")
    scenario_config = SCENARIO_MAP[name].copy()
    config = MariaDBConnectionConfig(**scenario_config)
    return MariaDBBackend, config


def get_enabled_scenarios() -> Dict[str, Any]:
    return SCENARIO_MAP


# --- Provider Logic ---

class BackendFeatureProvider:
    def __init__(self):
        self._backend = None
        self._async_backend = None

    def setup_backend(self, scenario_name: str):
        if self._backend:
            return self._backend
        backend_class, config = get_scenario(scenario_name)
        self._backend = backend_class(connection_config=config)
        self._backend.connect()
        self._backend.introspect_and_adapt()
        return self._backend

    async def setup_async_backend(self, scenario_name: str):
        if self._async_backend:
            return self._async_backend
        _, config = get_scenario(scenario_name)
        self._async_backend = AsyncMariaDBBackend(connection_config=config)
        await self._async_backend.connect()
        await self._async_backend.introspect_and_adapt()
        return self._async_backend

    def cleanup(self):
        if self._backend:
            self._backend.disconnect()
            self._backend = None

    async def async_cleanup(self):
        if self._async_backend:
            await self._async_backend.disconnect()
            self._async_backend = None


# --- Fixtures ---

def get_scenario_names():
    return list(get_enabled_scenarios().keys())


@pytest.fixture(scope="function", params=get_scenario_names())
def mariadb_backend(request):
    """Parameterized fixture providing MariaDB backend for each scenario."""
    scenario_name = request.param
    provider = BackendFeatureProvider()
    backend = provider.setup_backend(scenario_name)
    yield backend
    provider.cleanup()


@pytest.fixture(scope="function")
def mariadb_backend_single():
    """Non-parameterized fixture using the first available scenario.

    Use this for tests whose results do not vary across database versions.
    In --scenario-parallel mode, tests using this fixture are automatically
    pinned to the first scenario's worker to avoid table conflicts.
    """
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MariaDB scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = provider.setup_backend(scenario_name)
    yield backend
    provider.cleanup()


@pytest_asyncio.fixture(scope="function", params=get_scenario_names())
async def async_mariadb_backend(request):
    """Parameterized async fixture providing MariaDB backend for each scenario."""
    scenario_name = request.param
    provider = BackendFeatureProvider()
    backend = await provider.setup_async_backend(scenario_name)
    yield backend
    await provider.async_cleanup()


@pytest.fixture(scope="function")
def mariadb_control_backend(mariadb_backend):
    """Dedicated control backend sharing the same connection config as mariadb_backend.

    This fixture provides an independent backend instance for operations that
    need to control or interfere with the main test backend, such as:
    - KILL CONNECTION statements
    - Setting global variables
    - Monitoring other connections

    Automatically follows the same scenario parametrization as mariadb_backend.
    """
    backend = MariaDBBackend(connection_config=mariadb_backend.config)
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()


@pytest_asyncio.fixture(scope="function")
async def async_mariadb_control_backend(async_mariadb_backend):
    """Dedicated async control backend that connects to the same scenario as async_mariadb_backend.

    This fixture provides an independent async backend instance for operations that
    need to control or interfere with the main test backend, such as:
    - KILL CONNECTION statements
    - Setting global variables
    - Monitoring other connections

    Automatically follows the same scenario parametrization as async_mariadb_backend.
    """
    backend = AsyncMariaDBBackend(connection_config=async_mariadb_backend.config)
    await backend.connect()
    await backend.introspect_and_adapt()
    yield backend
    await backend.disconnect()


@pytest_asyncio.fixture(scope="function")
async def async_mariadb_backend_single():
    """Non-parameterized async fixture using the first available scenario.

    Use this for tests whose results do not vary across database versions.
    In --scenario-parallel mode, tests using this fixture are automatically
    pinned to the first scenario's worker to avoid table conflicts.
    """
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MariaDB scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = await provider.setup_async_backend(scenario_name)
    yield backend
    await provider.async_cleanup()


@pytest.fixture(scope="function")
def mariadb_dialect():
    """Fixture providing a MariaDBDialect instance for unit tests."""
    return MariaDBDialect(version=(10, 6, 0))


# --- Type Adapters ---

@pytest.fixture(scope="module")
def json_column_adapter():
    """
    Module-scoped fixture providing MariaDBJSONAdapter instance.

    This adapter can be used with column_adapters parameter to automatically
    parse JSON columns returned as strings by mariadb connector.

    Usage:
        result = mariadb_backend.execute(
            "SELECT data FROM table",
            column_adapters={'data': (json_column_adapter, dict)}
        )
    """
    from rhosocial.activerecord.backend.impl.mariadb.adapters import MariaDBJSONAdapter
    return MariaDBJSONAdapter()
