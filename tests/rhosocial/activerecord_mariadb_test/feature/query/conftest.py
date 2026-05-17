# tests/rhosocial/activerecord_mariadb_test/feature/query/conftest.py
"""
Pytest configuration for query feature tests.

This file imports fixtures from the corresponding testsuite, making them
available to the tests in this directory.
"""
import pytest

# Import sync fixtures from backend conftest
from rhosocial.activerecord_mariadb_test.feature.backend.conftest import (
    mariadb_backend,
    mariadb_backend_single,
)

from rhosocial.activerecord.testsuite.feature.query.conftest import *