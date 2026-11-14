# tests/support/mariadb.py
"""The MariaDB backend's test scenarios.

The scenario file holds server connection parameters only; the logical database
name comes from the test directory and is injected here.  MariaDB is a server
backend, so a scenario maps to one database on one server.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from rhosocial.activerecord.backend.impl.mariadb.backend import (
    AsyncMariaDBBackend,
    MariaDBBackend,
)
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

CONFIG_PATH = Path(
    os.environ.get("MARIADB_SCENARIOS_CONFIG_PATH")
    or Path(__file__).resolve().parents[1] / "config" / "mariadb_scenarios.yaml"
)

# The scenario file describes a server, never a database: the logical name is
# derived from the test directory.  A ``database`` key, if present, is dropped.
SERVER_ONLY_KEYS = ("database",)

DDL_OPTIONS = ExecutionOptions(stmt_type=StatementType.DDL)


def _load_scenarios(path: Path = CONFIG_PATH) -> Dict[str, Dict[str, Any]]:
    """Load one server-parameter dict per scenario from the YAML file."""
    with open(path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    entries = data.get("scenarios")
    if not entries:
        raise ValueError(f"{path} defines no scenarios")
    return {
        name: {key: value for key, value in entry.items() if key not in SERVER_ONLY_KEYS}
        for name, entry in entries.items()
    }


SCENARIO_MAP = _load_scenarios()
SCENARIOS = tuple(SCENARIO_MAP)


def _identifier(name: str) -> str:
    """Quote a MariaDB identifier (database names come from the testsuite)."""
    return "`" + name.replace("`", "``") + "`"


@dataclass(frozen=True)
class MariaDBScenario:
    """One MariaDB test scenario: a server plus the backend classes."""

    name: str
    server: Dict[str, Any]
    backend_class: Any = MariaDBBackend
    async_backend_class: Any = AsyncMariaDBBackend

    def make_config(self, database: str) -> MariaDBConnectionConfig:
        """Return the connection configuration for this database on this server."""
        return MariaDBConnectionConfig(**self.server, database=database)

    def reset_database(self, database: str) -> None:
        """Drop and recreate ``database`` on this scenario's server."""
        backend = self.backend_class(
            connection_config=MariaDBConnectionConfig(**self.server)
        )
        backend.connect()
        try:
            backend.execute(
                f"DROP DATABASE IF EXISTS {_identifier(database)}",
                (),
                options=DDL_OPTIONS,
            )
            charset = self.server.get("charset", "utf8mb4")
            backend.execute(
                f"CREATE DATABASE {_identifier(database)} "
                f"DEFAULT CHARACTER SET {charset}",
                (),
                options=DDL_OPTIONS,
            )
        finally:
            backend.disconnect()


def scenario(name: str) -> MariaDBScenario:
    """Return the scenario called ``name``."""
    try:
        server = SCENARIO_MAP[name]
    except KeyError:
        raise KeyError(f"Unknown MariaDB scenario: {name}") from None
    return MariaDBScenario(name, server)


def get_enabled_scenarios():
    """Return the scenarios this backend enables, as a name -> server map."""
    return {name: dict(server) for name, server in SCENARIO_MAP.items()}


def get_scenario(name: str):
    """Return ``(backend_class, config)`` for a benchmark database."""
    current = scenario(name)
    current.reset_database("test_benchmark")
    return current.backend_class, current.make_config("test_benchmark")


def get_scenario_raw(name: str):
    """Return ``(backend_class, config)`` for a server-level connection.

    Falls back to the first configured scenario when CI enables only one.
    """
    resolved = name if name in SCENARIO_MAP else next(iter(SCENARIO_MAP), None)
    if resolved is None:
        raise KeyError('No %s scenario configured' % name)
    current = scenario(resolved)
    return current.backend_class, current.make_config("information_schema")
