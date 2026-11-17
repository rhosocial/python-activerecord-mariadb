# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/conftest.py
"""L2 backend fixtures for the MariaDB native-type tests.

- ``database``: one database per directory (session scope, emptied at start);
- ``schema``: only the tables this module declares in ``TABLES``, dropped and
  recreated for every test (function scope), so each test starts from empty
  tables;
- one fixture per model, each configured against this directory's database.

A module declares what it needs and nothing else: the native ``UUID`` type
only exists from 10.7, so a directory-wide "create every family" would make a
``BIT`` test's setup fail on a server that lacks a table that test never
touches.
"""

from pathlib import Path

import pytest

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.native_capabilities import (
    supports_uuid,
    uuid_skip_reason,
)
from rhosocial.activerecord_mariadb_test.feature.backend.adapters.native.native_models import (
    NativeBitDefinition,
    NativeBitRow,
    NativeEnumDefinition,
    NativeEnumRow,
    NativeGeometryDefinition,
    NativeGeometryRow,
    NativeJsonDefinition,
    NativeJsonRow,
    NativeSetDefinition,
    NativeSetRow,
    NativeUuidDefinition,
    NativeUUIDRow,
    NativeYearDefinition,
    NativeYearRow,
)

from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    parallel=True,
    purpose="MariaDB backend tests (native) against the directory-owned database.",
    passes_means="the live-database contract of this directory holds on MariaDB",
    fails_means="the directory-owned database is corrupted or a backend behavior is wrong",
)

DDL = ExecutionOptions(stmt_type=StatementType.DDL)

#: Table name -> (definition, capability gate, skip reason for the gate).
#: A gate of ``None`` means the columns exist on every supported server; a
#: gate that answers ``no`` skips the module, and its reason names the probe.
FAMILIES = {
    "native_bit": (NativeBitDefinition, None, None),
    "native_set": (NativeSetDefinition, None, None),
    "native_enum": (NativeEnumDefinition, None, None),
    "native_year": (NativeYearDefinition, None, None),
    "native_json": (NativeJsonDefinition, None, None),
    "native_geometry": (NativeGeometryDefinition, None, None),
    "native_uuid": (NativeUuidDefinition, supports_uuid, uuid_skip_reason),
}


def _database_name() -> str:
    """Database name from this directory's namespace (below ``feature``)."""
    parts = Path(__file__).parent.parts
    start = parts.index("feature") + 1
    return "test_" + "_".join(parts[start:])


def _declared(request) -> tuple:
    """The families the module declares in ``TABLES``."""
    names = tuple(getattr(request.module, "TABLES", ()))
    unknown = [name for name in names if name not in FAMILIES]
    if unknown:
        raise LookupError(f"{request.module.__name__} declares unknown native families: {unknown}")
    return names


@pytest.fixture(scope="session")
def database_config(backend_scenario):
    """The scenario, its connection configuration, and the directory database name."""
    name = _database_name()
    return backend_scenario, backend_scenario.make_config(name), name


@pytest.fixture(scope="session")
def database(database_config):
    """The directory's database, prepared once and left for later files."""
    scenario, config, name = database_config
    scenario.reset_database(name)
    backend = scenario.backend_class(connection_config=config)
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()


@pytest.fixture(scope="function", autouse=True)
def schema(database, request):
    """Drop and recreate only the tables this module declares, before every test."""
    fixtures = []
    for name in _declared(request):
        definition, gate, reason = FAMILIES[name]
        if gate is not None and not gate(database.dialect):
            pytest.skip(reason(database.dialect))
        fixtures.append(definition(database.dialect))
    for fixture in fixtures:
        database.execute(*fixture.create_table.to_sql(), options=DDL)
    yield
    for fixture in reversed(fixtures):
        database.execute(*fixture.drop_table.to_sql(), options=DDL)


@pytest.fixture(name="native_bit")
def native_bit(database_config):
    """``NativeBitRow`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeBitRow.configure(config, scenario.backend_class)
    yield NativeBitRow
    NativeBitRow.backend().disconnect()


@pytest.fixture(name="native_set")
def native_set(database_config):
    """``NativeSetRow`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeSetRow.configure(config, scenario.backend_class)
    yield NativeSetRow
    NativeSetRow.backend().disconnect()


@pytest.fixture(name="native_enum")
def native_enum(database_config):
    """``NativeEnumRow`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeEnumRow.configure(config, scenario.backend_class)
    yield NativeEnumRow
    NativeEnumRow.backend().disconnect()


@pytest.fixture(name="native_year")
def native_year(database_config):
    """``NativeYearRow`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeYearRow.configure(config, scenario.backend_class)
    yield NativeYearRow
    NativeYearRow.backend().disconnect()


@pytest.fixture(name="native_json")
def native_json(database_config):
    """``NativeJsonRow`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeJsonRow.configure(config, scenario.backend_class)
    yield NativeJsonRow
    NativeJsonRow.backend().disconnect()


@pytest.fixture(name="native_geometry")
def native_geometry(database_config):
    """``NativeGeometryRow`` configured against this directory's database."""
    scenario, config, _name = database_config
    NativeGeometryRow.configure(config, scenario.backend_class)
    yield NativeGeometryRow
    NativeGeometryRow.backend().disconnect()


@pytest.fixture(name="native_uuid")
def native_uuid(database_config, database):
    """``NativeUUIDRow``, skipped when the server has no native ``UUID`` type."""
    if not supports_uuid(database.dialect):
        pytest.skip(uuid_skip_reason(database.dialect))
    scenario, config, _name = database_config
    NativeUUIDRow.configure(config, scenario.backend_class)
    yield NativeUUIDRow
    NativeUUIDRow.backend().disconnect()
