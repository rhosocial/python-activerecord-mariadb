# tests/rhosocial/activerecord_mariadb_test/feature/rules/backend/conftest.py
"""Fixtures for MariaDB's own rule suite.

MariaDB owns only its own ``impl/mariadb`` tree. Every path is derived from
the installed packages, never from a hardcoded worktree path, and
``source_roots`` names a single root: ``backend/impl/mariadb``. The shared
rule library supplies the assertions; this conftest selects the subject.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import List, Tuple

import pytest

from rhosocial.activerecord.testsuite.feature.rules.backend.conftest import *  # noqa: F401,F403
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    uses_database=False,
    parallel=False,
    purpose="Executable assertions of the MariaDB backend's formal constraints",
    passes_means="MariaDB source obeys the mechanical and structural rule",
    fails_means="MariaDB source introduces a forbidden construct or dependency",
)


def mariadb_expression_package() -> object:
    """The installed MariaDB expression package."""
    return importlib.import_module("rhosocial.activerecord.backend.impl.mariadb.expression")


def mariadb_impl_root() -> Path:
    """The installed ``backend/impl/mariadb`` directory."""
    package = mariadb_expression_package()
    for search_path in vars(package).get("__path__", ()):
        current = Path(search_path).resolve()
        for candidate in [current] + list(current.parents):
            if candidate.name == "impl" and candidate.parent.name == "backend":
                return candidate / current.relative_to(candidate).parts[0]
    pytest.skip("MariaDB impl root is not discoverable from the installed package")


def mariadb_project_root() -> Path:
    """Project root inferred from the installed MariaDB package layout."""
    for candidate in [mariadb_impl_root()] + list(mariadb_impl_root().parents):
        if (candidate / "tests").is_dir() and (candidate / "src").is_dir():
            return candidate
    pytest.skip("MariaDB project root is not discoverable from the installed package")


@pytest.fixture
def backend_expression_package() -> object:
    """MariaDB's expression package."""
    return mariadb_expression_package()


@pytest.fixture
def backend_dialect() -> object:
    """An instantiated MariaDB dialect."""
    from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

    return MariaDBDialect()


@pytest.fixture
def backend_prefix() -> str:
    """MariaDB's own naming prefix."""
    return "MariaDB"


@pytest.fixture
def backend_impl_root() -> Path:
    """The MariaDB ``impl`` root used by file-driven shared rules."""
    return mariadb_impl_root()


@pytest.fixture
def source_roots() -> List[Tuple[str, Path]]:
    """One root only: the MariaDB backend, never core or another backend."""
    return [("mariadb", mariadb_impl_root())]


@pytest.fixture
def backend_project_root() -> Path:
    """Project root for MariaDB's tests."""
    return mariadb_project_root()
