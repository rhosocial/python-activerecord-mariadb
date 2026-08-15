# tests/rhosocial/activerecord_mariadb_test/feature/basic/transaction/test_async_owner_task.py
"""
Async contracts for AsyncTransactionManager._owner_task safety warning (MariaDB backend).

Imports the shared tests verifying that a second asyncio task entering
``transaction()`` on a backend holding an active transaction in another
task MUST emit UserWarning with the expected message.
"""

from rhosocial.activerecord.testsuite.feature.basic.transaction.test_async_owner_task import *  # noqa: F403
