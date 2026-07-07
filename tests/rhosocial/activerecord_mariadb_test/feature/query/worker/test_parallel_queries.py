# tests/rhosocial/activerecord_mariadb_test/feature/query/worker/test_parallel_queries.py
"""
Bridge file for parallel queries worker tests.

Imports tests from testsuite and makes them discoverable by pytest.
"""
from rhosocial.activerecord.testsuite.feature.query.worker.conftest import (
    order_fixtures_for_worker,
    async_order_fixtures_for_worker,
)
from rhosocial.activerecord.testsuite.feature.query.worker.test_parallel_queries import *
from rhosocial.activerecord.testsuite.feature.query.worker.test_parallel_queries_async import *  # noqa: F403
