# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/conftest.py
"""L2 backend fixtures for the MariaDB native-type tests.

- ``database``: one database per directory (session scope, emptied at start);
- ``schema``: the native family tables, plus the ``UUID`` table only when the
  scenario's server reports the type, dropped and recreated for every test
  (function scope), so each test starts from empty tables;
- one fixture per model, each configured against this directory's database.
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

DDL = ExecutionOptions(stmt_type=StatementType.DDL)

DEFINITIONS = (
    NativeBitDefinition,
    NativeSetDefinition,
    NativeEnumDefinition,
    NativeYearDefinition,
    NativeJsonDefinition,
    NativeGeometryDefinition,
)


def _database_name() -> str:
    """Database name from this directory's namespace (below ``feature``)."""
    parts = Path(__file__).parent.parts
    start = parts.index("feature") + 1
    return "test_" + "_".join(parts[start:])


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
def schema(database):
    """Drop and recreate the native tables this directory uses, before every test."""
    fixtures = [definition(database.dialect) for definition in DEFINITIONS]
    if supports_uuid(database.dialect):
        fixtures.append(NativeUuidDefinition(database.dialect))
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
