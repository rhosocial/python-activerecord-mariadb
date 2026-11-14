# tests/rhosocial/activerecord_mariadb_test/feature/basic/fields/test_basic_mapped_models.py
# File path: tests/rhosocial/activerecord_mariadb_test/feature/basic/fields/test_basic_mapped_models.py

"""
This bridge file wildcard imports all test cases related to mapped models
from the testsuite. The fixtures those cases request (including
``mapped_models_fixtures``) come from the shared ``basic`` topic conftest.

IMPORTANT:
- Do NOT add any test logic directly in this file.
- This file is solely responsible for wiring up the testsuite's generic tests
  with the backend's specific fixtures and configuration.
"""

# Wildcard import all test cases from the testsuite's test files.
from rhosocial.activerecord.testsuite.feature.basic.fields.test_example_basic_fixtures import *  # noqa: F401,F403
