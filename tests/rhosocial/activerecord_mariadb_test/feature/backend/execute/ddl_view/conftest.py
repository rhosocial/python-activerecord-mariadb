# tests/rhosocial/activerecord_mariadb_test/feature/backend/execute/ddl_view/conftest.py
"""No directory-specific fixtures: these tests use the backend-owned fixtures."""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration


DECLARATION = Declaration(
    uses_database=True,
    parallel=True,
    purpose="MariaDB backend tests (ddl_view) against the directory-owned database.",
    passes_means="the live-database contract of this directory holds on MariaDB",
    fails_means="the directory-owned database is corrupted or a backend behavior is wrong",
)
