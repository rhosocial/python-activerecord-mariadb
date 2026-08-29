# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_schema_support.py
"""Tests for the SchemaSupport capability declared on the MariaDB dialect.

Under strict semantics MariaDB has no schema layer distinct from its
databases, so the umbrella ``supports_schema()`` flag must be False.
"""
from rhosocial.activerecord.backend.dialect.protocols import SchemaSupport
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


class TestSchemaCapability:
    """Umbrella flag and granular schema DDL capability bits."""

    def _dialect(self) -> MariaDBDialect:
        return MariaDBDialect()

    def test_supports_schema_is_false(self):
        assert self._dialect().supports_schema() is False

    def test_implements_schema_support_protocol(self):
        assert isinstance(self._dialect(), SchemaSupport)

    def test_no_schema_ddl_capabilities(self):
        d = self._dialect()
        assert d.supports_create_schema() is False
        assert d.supports_drop_schema() is False
