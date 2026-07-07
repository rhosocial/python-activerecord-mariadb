# tests/rhosocial/activerecord_mariadb_test/feature/mixins/test_optimistic_lock.py
"""
Test optimistic locking functionality for MariaDB backend.

This module imports and runs the shared tests from the testsuite package,
ensuring MariaDB backend compatibility.
"""
# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.mixins.test_optimistic_lock import *
from rhosocial.activerecord.testsuite.feature.mixins.test_optimistic_lock_async import *  # noqa: F403
