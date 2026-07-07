# tests/rhosocial/activerecord_mariadb_test/feature/basic/connection/test_active_record_crud.py
"""
Basic ActiveRecord CRUD Test Module for MariaDB backend.

This module imports and runs the shared tests from the testsuite package,
ensuring MariaDB backend compatibility for connection pool CRUD operations.
"""
from rhosocial.activerecord.testsuite.feature.basic.connection.conftest import (
    sync_pool_for_crud,
    async_pool_for_crud,
)

# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.basic.connection.test_active_record_crud import *
from rhosocial.activerecord.testsuite.feature.basic.connection.test_active_record_crud_async import *  # noqa: F403

