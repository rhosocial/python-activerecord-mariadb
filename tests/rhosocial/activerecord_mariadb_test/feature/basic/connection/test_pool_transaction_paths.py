# tests/rhosocial/activerecord_mariadb_test/feature/basic/connection/test_pool_transaction_paths.py
"""
Pool.transaction() dispatch branch contracts for MariaDB backend.

Imports the shared white-box tests for the three exclusive branches in
``BackendPool.transaction()`` and its async counterpart (Context-Match,
Connection-only, Acquire+Begin+Release dispatch).
"""

from rhosocial.activerecord.testsuite.feature.basic.connection.test_pool_transaction_paths import *  # noqa: F403
from rhosocial.activerecord.testsuite.feature.basic.connection.test_pool_transaction_paths_async import *  # noqa: F403
