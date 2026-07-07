# tests/rhosocial/activerecord_mariadb_test/feature/basic/connection/test_active_record_context.py
"""
Basic ActiveRecord Context Test Module for MariaDB backend.

This module imports and runs the shared tests from the testsuite package,
ensuring MariaDB backend compatibility for connection pool context awareness.
"""
from rhosocial.activerecord.testsuite.feature.basic.connection.conftest import (
    sync_pool_and_model,
    async_pool_and_model,
)

# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.basic.connection.test_active_record_context import *
from rhosocial.activerecord.testsuite.feature.basic.connection.test_active_record_context_async import *  # noqa: F403

