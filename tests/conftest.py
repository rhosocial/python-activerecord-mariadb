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


#: Directories whose assertions an old server's implicit timestamp rewrite
#: invalidates.
#:
#: A server that reports ``explicit_defaults_for_timestamp`` OFF gives the
#: table's first TIMESTAMP column an implicit
#: ``DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP``, so an UPDATE
#: rewrites a column it never names. ``feature/basic/crud`` asserts the
#: opposite. The suite does not bend for one backend, and the server's
#: configuration is the operator's, so the directory is skipped here when the
#: session says so. MariaDB 11.8.9 reports ON and therefore runs it.
_IMPLICIT_TIMESTAMP_DIRECTORIES = ("feature/basic/crud",)

#: The session's answer, per scenario name, read once.
_TIMESTAMP_DEFAULTS_ARE_EXPLICIT: dict = {}


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
def skip_directories_this_server_cannot_satisfy(request):
    """Skip the shared directories whose assertions this server breaks."""
    path = str(getattr(request.node, "path", "")).replace("\\", "/")
    directory = next(
        (name for name in _IMPLICIT_TIMESTAMP_DIRECTORIES if name in path), None
    )
    if directory is None:
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
        "@@SESSION.explicit_defaults_for_timestamp is OFF on this server, so it "
        "rewrites the table's first TIMESTAMP column on UPDATE; {} asserts that "
        "an unmodified field keeps its value".format(directory)
    )
