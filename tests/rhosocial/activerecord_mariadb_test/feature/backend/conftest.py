# tests/rhosocial/activerecord_mariadb_test/feature/backend/conftest.py
"""Fixtures for the backend-owned tests.

The backend runs these against a real server. The scenario supplies the
connection parameters; the database name is derived from the directory that
owns the test, so two directories never share tables.
"""
import os
from typing import Any, Dict, Tuple, Type

import pytest
import pytest_asyncio

import support.mariadb

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.backend.async_backend import AsyncMariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.mixins.introspection import SEQUENCES_SINCE

# --- Scenario Loading Logic ---

SCENARIO_MAP: Dict[str, Dict[str, Any]] = dict(support.mariadb.SCENARIO_MAP)


def _apply_scenario_filter():
    """Filter SCENARIO_MAP based on the active scenarios env var.

    Keeps the backend-feature scenarios consistent with the scenarios active
    for the rest of the test run.
    """
    filter_str = os.getenv(
        "MARIADB_ACTIVE_SCENARIOS"
    ) or os.getenv("TESTSUITE_ACTIVE_SCENARIOS")
    if not filter_str:
        return
    allowed = set(s.strip() for s in filter_str.split(",") if s.strip())
    if not allowed:
        return
    for name in [n for n in SCENARIO_MAP if n not in allowed]:
        del SCENARIO_MAP[name]


_apply_scenario_filter()


def get_enabled_scenarios() -> Dict[str, Any]:
    return SCENARIO_MAP


def get_scenario_names():
    return list(get_enabled_scenarios().keys())


_PREPARED_DATABASES = set()


def _database_for(request) -> str:
    """Derive the logical database the directory owning the test runs in."""
    parts = list(request.node.path.parts)
    try:
        index = max(i for i, part in enumerate(parts) if part == "backend")
        names = [part for part in parts[index + 1 : -1] if part]
        return "test_backend" + "".join("_" + name for name in names)
    except ValueError:
        if "feature" in parts:
            index = max(i for i, part in enumerate(parts) if part == "feature")
            names = [part for part in parts[index + 1 : -1] if part]
            return "test_" + "_".join(names) if names else "test_misc"
        return "test_backend"


def _prepare_database(scenario_name: str, database: str) -> None:
    """Create the directory's database once per scenario."""
    key = (scenario_name, database)
    if key in _PREPARED_DATABASES:
        return
    support.mariadb.scenario(scenario_name).reset_database(database)
    _PREPARED_DATABASES.add(key)


def get_scenario(
    name: str, database: str = "test_backend"
) -> Tuple[Type[MariaDBBackend], MariaDBConnectionConfig]:
    if name not in SCENARIO_MAP:
        if SCENARIO_MAP:
            name = next(iter(SCENARIO_MAP))
        else:
            raise ValueError("No scenarios registered")
    _prepare_database(name, database)
    return MariaDBBackend, support.mariadb.scenario(name).make_config(database)


def pytest_collection_modifyitems(config, items):
    """Pin a backend directory's tests to one worker.

    These directories create and drop tables in the directory's own database,
    so two workers must never run tests from the same directory at once.
    """
    for item in items:
        parts = item.path.parts
        if "backend" not in parts:
            continue
        item.add_marker(
            pytest.mark.xdist_group("mariadb-backend::" + str(item.path.parent))
        )


# --- Provider Logic ---


class BackendFeatureProvider:
    def __init__(self):
        self._backend = None
        self._async_backend = None

    def setup_backend(self, scenario_name: str, database: str):
        if self._backend:
            return self._backend
        backend_class, config = get_scenario(scenario_name, database)
        self._backend = backend_class(connection_config=config)
        self._backend.connect()
        self._backend.introspect_and_adapt()
        return self._backend

    async def setup_async_backend(self, scenario_name: str, database: str):
        if self._async_backend:
            return self._async_backend
        _, config = get_scenario(scenario_name, database)
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


@pytest.fixture(scope="function", params=get_scenario_names())
def mariadb_backend(request):
    """Parameterized fixture providing MariaDB backend for each scenario."""
    scenario_name = request.param
    provider = BackendFeatureProvider()
    backend = provider.setup_backend(scenario_name, _database_for(request))
    yield backend
    provider.cleanup()


@pytest.fixture(scope="function")
def mariadb_backend_single(request):
    """Non-parameterized fixture using the first available scenario.

    Use this for tests whose results do not vary across database versions.
    """
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MariaDB scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = provider.setup_backend(scenario_name, _database_for(request))
    yield backend
    provider.cleanup()


@pytest_asyncio.fixture(scope="function", params=get_scenario_names())
async def async_mariadb_backend(request):
    """Parameterized async fixture providing MariaDB backend for each scenario."""
    scenario_name = request.param
    provider = BackendFeatureProvider()
    backend = await provider.setup_async_backend(
        scenario_name, _database_for(request)
    )
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
async def async_mariadb_backend_single(request):
    """Non-parameterized async fixture using the first available scenario.

    Use this for tests whose results do not vary across database versions.
    """
    scenario_names = get_scenario_names()
    if not scenario_names:
        pytest.skip("No MariaDB scenarios configured")
    scenario_name = scenario_names[0]
    provider = BackendFeatureProvider()
    backend = await provider.setup_async_backend(
        scenario_name, _database_for(request)
    )
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


# --- sequence fixtures shared by introspection and CLI ---------------------

_SEQUENCE_SQL = """
    DROP SEQUENCE IF EXISTS intro_seq;
    CREATE SEQUENCE intro_seq
        START WITH 10 INCREMENT BY 2
        MINVALUE 5 MAXVALUE 100
        CYCLE;
"""

_CLEANUP_SEQUENCE_SQL = """
    DROP SEQUENCE IF EXISTS intro_seq;
"""

#: MariaDB gained sequences in 10.3. Below that the statements above are a
#: syntax error, not an empty answer, so the fixtures skip instead of poisoning
#: the run: ``DROP SEQUENCE``/``CREATE SEQUENCE`` do not exist to be optional.
#: ``SEQUENCES_SINCE`` is the mixin's own constant and the one the introspector
#: gates on, so the test and the code under test read the same line.
MIN_MARIADB_FOR_SEQUENCES = SEQUENCES_SINCE


def _has_sequences(backend) -> bool:
    """Whether this server can create a sequence at all.

    Read from the backend's own version tuple rather than a scenario name, so
    the answer follows the connection the fixture actually holds.
    """
    version = getattr(backend, "_version", None) or (0, 0, 0)
    return tuple(version[:3]) >= SEQUENCES_SINCE


def _require_sequences(backend) -> None:
    """Skip the calling test when this server predates sequences.

    A skip rather than an error: the question the test asks is unanswerable on
    this server, which is different from the code being wrong.
    """
    if not _has_sequences(backend):
        pytest.skip(
            "MariaDB {} has no sequences (they arrived in {})".format(
                ".".join(str(p) for p in (getattr(backend, "_version", None) or (0, 0, 0))[:3]),
                ".".join(str(p) for p in SEQUENCES_SINCE),
            )
        )


# A sequence is a table, so it lands in information_schema.TABLES beside the
# base tables -- the same list table options reads.
_SEQUENCE_TABLE_SQL = _SEQUENCE_SQL + """
    CREATE TABLE IF NOT EXISTS intro_options (
        id INT AUTO_INCREMENT PRIMARY KEY,
        note VARCHAR(64) NOT NULL
    ) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;
"""

_CLEANUP_SEQUENCE_TABLE_SQL = """
    DROP TABLE IF EXISTS intro_options;
""" + _CLEANUP_SEQUENCE_SQL


@pytest.fixture(scope="function")
def backend_with_sequence(mariadb_backend):
    """Fixture providing backend with a sequence that states its own limits."""
    _require_sequences(mariadb_backend)
    mariadb_backend.introspector.clear_cache()
    mariadb_backend.executescript(_SEQUENCE_SQL)
    yield mariadb_backend
    try:
        mariadb_backend.introspector.clear_cache()
        mariadb_backend.executescript(_CLEANUP_SEQUENCE_SQL)
    except Exception:
        pass


@pytest_asyncio.fixture(scope="function")
async def async_backend_with_sequence(async_mariadb_backend):
    """Async fixture providing backend with a sequence."""
    _require_sequences(async_mariadb_backend)
    async_mariadb_backend.introspector.clear_cache()
    await async_mariadb_backend.executescript(_SEQUENCE_SQL)
    yield async_mariadb_backend
    try:
        async_mariadb_backend.introspector.clear_cache()
        await async_mariadb_backend.executescript(_CLEANUP_SEQUENCE_SQL)
    except Exception:
        pass
