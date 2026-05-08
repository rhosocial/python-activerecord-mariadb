# tests/rhosocial/activerecord_mariadb_test/feature/query/connection/test_set_operation_context.py
"""
SetOperationQuery Context Test Module for MariaDB backend.

This module imports and runs the shared tests from the testsuite package,
ensuring MariaDB backend compatibility for SetOperationQuery connection pool context awareness.
"""
from rhosocial.activerecord.testsuite.feature.query.connection.conftest import (
    sync_pool_and_model,
    async_pool_and_model,
)

# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.query.connection.test_set_operation_context import *