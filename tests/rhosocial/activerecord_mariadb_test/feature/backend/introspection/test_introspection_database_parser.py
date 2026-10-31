# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_introspection_database_parser.py
"""Parser-level tests for MariaDB database and table introspection.

These call the parsers with no server at all -- the row the query would have
returned is supplied directly. They pin two things the MariaDB backend had
been reading through a backend private: the version a database record
reports, and the kind a ``information_schema.TABLES`` row names.
"""

from types import SimpleNamespace

from rhosocial.activerecord.backend.impl.mariadb.introspection import (
    SyncMariaDBIntrospector,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.introspection.types import TableType


class _NoServerBackend:
    """The parts of a MariaDB backend an introspector reads, and nothing else."""

    def __init__(self, version=None, cached_version=None):
        self.config = SimpleNamespace(database="shop")
        self.dialect = MariaDBDialect(version)
        self._cached_version = cached_version

    def get_cached_server_version(self):
        return self._cached_version


class _UnusedExecutor:
    """An executor that fails loudly if a parser-level test asks for SQL."""

    def execute(self, sql, params=()):
        raise AssertionError("a parser-level test must not execute SQL")


def _introspector(**kwargs) -> SyncMariaDBIntrospector:
    return SyncMariaDBIntrospector(_NoServerBackend(**kwargs), _UnusedExecutor())


_SCHEMATA_ROW = {
    "DEFAULT_CHARACTER_SET_NAME": "utf8mb4",
    "DEFAULT_COLLATION_NAME": "utf8mb4_uca1400_ai_ci",
}


class TestParseDatabaseInfo:
    """The record is built from the row and the version, never a private."""

    def test_unadapted_version_is_reported_as_unknown(self):
        """An unknown version is not a fabricated default."""
        info = _introspector().parse_database_info([_SCHEMATA_ROW])

        assert info.version == "unknown"
        assert info.version_tuple == (0, 0, 0)

    def test_row_values_fill_the_rest_of_the_record(self):
        info = _introspector().parse_database_info([_SCHEMATA_ROW])

        assert info.name == "shop"
        assert info.vendor == "MariaDB"
        assert info.encoding == "utf8mb4"
        assert info.collation == "utf8mb4_uca1400_ai_ci"
        # Not selected by the statement, so not invented here.
        assert info.table_count is None
        assert info.size_bytes is None

    def test_adapted_version_is_reported(self):
        info = _introspector(version=(11, 4, 2)).parse_database_info([_SCHEMATA_ROW])

        assert info.version == "11.4.2"
        assert info.version_tuple == (11, 4, 2)

    def test_backend_cache_is_used_when_the_dialect_has_none(self):
        info = _introspector(cached_version=(10, 11, 8)).parse_database_info(
            [_SCHEMATA_ROW]
        )

        assert info.version == "10.11.8"
        assert info.version_tuple == (10, 11, 8)

    def test_no_rows_leaves_the_row_derived_fields_empty(self):
        info = _introspector(version=(11, 4, 2)).parse_database_info([])

        assert info.name == "shop"
        assert info.encoding is None
        assert info.collation is None


class TestParseTables:
    """The catalog's kind is carried through instead of being flattened."""

    def test_table_kinds_are_reported_as_named(self):
        rows = [
            {"TABLE_NAME": "users", "TABLE_TYPE": "BASE TABLE"},
            {"TABLE_NAME": "user_summary", "TABLE_TYPE": "VIEW"},
            {"TABLE_NAME": "INNODB_METRICS", "TABLE_TYPE": "SYSTEM VIEW"},
        ]

        tables = _introspector().parse_tables(rows, schema=None)

        assert [table.name for table in tables] == [
            "users",
            "user_summary",
            "INNODB_METRICS",
        ]
        assert [table.table_type for table in tables] == [
            TableType.BASE_TABLE,
            TableType.VIEW,
            TableType.SYSTEM_TABLE,
        ]

    def test_schema_defaults_to_the_connected_database(self):
        rows = [{"TABLE_NAME": "users", "TABLE_TYPE": "BASE TABLE"}]

        tables = _introspector().parse_tables(rows, schema=None)

        assert tables[0].schema == "shop"

    def test_an_explicit_schema_wins_over_the_default(self):
        rows = [{"TABLE_NAME": "users", "TABLE_TYPE": "BASE TABLE"}]

        tables = _introspector().parse_tables(rows, schema="archive")

        assert tables[0].schema == "archive"
