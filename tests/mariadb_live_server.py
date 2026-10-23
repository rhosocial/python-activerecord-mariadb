# tests/mariadb_live_server.py
"""Collection-time check that a MariaDB server is reachable.

The backend-feature suite connects from its fixtures, so a missing server
surfaces as a fixture error rather than a skip. Tests whose whole point is
a live server use :func:`mariadb_server_available` in a module-level
``skipif`` marker instead, which is decided at collection time and before
any fixture tries to connect.

The scenarios are read from the same YAML the test conftest reads, with the
same ``MARIADB_SCENARIOS_CONFIG_PATH`` override and the same
``MARIADB_ACTIVE_SCENARIOS`` filter, so "reachable" means "one of the
servers this run is configured to use" and not "one of the servers someone
once configured".
"""

import os
import socket
from pathlib import Path
from typing import Iterator, Optional

import yaml

DEFAULT_SCENARIO_FILE = (
    Path(__file__).resolve().parent / "config" / "mariadb_scenarios.yaml"
)


def scenario_config_path() -> Optional[Path]:
    """Return the scenario file this run will use, if any."""
    explicit = os.getenv("MARIADB_SCENARIOS_CONFIG_PATH")
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    return DEFAULT_SCENARIO_FILE if DEFAULT_SCENARIO_FILE.is_file() else None


def _active_filter() -> Optional[set]:
    """The scenario names this run selected, or ``None`` for all of them."""
    filter_str = os.getenv("MARIADB_ACTIVE_SCENARIOS")
    if not filter_str:
        return None
    allowed = {s.strip() for s in filter_str.split(",") if s.strip()}
    return allowed or None


def _scenarios() -> Iterator[dict]:
    path = scenario_config_path()
    if path is None:
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return
    active = _active_filter()
    for name, config in (data.get("scenarios") or {}).items():
        if active is not None and name not in active:
            continue
        if isinstance(config, dict):
            yield config


def mariadb_server_available(timeout: float = 1.0) -> bool:
    """Return True if any configured MariaDB server accepts a TCP connection.

    Only the transport is checked: a server that accepts and then refuses
    the credentials still means "a server is there", and the fixture that
    actually connects reports the refusal in the usual way.
    """
    for config in _scenarios():
        host = config.get("host")
        port = config.get("port")
        if not host or not port:
            continue
        try:
            with socket.create_connection((str(host), int(port)), timeout=timeout):
                return True
        except OSError:
            continue
    return False
