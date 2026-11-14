"""Re-export the introspection fixtures used by the CLI contract tests."""
import importlib

_intro = importlib.import_module(
    "rhosocial.activerecord_mariadb_test.feature.backend.execute.introspection.conftest"
)

for _name, _value in list(vars(_intro).items()):
    if getattr(_value, "_fixture_function", None) is not None:
        globals()[_name] = _value
