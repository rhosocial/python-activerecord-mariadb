# tests/rhosocial/activerecord_mariadb_test/feature/basic/type_adapter/conftest.py
"""Use the shared ``basic/type_adapter`` minimal test set.

MariaDB needs one DDL adjustment on top of the shared fixtures. The shared
``TypeAdapterTest`` declares ``unsupported_union`` as a TEXT column with a
Python-side ``0`` default, but core emits no SQL ``DEFAULT`` for it, so the
column is created ``TEXT NOT NULL`` with nothing to fall back on. A raw
``INSERT INTO type_adapter_tests (id, name) ...`` (as used by the
"NULL into a NOT NULL column" contract test) then fails on *this* column with
errno 1364 instead of reaching the intended ``name`` violation. Other drivers
tolerate the omission; MariaDB in strict mode does not. Give the column the
string form of its declared Python default after the shared schema is built.
"""
import pytest

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.testsuite.feature.basic.type_adapter.conftest import *  # noqa: F401,F403

DDL = ExecutionOptions(stmt_type=StatementType.DDL)


@pytest.fixture(scope="function", autouse=True)
def mariadb_type_adapter_column_defaults(database, schema):
    """Add the SQL default the shared model's Python-only default omits.

    Depends on ``schema`` so it runs after the shared fixture creates the
    tables and before the test body; the shared fixture still owns teardown.
    """
    database.execute(
        "ALTER TABLE `type_adapter_tests` MODIFY COLUMN `unsupported_union` "
        "TEXT NOT NULL DEFAULT ('0')",
        options=DDL,
    )
