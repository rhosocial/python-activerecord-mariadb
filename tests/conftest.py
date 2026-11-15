# tests/conftest.py
"""Root configuration for the MariaDB backend's test tree.

The backend knows its own classes and how a scenario maps to a connection, so
no declaration table is needed here: the scenario is exposed as a parameterized
pytest fixture that the testsuite environment consumes.
"""
import pytest

import support.mariadb

_SCENARIOS = [support.mariadb.scenario(name) for name in support.mariadb.SCENARIOS]


@pytest.fixture(scope="session", params=_SCENARIOS, ids=lambda scenario: scenario.name)
def backend_scenario(request):
    """Return the scenario the tests run against; its id is the scenario name."""
    return request.param


#: The suite's package prefix: a bridge file imports its tests with ``*``, so the
#: test objects keep this module and identify themselves as suite tests even
#: though the file that re-exports them lives here.
_SUITE_PACKAGE_PREFIX = "rhosocial.activerecord.testsuite."

#: Whether each scenario's sessions keep TIMESTAMP columns explicit, read once.
_TIMESTAMP_DEFAULTS_ARE_EXPLICIT: dict = {}


def _is_shared_suite_test(item) -> bool:
    """Whether this item's test object comes from the shared suite."""
    for owner in (
        getattr(item, "cls", None),
        getattr(item, "function", None),
        getattr(item, "obj", None),
    ):
        module = getattr(owner, "__module__", "")
        if module.startswith(_SUITE_PACKAGE_PREFIX):
            return True
    return False


def _timestamp_defaults_are_explicit(scenario) -> bool:
    """Whether this scenario's sessions keep TIMESTAMP columns explicit.

    The answer comes from the dialect, which records the session's variables
    during adaptation -- so a server started with a different setting answers
    according to what it actually does, not according to its version.
    """
    answer = _TIMESTAMP_DEFAULTS_ARE_EXPLICIT.get(scenario.name)
    if answer is None:
        backend = scenario.backend_class(
            connection_config=scenario.make_config("mysql")
        )
        backend.connect()
        try:
            backend.introspect_and_adapt()
            answer = backend.dialect.explicit_defaults_for_timestamp()
        finally:
            backend.disconnect()
        _TIMESTAMP_DEFAULTS_ARE_EXPLICIT[scenario.name] = answer
    return answer


@pytest.fixture(autouse=True)
def skip_the_shared_suite_when_timestamps_are_implicit(request):
    """Skip the shared suite on a server that rewrites TIMESTAMP columns.

    The suite assumes an UPDATE leaves a TIMESTAMP column it does not name alone.
    A server reporting ``explicit_defaults_for_timestamp`` OFF rewrites the table's
    first TIMESTAMP column -- the default on 10.2-10.6, where the suite's own
    failures showed it, and reproducible on 11.8 by switching the session off: a
    seeded ``start_at`` came back as the current instant and broke the period
    validator. The suite does not bend for one backend, so it is skipped as a
    whole -- bridge files included, which is why the test object's module
    decides. MariaDB 10.11 and later report ON and run it.
    """
    if not _is_shared_suite_test(request.node):
        yield
        return
    callspec = getattr(request.node, "callspec", None)
    scenario = getattr(callspec, "params", {}).get("backend_scenario")
    if scenario is None:
        yield
        return
    if _timestamp_defaults_are_explicit(scenario):
        yield
        return
    pytest.skip(
        "@@SESSION.explicit_defaults_for_timestamp is OFF on this server, so an "
        "UPDATE rewrites the table's first TIMESTAMP column; the shared suite "
        "assumes it does not"
    )
