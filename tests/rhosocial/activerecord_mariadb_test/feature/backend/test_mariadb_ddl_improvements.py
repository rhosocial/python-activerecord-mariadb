# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_ddl_improvements.py
"""Tests for MariaDB DDL improvements: capability gating, UnsupportedFeatureError."""
import pytest
from unittest.mock import patch, PropertyMock

from rhosocial.activerecord.backend.expression import (
    Column,
    TableExpression,
    QueryExpression,
    CreateViewExpression,
    DropViewExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class TestMariaDBViewCapabilityGating:
    """Tests for MariaDB VIEW DDL capability gating."""

    def test_or_replace_view_supported(self):
        """MariaDB supports CREATE OR REPLACE VIEW."""
        dialect = MariaDBDialect()
        assert dialect.supports_or_replace_view() is True

    def test_drop_view_if_exists_supported(self):
        """MariaDB supports DROP VIEW IF EXISTS."""
        dialect = MariaDBDialect()
        assert dialect.supports_if_exists_view() is True

    def test_cascade_view_supported(self):
        """MariaDB supports DROP VIEW CASCADE."""
        dialect = MariaDBDialect()
        assert dialect.supports_cascade_view() is True

    def test_materialized_view_not_supported(self):
        """MariaDB does not support materialized views."""
        dialect = MariaDBDialect()
        assert dialect.supports_materialized_view() is False


class TestMariaDBColumnCapabilityGating:
    """Tests for MariaDB COLUMN DDL capability gating."""

    def test_foreign_key_on_delete_supported(self):
        """MariaDB supports FK ON DELETE."""
        dialect = MariaDBDialect()
        assert dialect.supports_foreign_key_on_delete() is True

    def test_foreign_key_on_update_supported(self):
        """MariaDB supports FK ON UPDATE."""
        dialect = MariaDBDialect()
        assert dialect.supports_foreign_key_on_update() is True

    def test_fk_match_not_supported(self):
        """MariaDB does not support FK MATCH."""
        dialect = MariaDBDialect()
        assert dialect.supports_fk_match() is False


class TestMariaDBTriggerCapabilityGating:
    """Tests for MariaDB TRIGGER DDL capability gating."""

    def test_trigger_referencing_not_supported(self):
        """MariaDB does not support trigger REFERENCING clause."""
        dialect = MariaDBDialect()
        assert dialect.supports_trigger_referencing() is False

    def test_trigger_when_not_supported(self):
        """MariaDB does not support trigger WHEN clause."""
        dialect = MariaDBDialect()
        assert dialect.supports_trigger_when() is False


class TestMariaDBFunctionCapabilityGating:
    """Tests for MariaDB FUNCTION DDL capability gating."""

    def test_stored_function_supported(self):
        """MariaDB supports stored functions."""
        dialect = MariaDBDialect()
        assert dialect.supports_stored_function() is True
