# tests/rhosocial/activerecord_mariadb_test/feature/mixins/test_soft_delete.py
"""
Test soft delete functionality for MariaDB backend.

This module imports and runs the shared tests from the testsuite package,
ensuring MariaDB backend compatibility.
"""
# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.mixins.test_soft_delete import *
from rhosocial.activerecord.testsuite.feature.mixins.test_soft_delete_async import *  # noqa: F403
