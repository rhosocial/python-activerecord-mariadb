# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_schema_support.py
"""Tests for MariaDB's two, unrelated answers about "schema".

``supports_schema`` is the DDL-side switch -- does the engine have a schema
namespace, can it ``CREATE SCHEMA`` -- and it is False for MariaDB, whose
``CREATE SCHEMA`` is a synonym for ``CREATE DATABASE`` rather than a second
namespace layer. It is answered by core's ``SchemaMixin``, not by the naming
side, and MariaDB does not override it.

``NamespaceSupport`` is the naming-side protocol: which namespace levels a
name may carry. MariaDB declares it, because a name may carry a database --
it just cannot carry a schema, which ``supports_schema_qualification`` says.
"""
from rhosocial.activerecord.backend.dialect.protocols import NamespaceSupport
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


class TestSchemaCapability:
    """Umbrella flag and granular schema DDL capability bits."""

    def _dialect(self) -> MariaDBDialect:
        return MariaDBDialect()

    def test_supports_schema_is_false(self):
        assert self._dialect().supports_schema() is False

    def test_no_schema_ddl_capabilities(self):
        d = self._dialect()
        assert d.supports_create_schema() is False
        assert d.supports_drop_schema() is False

    def test_declares_the_naming_protocol(self):
        assert isinstance(self._dialect(), NamespaceSupport)

    def test_qualifies_by_database_but_never_by_schema(self):
        d = self._dialect()
        assert d.supports_catalog() is True
        assert d.supports_catalog_qualification() is True
        assert d.supports_schema_qualification() is False