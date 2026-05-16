# tests/conftest.py
"""
This is the root pytest configuration file for the rhosocial-activerecord-mariadb package's test suite.

Its primary responsibility is to configure the environment so that the external
`rhosocial-activerecord-testsuite` can find and use the backend-specific
implementations (Providers) defined within this project.
"""
import os
import pytest

# Set the environment variable that the testsuite uses to locate the provider registry.
# The testsuite is a generic package and doesn't know the specific location of the
# provider implementations for this backend (MariaDB). This environment variable
# acts as a bridge, pointing the testsuite to the correct import path.
#
# `setdefault` is used to ensure that this value is set only if it hasn't been
# set already, allowing for overrides in different environments if needed.
os.environ.setdefault(
    'TESTSUITE_PROVIDER_REGISTRY',
    'providers.registry:provider_registry'
)

# Early-parse --scenarios from sys.argv and set MARIADB_ACTIVE_SCENARIOS env var
# before any conftest module loads its SCENARIO_MAP. This must happen at module
# level (not inside a pytest hook) because sub-conftests execute their
# _load_scenarios_from_config() at import time.
import sys
_argv_scenarios = None
for i, arg in enumerate(sys.argv):
    if arg.startswith('--scenarios='):
        _argv_scenarios = arg.split('=', 1)[1]
        break
    elif arg == '--scenarios' and i + 1 < len(sys.argv):
        _argv_scenarios = sys.argv[i + 1]
        break
if _argv_scenarios:
    os.environ['MARIADB_ACTIVE_SCENARIOS'] = _argv_scenarios


# =============================================================================
# Scenario Parallel Scheduling Plugin
#
# Usage:
#   pytest --scenario-parallel -n 11 --dist=loadgroup tests/
#
# Design: All tests for the same scenario are pinned to the same xdist worker
#         (via nodeid @suffix), while tests for different scenarios run in
#         parallel. Behavior is unchanged without --scenario-parallel.
# =============================================================================

def _get_scenario_names():
    """Lazy import to avoid side effects during conftest loading."""
    try:
        from providers.scenarios import SCENARIO_MAP
        return set(SCENARIO_MAP.keys()), list(SCENARIO_MAP.keys())
    except Exception:
        return set(), []


def _extract_scenario_from_item(item, scenario_name_set):
    """Extract scenario name from item's callspec.

    Returns:
        str:  scenario name when exactly one scenario param is found
        None: no scenario params (not a scenario-parametrized test)
        list: multiple distinct scenario names (cross-scenario test)
    """
    callspec = getattr(item, 'callspec', None)
    if callspec is None:
        return None
    scenario_values = [
        v for v in callspec.params.values()
        if isinstance(v, str) and v in scenario_name_set
    ]
    if len(scenario_values) == 1:
        return scenario_values[0]
    if len(scenario_values) >= 2:
        return scenario_values  # cross-scenario: caller checks isinstance(result, list)
    return None


def _add_xdist_group_marker(item, group_name):
    """Append @group_name suffix to item._nodeid for loadgroup scheduling."""
    suffix = f"@{group_name}"
    if suffix not in item.nodeid:
        item._nodeid = item.nodeid + suffix


def pytest_addoption(parser):
    parser.addoption(
        '--scenario-parallel',
        action='store_true',
        default=False,
        help='Scenario parallel mode: distribute scenarios across workers, keep each scenario on one worker.',
    )
    parser.addoption(
        '--scenarios',
        default=None,
        help='Comma-separated list of scenario names to run (e.g., --scenarios=mariadb_102,mariadb_122). ',
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "xdist_group(name): specify the xdist group for a test (provided by pytest-xdist).",
    )

    # Propagate --scenarios to environment variable so that all conftest.py
    # instances (which load SCENARIO_MAP independently) can filter consistently.
    scenarios_opt = config.getoption('--scenarios', default=None)
    if scenarios_opt:
        os.environ['MARIADB_ACTIVE_SCENARIOS'] = scenarios_opt


def _is_backend_single_test(item):
    """Check if a test uses mariadb_backend_single or async_mariadb_backend_single.

    These fixtures connect to the first scenario's database but are not
    scenario-parametrized. In --scenario-parallel mode they must be pinned
    to the first scenario's worker to avoid table conflicts.
    """
    fixturenames = getattr(item, 'fixturenames', None)
    if fixturenames is None:
        return False
    return 'mariadb_backend_single' in fixturenames or 'async_mariadb_backend_single' in fixturenames


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--scenario-parallel', default=False):
        return

    scenario_name_set, scenario_name_list = _get_scenario_names()
    if not scenario_name_set:
        return

    first_scenario = scenario_name_list[0]
    scenario_items = []
    cross_scenario_items = []
    backend_single_items = []
    normal_items = []

    for item in items:
        result = _extract_scenario_from_item(item, scenario_name_set)
        if isinstance(result, list):
            # Cross-scenario test: uses fixtures from multiple scenarios simultaneously.
            # Running concurrently with per-scenario workers causes table conflicts on
            # shared database instances, so skip during parallel mode. Run separately
            # without --scenario-parallel for serial execution.
            item.add_marker(
                pytest.mark.skip(
                    reason="Cross-scenario test skipped in --scenario-parallel mode. "
                           "Run without --scenario-parallel for serial execution."
                )
            )
            cross_scenario_items.append(item)
        elif isinstance(result, str):
            _add_xdist_group_marker(item, result)
            scenario_items.append(item)
        elif _is_backend_single_test(item):
            # Non-parametrized fixture using first scenario's DB.
            # Pin to the first scenario's worker to avoid table conflicts.
            _add_xdist_group_marker(item, first_scenario)
            backend_single_items.append(item)
        else:
            normal_items.append(item)

    def sort_key(item):
        result = _extract_scenario_from_item(item, scenario_name_set)
        if not isinstance(result, str):
            return ('~', 0)
        try:
            scenario_idx = scenario_name_list.index(result)
        except ValueError:
            scenario_idx = 0
        base = item.nodeid.split('[')[0] if '[' in item.nodeid else item.nodeid
        return (base, scenario_idx)

    scenario_items.sort(key=sort_key)
    items[:] = scenario_items + backend_single_items + normal_items + cross_scenario_items

    groups: dict = {}
    for item in scenario_items:
        sn = _extract_scenario_from_item(item, scenario_name_set)
        if isinstance(sn, str):
            base = item.nodeid.split('[')[0] if '[' in item.nodeid else item.nodeid
            groups.setdefault(base, set()).add(sn)

    print(f"\n[ScenarioParallel] {len(items)} items: "
          f"{len(scenario_items)} scenario-param + "
          f"{len(backend_single_items)} backend-single @{first_scenario} + "
          f"{len(normal_items)} normal + "
          f"{len(cross_scenario_items)} cross-scenario (skipped)")
    print(f"[ScenarioParallel] {len(groups)} test methods, {len(scenario_name_list)} scenarios in parallel")
    print(f"[ScenarioParallel] Suggested: --dist=loadgroup -n {len(scenario_name_list)}")
