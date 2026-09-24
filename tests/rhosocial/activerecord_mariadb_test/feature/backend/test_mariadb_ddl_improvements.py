# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_ddl_improvements.py
"""Tests for MariaDB DDL improvements: capability gating, UnsupportedFeatureError."""
import pytest
from unittest.mock import patch, PropertyMock

from rhosocial.activerecord.base.ddl import TableDDLDeriver
from rhosocial.activerecord.model import ActiveRecord
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


class InheritedTable(ActiveRecord):
    __table_name__ = "inherited"

    id: int

    @classmethod
    def table_inherits(cls):
        return ["parent_a", "parent_b"]


class TablespacedTable(ActiveRecord):
    __table_name__ = "tablespaced"

    id: int

    @classmethod
    def table_tablespace(cls):
        return "ts_data"


class TestMariaDBTableDeclarationGating:
    def test_table_declaration_defaults_are_absent(self):
        class Plain(ActiveRecord):
            __table_name__ = "plain_table_defaults"

            id: int

        expression = TableDDLDeriver(Plain, MariaDBDialect()).create_table()
        assert expression.inherits == []
        assert expression.tablespace is None

    def test_table_inherits_is_propagated_and_rejected(self):
        dialect = MariaDBDialect(version=(10, 6, 0))
        assert dialect.supports_table_inheritance() is False
        expression = TableDDLDeriver(InheritedTable, dialect).create_table()
        assert expression.inherits == ["parent_a", "parent_b"]
        with pytest.raises(UnsupportedFeatureError, match="INHERITS"):
            expression.to_sql()

    def test_table_tablespace_is_propagated_and_rejected(self):
        dialect = MariaDBDialect(version=(10, 6, 0))
        assert dialect.supports_table_tablespace() is False
        expression = TableDDLDeriver(TablespacedTable, dialect).create_table()
        assert expression.tablespace == "ts_data"
        with pytest.raises(UnsupportedFeatureError, match="TABLESPACE"):
            expression.to_sql()
