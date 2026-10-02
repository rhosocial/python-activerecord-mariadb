# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_schema_support.py
"""Tests for the SchemaSupport capability declared on the MariaDB dialect.

MariaDB treats ``SCHEMA`` as a synonym for ``DATABASE`` rather than as a distinct
namespace level. A ``schema_name`` is therefore usable -- it resolves to a
database -- so the umbrella flag is True. The granular DDL flags stay True as
well, because the server accepts the SCHEMA spelling for CREATE/DROP.
"""
from rhosocial.activerecord.backend.dialect.protocols import SchemaSupport
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


class TestSchemaCapability:
    """Umbrella flag and granular schema DDL capability bits."""

    def _dialect(self) -> MariaDBDialect:
        return MariaDBDialect()

    def test_supports_schema_is_true(self):
        """A schema_name resolves to a database, which is usable."""
        assert self._dialect().supports_schema() is True

    def test_implements_schema_support_protocol(self):
        assert isinstance(self._dialect(), SchemaSupport)

    def test_create_drop_schema_are_database_aliases(self):
        """The server accepts the SCHEMA spelling; it creates a database."""
        d = self._dialect()
        assert d.supports_create_schema() is True
        assert d.supports_drop_schema() is True
        assert d.supports_schema_if_not_exists() is True
        assert d.supports_schema_if_exists() is True
