# tests/rhosocial/activerecord_mariadb_test/feature/query/conftest.py
"""
Pytest configuration for query feature tests.

This file imports fixtures from the corresponding testsuite, making them
available to the tests in this directory.
"""
import pytest
import pytest_asyncio

# Import fixtures from backend conftest
# The mariadb_backend and async_mariadb_backend fixtures are defined in
# feature/backend/conftest.py
from rhosocial.activerecord_mariadb_test.feature.backend.conftest import (
    mariadb_backend,
    mariadb_backend_single,
    async_mariadb_backend,
    async_mariadb_backend_single,
)

from rhosocial.activerecord.testsuite.feature.query.conftest import *