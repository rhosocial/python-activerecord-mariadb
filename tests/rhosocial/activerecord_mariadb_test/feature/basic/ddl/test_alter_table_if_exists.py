# tests/rhosocial/activerecord_mariadb_test/feature/basic/ddl/test_alter_table_if_exists.py
"""
ALTER TABLE IF [NOT] EXISTS tests (sync) for the MariaDB backend.

Thin bridge that runs the shared testsuite contract against the MariaDB
dialect, which supports the ``IF [NOT] EXISTS`` column modifiers (10.0.2+).
"""

from rhosocial.activerecord.testsuite.feature.basic.ddl.test_alter_table_if_exists import *  # noqa: F403