# tests/rhosocial/activerecord_mariadb_test/feature/backend/named_connection/example_connections.py
"""
Example named connections for MariaDB testing.

Connection configurations are loaded from the scenarios YAML file
(tests/config/mariadb_scenarios.yaml) to avoid hardcoding credentials.

Each top-level key in the scenarios section becomes a factory function
in this module, e.g. calling ``mariadb_122()`` returns a
MariaDBConnectionConfig for the MariaDB 12.2 scenario.
"""

import os
from typing import Any, Dict

import yaml

from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


def _resolve_config_path() -> str:
    """Locate the scenarios configuration file.

    Returns the first existing path from a priority list.
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))
    # relative to tests/rhosocial/activerecord_mariadb_test/feature/backend/named_connection/
    candidates = [
        # MARIADB_SCENARIOS_CONFIG_PATH env var
        os.environ.get("MARIADB_SCENARIOS_CONFIG_PATH"),
        # standard location inside the repo (5x .. = python-activerecord-mariadb/tests/)
        os.path.join(this_dir, "..", "..", "..", "..", "..", "config", "mariadb_scenarios.yaml"),
        # alternate config.yml
        os.path.join(this_dir, "..", "..", "..", "..", "..", "config", "config.yml"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError(
        "Cannot locate mariadb_scenarios.yaml – set MARIADB_SCENARIOS_CONFIG_PATH or "
        "place the file in tests/config/mariadb_scenarios.yaml"
    )


def _load_scenarios() -> Dict[str, Dict[str, Any]]:
    """Parse the scenarios YAML and return the scenario name -> config mapping."""
    path = _resolve_config_path()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if "scenarios" in data:
        return data["scenarios"]
    # also support the flattened format used by some config files
    if "databases" in data and "mariadb" in data["databases"]:
        # Use first version only; named connections are single-target.
        versions = data["databases"]["mariadb"].get("versions", [])
        return {v.get("label", f"v{i}"): v for i, v in enumerate(versions)}
    return {"default": data}


# ---------------------------------------------------------------------------
# Dynamically create one factory function per scenario.
# Each function accepts a ``database`` override keyword argument so callers
# can customise the target database without editing configuration files.
# ---------------------------------------------------------------------------
_scenarios = _load_scenarios()
_globals = globals()
__all__ = []

for _name, _cfg in _scenarios.items():
    # Skip commented-out / disabled entries
    if _name.startswith("_"):
        continue

    def _make_factory(scenario_name: str, base_cfg: dict):
        def factory(database: str = None):
            kw = dict(base_cfg)
            if database is not None:
                kw["database"] = database
            return MariaDBConnectionConfig(**kw)

        factory.__name__ = scenario_name
        factory.__qualname__ = scenario_name
        factory.__doc__ = f"Connection factory for the ``{scenario_name}`` scenario."
        return factory

    _fn = _make_factory(_name, _cfg)
    _globals[_name] = _fn
    __all__.append(_name)
