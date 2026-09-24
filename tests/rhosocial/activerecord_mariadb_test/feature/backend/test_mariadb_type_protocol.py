# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_type_protocol.py
"""
MariaDB type protocol conformance tests.

Verifies the two-level data-type contract between the core ``DataType``
system and the MariaDB backend:

- ``supports_data_type_<name>`` / ``format_data_type_<name>`` 1:1
  correspondence on ``MariaDBDialect``;
- ``supports_data_types()`` merges the ``mariadb_*`` namespaced family with
  the core family;
- ``suggested_data_types()`` values are real ``DataType`` classes and its
  keys are disjoint from the supported keys;
- ``MariaDBEnumType`` renders ``ENUM('a','b')`` (with charset/collation
  extensions);
- dialect-specific range checks live in the formatters (DECIMAL/FLOAT
  precision, fractional-seconds precision);
- ``dialect_options`` forwards through construction and participates in
  equality.
"""

from uuid import UUID

import pytest

from rhosocial.activerecord.base.ddl import ColumnTypeResolver
from rhosocial.activerecord.backend.dialect.mixins import DataTypeMixin
from rhosocial.activerecord.backend.expression.types import (
    DataType,
    DecimalType,
    FloatType,
    IntegerType,
    TimestampType,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.schema import MariaDBSchemaDiffer
from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
    MariaDBBinaryType,
    MariaDBEnumType,
    MariaDBIntType,
    MariaDBSetType,
    MariaDBUUIDType,
)
from rhosocial.activerecord.backend.introspection.types import ColumnInfo


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


class TestSupportFormatCorrespondence:
    """Every format_data_type_<name> has supports_data_type_<name>, 1:1."""

    def test_format_family_equals_supports_family(self, dialect):
        format_names = {
            member[len("format_data_type_"):]
            for member in dir(MariaDBDialect)
            if member.startswith("format_data_type_")
        }
        support_names = {
            member[len("supports_data_type_"):]
            for member in dir(MariaDBDialect)
            if member.startswith("supports_data_type_")
        }
        assert format_names, "MariaDBDialect must implement format_data_type_* members"
        assert format_names == support_names

    def test_supports_data_types_covers_every_formatter(self, dialect):
        format_names = {
            member[len("format_data_type_"):]
            for member in dir(MariaDBDialect)
            if member.startswith("format_data_type_")
        }
        supported = dialect.supports_data_types()
        assert set(supported) == format_names

    def test_supports_data_types_returns_classes(self, dialect):
        for name, klass in dialect.supports_data_types().items():
            assert isinstance(klass, type), name
            assert issubclass(klass, DataType), name

    def test_inherits_mixin_scan_implementation(self, dialect):
        assert MariaDBDialect.supports_data_types is DataTypeMixin.supports_data_types


class TestSupportsDataTypesMapping:
    """supports_data_types() merges mariadb_* namespaced and core entries."""

    def test_includes_mariadb_namespaced_entries(self, dialect):
        supported = dialect.supports_data_types()
        assert "mariadb_int" in supported
        assert supported["mariadb_int"] is MariaDBIntType
        assert "mariadb_enum" in supported
        assert "mariadb_set" in supported
        assert supported["mariadb_uuid"] is MariaDBUUIDType

    def test_includes_core_entries(self, dialect):
        supported = dialect.supports_data_types()
        assert "integer" in supported
        assert supported["integer"] is IntegerType
        assert "varchar" in supported
        assert "decimal" in supported
        assert "json" in supported

    def test_per_type_support_methods_are_truthful(self, dialect):
        supported = dialect.supports_data_types()
        for name in supported:
            checker = getattr(dialect, f"supports_data_type_{name}")
            assert checker() is True, name


class TestSuggestedDataTypes:
    """suggested_data_types(): real classes, disjoint from supported keys."""

    def test_values_are_data_type_classes(self, dialect):
        suggestions = dialect.suggested_data_types()
        for key, klass in suggestions.items():
            assert isinstance(klass, type), key
            assert issubclass(klass, DataType), key

    def test_keys_disjoint_from_supported(self, dialect):
        suggestions = dialect.suggested_data_types()
        supported = dialect.supports_data_types()
        assert not (set(suggestions) & set(supported))

    def test_uuid_suggestion_defaults_to_fixed_length_binary(self, dialect):
        suggestion = dialect.suggested_data_types()["uuid"]
        assert suggestion is MariaDBUUIDType
        sql, params = suggestion(dialect).to_sql()
        assert sql == "BINARY(16)"
        assert params == ()

    def test_column_type_resolver_resolves_uuid_as_fixed_length_binary(self, dialect):
        resolved = ColumnTypeResolver(dialect).resolve(UUID)
        assert type(resolved) is MariaDBUUIDType
        assert resolved.name == "mariadb_uuid"
        assert resolved.length == 16
        assert resolved.dialect is dialect
        assert resolved.to_sql() == ("BINARY(16)", ())

    def test_enum_suggested_as_mariadb_enum(self, dialect):
        suggestions = dialect.suggested_data_types()
        assert suggestions.get("enum") is MariaDBEnumType


class TestMariaDBUUIDTypeEquivalence:
    @pytest.mark.parametrize("length", [8, 32])
    def test_schema_differ_rejects_non_16_byte_binary(self, dialect, length):
        differ = MariaDBSchemaDiffer()
        binary_column = ColumnInfo(
            name="id",
            table_name="users",
            ordinal_position=1,
            data_type=f"BINARY({length})",
            parsed_data_type=MariaDBBinaryType(dialect, length=length),
        )
        uuid_column = ColumnInfo(
            name="id",
            table_name="users",
            ordinal_position=1,
            data_type="BINARY(16)",
            parsed_data_type=MariaDBUUIDType(dialect),
        )

        assert not differ._columns_equivalent(binary_column, uuid_column)
        assert not differ._columns_equivalent(uuid_column, binary_column)

    def test_schema_differ_accepts_16_byte_binary(self, dialect):
        differ = MariaDBSchemaDiffer()
        binary_column = ColumnInfo(
            name="id",
            table_name="users",
            ordinal_position=1,
            data_type="BINARY(16)",
            parsed_data_type=MariaDBBinaryType(dialect, length=16),
        )
        uuid_column = ColumnInfo(
            name="id",
            table_name="users",
            ordinal_position=1,
            data_type="BINARY(16)",
            parsed_data_type=MariaDBUUIDType(dialect),
        )

        assert differ._columns_equivalent(binary_column, uuid_column)
        assert differ._columns_equivalent(uuid_column, binary_column)


class TestMariaDBEnumRendering:
    """MariaDBEnumType inherits core EnumType; rendering keeps extensions."""

    def test_simple_enum(self, dialect):
        enum_type = MariaDBEnumType(dialect, values=["a", "b"])
        assert enum_type.name == "mariadb_enum"
        sql, params = enum_type.to_sql()
        assert sql == "ENUM('a','b')"
        assert params == ()

    def test_enum_with_charset_and_collation(self, dialect):
        enum_type = MariaDBEnumType(
            dialect, values=["a", "b"],
            charset="utf8mb4", collation="utf8mb4_bin",
        )
        sql, _ = enum_type.to_sql()
        assert "ENUM('a','b')" in sql
        assert "CHARACTER SET utf8mb4" in sql
        assert "COLLATE utf8mb4_bin" in sql

    def test_enum_requires_non_empty_values(self, dialect):
        with pytest.raises(ValueError):
            MariaDBEnumType(dialect, values=[])
        with pytest.raises(ValueError):
            MariaDBEnumType(dialect, values=None)

    def test_set_type_still_renders_set(self, dialect):
        set_type = MariaDBSetType(dialect, values=["read", "write"])
        sql, _ = set_type.to_sql()
        assert sql == "SET('read','write')"


class TestDialectRangeValidation:
    """Dialect-specific range checks live inside the formatters."""

    def test_decimal_precision_over_65_raises(self, dialect):
        data_type = DecimalType(dialect, 66, 2)
        with pytest.raises(ValueError, match="between 1 and 65"):
            dialect.format_data_type(data_type)

    def test_decimal_scale_over_30_raises(self, dialect):
        data_type = DecimalType(dialect, 65, 31)
        with pytest.raises(ValueError, match="between 0 and 30"):
            dialect.format_data_type(data_type)

    def test_decimal_scale_over_precision_raises(self, dialect):
        data_type = DecimalType(dialect, 10, 11)
        with pytest.raises(ValueError, match="cannot exceed"):
            dialect.format_data_type(data_type)

    def test_decimal_valid_range_renders(self, dialect):
        sql, _ = dialect.format_data_type(DecimalType(dialect, 65, 30))
        assert sql == "DECIMAL(65, 30)"

    def test_float_precision_over_53_raises(self, dialect):
        with pytest.raises(ValueError, match="between 1 and 53"):
            dialect.format_data_type(FloatType(dialect, 54))

    def test_timestamp_precision_over_6_raises(self, dialect):
        with pytest.raises(ValueError, match="between 0 and 6"):
            dialect.format_data_type(TimestampType(dialect, 7))

    def test_timestamp_valid_precision_renders(self, dialect):
        sql, _ = dialect.format_data_type(TimestampType(dialect, 6))
        assert sql == "TIMESTAMP(6)"


class TestDialectOptions:
    """The data-type value objects no longer carry a dialect_options bag."""



    def test_constructor_rejects_dialect_options(self, dialect):
        with pytest.raises(TypeError):
            MariaDBIntType(dialect, unsigned=True, dialect_options={"display_width": 10})

    def test_equality_ignores_dialect(self, dialect):
        other = MariaDBDialect()
        assert MariaDBIntType(dialect, unsigned=True) == MariaDBIntType(other, unsigned=True)

    def test_semantic_params_drive_equality(self, dialect):
        assert MariaDBIntType(dialect, unsigned=True) != MariaDBIntType(dialect)
        assert MariaDBEnumType(dialect, values=["a"]) != MariaDBEnumType(dialect, values=["b"])
        assert MariaDBEnumType(dialect, values=["a"]) == MariaDBEnumType(dialect, values=["a"])
