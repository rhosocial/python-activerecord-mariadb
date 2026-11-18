"""Re-export the introspection fixtures used by the CLI contract tests."""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration
import importlib


DECLARATION = Declaration(
    uses_database=True,
    parallel=True,
    purpose="MariaDB backend tests (cli) against the directory-owned database.",
    passes_means="the live-database contract of this directory holds on MariaDB",
    fails_means="the directory-owned database is corrupted or a backend behavior is wrong",
)

_intro = importlib.import_module(
    "rhosocial.activerecord_mariadb_test.feature.backend.execute.introspection.conftest"
)

for _name, _value in list(vars(_intro).items()):
    if getattr(_value, "_fixture_function", None) is not None:
        globals()[_name] = _value
