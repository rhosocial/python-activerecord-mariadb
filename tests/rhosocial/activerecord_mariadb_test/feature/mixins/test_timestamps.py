# tests/rhosocial/activerecord_mariadb_test/feature/mixins/test_timestamps.py
"""
Test timestamp functionality for MariaDB backend.

This module imports and runs the shared tests from the testsuite package,
ensuring MariaDB backend compatibility.
"""

# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.mixins.test_timestamps import *  # noqa: F403
from rhosocial.activerecord.testsuite.feature.mixins.test_timestamps_async import *  # noqa: F403

