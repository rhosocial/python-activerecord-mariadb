# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/partition/conftest.py
"""No directory-specific fixtures: these tests use the backend-owned fixtures."""

from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    parallel=True,
    purpose="MariaDB backend tests (partition) against the directory-owned database.",
    passes_means="the live-database contract of this directory holds on MariaDB",
    fails_means="the directory-owned database is corrupted or a backend behavior is wrong",
)
