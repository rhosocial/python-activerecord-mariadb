# tests/rhosocial/activerecord_mariadb_test/feature/rules/backend/conftest.py
from __future__ import annotations

import importlib

import pytest

from rhosocial.activerecord.testsuite.feature.rules.backend.support import impl_root_of
from rhosocial.activerecord.testsuite.feature.rules.contracts.subject import (
    ExpressionSubject,
    Root,
)

IMPL = "rhosocial.activerecord.backend.impl.mariadb"
PREFIX = "MariaDB"


@pytest.fixture
def subject() -> ExpressionSubject:
    """mariadb's namespace, described without spelling its root."""
    expression = importlib.import_module(f"{IMPL}.expression")
    root = impl_root_of(expression)
    return ExpressionSubject(
        label="mariadb",
        roots=(Root("mariadb", root, IMPL),),
        prefix=PREFIX,
        open_package_root=root,
        impl_module_prefix=IMPL,
    )


@pytest.fixture
def registry() -> object:
    """MariaDB's published table: core's kinds merged with MariaDB's own."""
    return importlib.import_module(f"{IMPL}.expression_registry").MARIADB_EXPRESSION_REGISTRY
