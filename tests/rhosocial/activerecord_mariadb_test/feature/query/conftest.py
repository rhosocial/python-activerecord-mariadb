# tests/rhosocial/activerecord_mariadb_test/feature/query/conftest.py
"""
Pytest configuration for query feature tests.

This file imports fixtures from the corresponding testsuite, making them
available to the tests in this directory. It also applies MariaDB-specific
test markers.
"""
import pytest

# Import sync fixtures from backend conftest
from rhosocial.activerecord_mariadb_test.feature.backend.conftest import (
    mariadb_backend,
    mariadb_backend_single,
)

from rhosocial.activerecord.testsuite.feature.query.conftest import *


def pytest_collection_modifyitems(items):
    """Apply MariaDB-specific xfail markers to tests with known issues."""
    for item in items:
        # CTE range conditions test lacks outer ORDER BY in testsuite <= 1.0.0.dev13.
        # MariaDB does not guarantee CTE internal ORDER BY carries to outer SELECT.
        # Fix: testsuite adds explicit order_by() to outer query (pending release).
        if "cte_with_range_conditions" in item.nodeid:
            item.add_marker(pytest.mark.xfail(
                reason="Testsuite CTE range conditions test lacks outer ORDER BY; "
                       "MariaDB returns non-deterministic order. "
                       "Will pass once testsuite >= 1.0.0.dev14 is released.",
                strict=False,
            ))
