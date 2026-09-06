# tests/rhosocial/activerecord_mariadb_test/feature/backend/dialect/test_mariadb_type_formatting.py
"""MariaDB DataType formatting, parsing and suggestion tests.

This module covers ``MariaDBTypeSupportMixin`` and
``MariaDBTypeSuggestionMixin``: every ``@DDLTypeMixin.handles`` formatter
dispatched through ``MariaDBDialect.format_data_type``, the ``parse_type``
raw SQL round-trip parser and the ``suggest_column_type`` mapping.
"""
import datetime
import decimal
import enum
import ipaddress
import uuid

import pytest

from rhosocial.activerecord.backend.expression import types as ct
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression import types as mt

VERSION = (10, 11, 0)


def _maria_int(t, unsigned=False, zerofill=False):
    """Set UNSIGNED/ZEROFILL flags on a MariaDB integer type and return it."""
    t.unsigned = unsigned
    t.zerofill = zerofill
    return t


class TestMariaDBIntFormatting:
    """Tests for MariaDB integer type formatters."""

    @pytest.mark.parametrize("type_cls,base", [
        (mt.MariaDBTinyIntType, "TINYINT"),
        (mt.MariaDBSmallIntType, "SMALLINT"),
        (mt.MariaDBIntType, "INT"),
        (mt.MariaDBBigIntType, "BIGINT"),
    ])
    @pytest.mark.parametrize("unsigned,zerofill,suffix", [
        (False, False, ""),
        (True, False, " UNSIGNED"),
        (False, True, " ZEROFILL"),
    ])
    def test_format(self, type_cls, base, unsigned, zerofill, suffix):
        """Test each MariaDB integer formatter with flag combinations."""
        dialect = MariaDBDialect(VERSION)
        sql, params = dialect.format_data_type(
            _maria_int(type_cls(), unsigned=unsigned, zerofill=zerofill)
        )
        assert sql == f"{base}{suffix}", "flag combination must map to the expected suffix"
        assert params == (), "integer types produce no bind parameters"


class TestMariaDBBlobTextFormatting:
    """Tests for MariaDB BLOB / TEXT size variant formatters."""

    @pytest.mark.parametrize("type_cls,expected", [
        (mt.MariaDBTinyBlobType, "TINYBLOB"),
        (mt.MariaDBBlobType, "BLOB"),
        (mt.MariaDBMediumBlobType, "MEDIUMBLOB"),
        (mt.MariaDBLongBlobType, "LONGBLOB"),
        (mt.MariaDBTinyTextType, "TINYTEXT"),
        (mt.MariaDBTextType, "TEXT"),
        (mt.MariaDBMediumTextType, "MEDIUMTEXT"),
        (mt.MariaDBLongTextType, "LONGTEXT"),
    ])
    def test_format(self, type_cls, expected):
        """Test a BLOB/TEXT size variant renders its keyword."""
        dialect = MariaDBDialect(VERSION)
        sql, params = dialect.format_data_type(type_cls())
        assert sql == expected, "size variant must render its exact keyword"
        assert params == (), "blob/text types produce no bind parameters"


class TestMariaDBBitYearBinaryFormatting:
    """Tests for MariaDB BIT / YEAR / BINARY / VARBINARY formatters."""

    def test_bit_plain(self):
        """Test BIT without a length."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBBitType())
        assert sql == "BIT", "BIT without n must render bare BIT"

    def test_bit_with_n(self):
        """Test BIT with a length n."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBBitType(n=8))
        assert sql == "BIT(8)", "BIT with n must render BIT(n)"

    def test_year_plain(self):
        """Test YEAR without a display width."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBYearType())
        assert sql == "YEAR", "YEAR without display width must render bare YEAR"

    def test_year_with_width(self):
        """Test YEAR with a display width."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBYearType(display_width=4))
        assert sql == "YEAR(4)", "YEAR with display width must render YEAR(4)"

    def test_binary_plain(self):
        """Test BINARY without a length."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBBinaryType())
        assert sql == "BINARY", "BINARY without length must render bare BINARY"

    def test_binary_with_length(self):
        """Test BINARY with a length."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBBinaryType(length=16))
        assert sql == "BINARY(16)", "BINARY with length must render BINARY(n)"

    def test_var_binary_plain(self):
        """Test VARBINARY without a length."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBVarBinaryType())
        assert sql == "VARBINARY", "VARBINARY without length must render bare VARBINARY"

    def test_var_binary_with_length(self):
        """Test VARBINARY with a length."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBVarBinaryType(length=32))
        assert sql == "VARBINARY(32)", "VARBINARY with length must render VARBINARY(n)"


class TestMariaDBEnumSetFormatting:
    """Tests for MariaDB ENUM / SET formatters."""

    def test_enum_plain(self):
        """Test ENUM with values only."""
        dialect = MariaDBDialect(VERSION)
        sql, params = dialect.format_data_type(mt.MariaDBEnumType(values=["a", "b"]))
        assert sql == "ENUM('a','b')", "ENUM values must be quoted and comma-joined"
        assert params == (), "ENUM produces no bind parameters"

    def test_enum_charset(self):
        """Test ENUM with a CHARACTER SET."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBEnumType(values=["a"], charset="utf8mb4"))
        assert sql == "ENUM('a') CHARACTER SET utf8mb4", "ENUM charset must be appended"

    def test_enum_collation(self):
        """Test ENUM with a COLLATE."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBEnumType(values=["a"], collation="utf8mb4_bin"))
        assert sql == "ENUM('a') COLLATE utf8mb4_bin", "ENUM collation must be appended"

    def test_set_plain(self):
        """Test SET with values only."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBSetType(values=["x", "y"]))
        assert sql == "SET('x','y')", "SET values must be quoted and comma-joined"

    def test_set_charset(self):
        """Test SET with a CHARACTER SET."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBSetType(values=["x"], charset="utf8mb4"))
        assert sql == "SET('x') CHARACTER SET utf8mb4", "SET charset must be appended"

    def test_set_collation(self):
        """Test SET with a COLLATE."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(mt.MariaDBSetType(values=["x"], collation="utf8mb4_bin"))
        assert sql == "SET('x') COLLATE utf8mb4_bin", "SET collation must be appended"


class TestMariaDBSpatialFormatting:
    """Tests for MariaDB spatial type formatters."""

    @pytest.mark.parametrize("type_cls,expected", [
        (mt.MariaDBGeometryType, "GEOMETRY"),
        (mt.MariaDBPointType, "POINT"),
        (mt.MariaDBLineStringType, "LINESTRING"),
        (mt.MariaDBPolygonType, "POLYGON"),
        (mt.MariaDBMultiPointType, "MULTIPOINT"),
        (mt.MariaDBMultiLineStringType, "MULTILINESTRING"),
        (mt.MariaDBMultiPolygonType, "MULTIPOLYGON"),
        (mt.MariaDBGeometryCollectionType, "GEOMETRYCOLLECTION"),
    ])
    def test_plain(self, type_cls, expected):
        """Test a spatial type without SRID."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(type_cls())
        assert sql == expected, "spatial type must render its bare keyword"

    @pytest.mark.parametrize("type_cls,expected", [
        (mt.MariaDBGeometryType, "GEOMETRY SRID 4326"),
        (mt.MariaDBPointType, "POINT SRID 4326"),
        (mt.MariaDBLineStringType, "LINESTRING SRID 4326"),
        (mt.MariaDBPolygonType, "POLYGON SRID 4326"),
        (mt.MariaDBMultiPointType, "MULTIPOINT SRID 4326"),
        (mt.MariaDBMultiLineStringType, "MULTILINESTRING SRID 4326"),
        (mt.MariaDBMultiPolygonType, "MULTIPOLYGON SRID 4326"),
        (mt.MariaDBGeometryCollectionType, "GEOMETRYCOLLECTION SRID 4326"),
    ])
    def test_with_srid(self, type_cls, expected):
        """Test a spatial type with an SRID."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(type_cls(srid=4326))
        assert sql == expected, "SRID qualifier must be appended"


class TestCoreTypeFormatting:
    """Tests for core (generic) type formatters overridden by MariaDB."""

    @pytest.mark.parametrize("type_cls,expected", [
        (ct.DoubleType, "DOUBLE"),
        (ct.BooleanType, "TINYINT(1)"),
        (ct.IntegerType, "INT"),
        (ct.BigIntType, "BIGINT"),
        (ct.SmallIntType, "SMALLINT"),
        (ct.TinyIntType, "TINYINT"),
        (ct.TextType, "TEXT"),
        (ct.DateType, "DATE"),
        (ct.RealType, "REAL"),
        (ct.JsonType, "JSON"),
        (ct.UUIDType, "VARCHAR(36)"),
        (ct.InetType, "VARBINARY(16)"),
        (ct.CidrType, "VARCHAR(45)"),
        (ct.MacAddrType, "BINARY(6)"),
        (ct.BlobType, "BLOB"),
    ])
    def test_fixed(self, type_cls, expected):
        """Test a core type with a fixed SQL rendering."""
        dialect = MariaDBDialect(VERSION)
        sql, params = dialect.format_data_type(type_cls())
        assert sql == expected, "core type must render the MariaDB-specific form"
        assert params == (), "core types produce no bind parameters"

    @pytest.mark.parametrize("type_cls,kwargs,expected", [
        (ct.VarCharType, {}, "VARCHAR"),
        (ct.VarCharType, {"length": 100}, "VARCHAR(100)"),
        (ct.CharType, {}, "CHAR"),
        (ct.CharType, {"length": 10}, "CHAR(10)"),
        (ct.DateTimeType, {}, "DATETIME"),
        (ct.DateTimeType, {"precision": 6}, "DATETIME(6)"),
        (ct.TimeType, {}, "TIME"),
        (ct.TimeType, {"precision": 3}, "TIME(3)"),
        (ct.TimestampType, {}, "TIMESTAMP"),
        (ct.TimestampType, {"precision": 3}, "TIMESTAMP(3)"),
        (ct.FloatType, {}, "FLOAT"),
        (ct.FloatType, {"precision": 10}, "FLOAT(10)"),
    ])
    def test_optional_arg(self, type_cls, kwargs, expected):
        """Test a core type with and without its optional argument."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(type_cls(**kwargs))
        assert sql == expected, "optional argument must toggle the parenthesized form"

    def test_decimal_precision_scale(self):
        """Test DECIMAL with precision and scale."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(ct.DecimalType(precision=10, scale=2))
        assert sql == "DECIMAL(10, 2)", "DECIMAL(p, s) must render both parts"

    def test_decimal_precision_only(self):
        """Test DECIMAL with precision only."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(ct.DecimalType(precision=10))
        assert sql == "DECIMAL(10)", "DECIMAL(p) must render only precision"

    def test_decimal_plain(self):
        """Test DECIMAL with no arguments."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(ct.DecimalType())
        assert sql == "DECIMAL", "DECIMAL without args must render bare DECIMAL"

    def test_core_binary(self):
        """Test core BinaryType renders BINARY(n)."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(ct.BinaryType(length=16))
        assert sql == "BINARY(16)", "core BINARY must render BINARY(n)"

    def test_core_var_binary(self):
        """Test core VarBinaryType renders VARBINARY(n)."""
        dialect = MariaDBDialect(VERSION)
        sql, _ = dialect.format_data_type(ct.VarBinaryType(length=32))
        assert sql == "VARBINARY(32)", "core VARBINARY must render VARBINARY(n)"


class TestParseType:
    """Tests for the raw SQL type parser."""

    @pytest.mark.parametrize("raw,expected", [
        ("BIT", mt.MariaDBBitType),
        ("BIT(8)", mt.MariaDBBitType),
    ])
    def test_bit(self, raw, expected):
        """Test BIT parsing captures the optional length."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type(raw)
        assert isinstance(result, expected), "BIT must parse to MariaDBBitType"
        assert result.n == (8 if raw == "BIT(8)" else None), "bit length must be extracted"

    def test_tinyint_boolean(self):
        """Test TINYINT(1) parses to BooleanType."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("TINYINT(1)")
        assert isinstance(result, ct.BooleanType), "TINYINT(1) must map to BooleanType"

    def test_tinyint_unsigned(self):
        """Test TINYINT UNSIGNED parses with the unsigned flag."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("TINYINT UNSIGNED")
        assert isinstance(result, mt.MariaDBTinyIntType), "TINYINT must parse to MariaDBTinyIntType"
        assert result.unsigned is True, "unsigned flag must be captured"
        assert result.zerofill is False, "zerofill must default to False"

    def test_tinyint_display_width(self):
        """Test TINYINT(4) keeps a non-boolean display width."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("TINYINT(4)")
        assert isinstance(result, mt.MariaDBTinyIntType), "TINYINT(4) must stay an int type"

    @pytest.mark.parametrize("raw,expected", [
        ("SMALLINT UNSIGNED", mt.MariaDBSmallIntType),
        ("MEDIUMINT ZEROFILL", mt.MariaDBIntType),
        ("BIGINT UNSIGNED", mt.MariaDBBigIntType),
        ("INT", mt.MariaDBIntType),
        ("INTEGER UNSIGNED", mt.MariaDBIntType),
    ])
    def test_integer_variants(self, raw, expected):
        """Test integer-family parsing returns the matching MariaDB type."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type(raw)
        assert isinstance(result, expected), f"{raw} must parse to {expected.__name__}"

    def test_float_precision(self):
        """Test FLOAT parsing captures precision."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("FLOAT(10,2)")
        assert isinstance(result, ct.FloatType), "FLOAT must parse to FloatType"
        assert result.precision == 10, "FLOAT precision must be extracted"

    def test_real(self):
        """Test REAL parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("REAL")
        assert isinstance(result, ct.RealType), "REAL must parse to RealType"

    def test_double(self):
        """Test DOUBLE parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("DOUBLE")
        assert isinstance(result, ct.DoubleType), "DOUBLE must parse to DoubleType"

    def test_decimal_precision_scale(self):
        """Test DECIMAL(10,2) parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("DECIMAL(10,2)")
        assert isinstance(result, ct.DecimalType), "DECIMAL must parse to DecimalType"
        assert result.precision == 10, "decimal precision must be extracted"
        assert result.scale == 2, "decimal scale must be extracted"

    @pytest.mark.parametrize("raw,expected_precision", [
        ("DECIMAL(10)", 10),
        ("NUMERIC(5)", 5),
        ("FIXED(10,2)", 10),
        ("DECIMAL", None),
    ])
    def test_decimal_variants(self, raw, expected_precision):
        """Test DECIMAL/NUMERIC/FIXED parsing variants."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type(raw)
        assert isinstance(result, ct.DecimalType), "decimal-family must parse to DecimalType"
        assert result.precision == expected_precision, "decimal precision must be extracted"

    @pytest.mark.parametrize("raw,expected", [
        ("TINYTEXT", mt.MariaDBTinyTextType),
        ("MEDIUMTEXT", mt.MariaDBMediumTextType),
        ("LONGTEXT", mt.MariaDBLongTextType),
        ("TEXT", mt.MariaDBTextType),
    ])
    def test_text_variants(self, raw, expected):
        """Test TEXT size variant parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type(raw)
        assert isinstance(result, expected), f"{raw} must parse to {expected.__name__}"

    def test_enum_with_options(self):
        """Test ENUM parsing with values, charset and collation."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("ENUM('a','b') CHARACTER SET utf8mb4 COLLATE utf8mb4_bin")
        assert isinstance(result, mt.MariaDBEnumType), "ENUM must parse to MariaDBEnumType"
        assert result.values == ["a", "b"], "ENUM values must be extracted"
        assert result.charset == "UTF8MB4", "ENUM charset must be captured"
        assert result.collation == "UTF8MB4_BIN", "ENUM collation must be captured"

    def test_enum_plain(self):
        """Test ENUM parsing with values only (no charset/collation)."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("ENUM('a','b')")
        assert isinstance(result, mt.MariaDBEnumType), "ENUM must parse to MariaDBEnumType"
        assert result.values == ["a", "b"], "ENUM values must be extracted"
        assert result.charset is None, "ENUM charset must default to None"
        assert result.collation is None, "ENUM collation must default to None"

    def test_enum_charset_only(self):
        """Test ENUM parsing with a charset but no collation."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("ENUM('a') CHARACTER SET utf8mb4")
        assert isinstance(result, mt.MariaDBEnumType), "ENUM must parse to MariaDBEnumType"
        assert result.charset == "UTF8MB4", "ENUM charset must be captured"
        assert result.collation is None, "ENUM collation must default to None"

    def test_set_plain(self):
        """Test SET parsing with values only."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("SET('x','y')")
        assert isinstance(result, mt.MariaDBSetType), "SET must parse to MariaDBSetType"
        assert result.values == ["x", "y"], "SET values must be extracted"

    def test_set_with_options(self):
        """Test SET parsing with charset and collation."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("SET('x') CHARACTER SET utf8mb4 COLLATE utf8mb4_bin")
        assert isinstance(result, mt.MariaDBSetType), "SET must parse to MariaDBSetType"
        assert result.values == ["x"], "SET values must be extracted"
        assert result.charset == "UTF8MB4", "SET charset must be captured"
        assert result.collation == "UTF8MB4_BIN", "SET collation must be captured"

    def test_binary_length(self):
        """Test BINARY(16) parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("BINARY(16)")
        assert isinstance(result, mt.MariaDBBinaryType), "BINARY must parse to MariaDBBinaryType"
        assert result.length == 16, "binary length must be extracted"

    def test_var_binary_length(self):
        """Test VARBINARY(32) parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("VARBINARY(32)")
        assert isinstance(result, mt.MariaDBVarBinaryType), "VARBINARY must parse to MariaDBVarBinaryType"
        assert result.length == 32, "varbinary length must be extracted"

    def test_varchar_length(self):
        """Test VARCHAR(255) parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("VARCHAR(255)")
        assert isinstance(result, ct.VarCharType), "VARCHAR must parse to VarCharType"
        assert result.length == 255, "varchar length must be extracted"

    def test_char_length(self):
        """Test CHAR(10) parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("CHAR(10)")
        assert isinstance(result, ct.CharType), "CHAR must parse to CharType"
        assert result.length == 10, "char length must be extracted"

    @pytest.mark.parametrize("raw,expected", [
        ("TINYBLOB", mt.MariaDBTinyBlobType),
        ("MEDIUMBLOB", mt.MariaDBMediumBlobType),
        ("LONGBLOB", mt.MariaDBLongBlobType),
        ("BLOB", mt.MariaDBBlobType),
    ])
    def test_blob_variants(self, raw, expected):
        """Test BLOB size variant parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type(raw)
        assert isinstance(result, expected), f"{raw} must parse to {expected.__name__}"

    def test_year(self):
        """Test YEAR(4) parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("YEAR(4)")
        assert isinstance(result, mt.MariaDBYearType), "YEAR must parse to MariaDBYearType"
        assert result.display_width == 4, "year display width must be extracted"

    @pytest.mark.parametrize("raw,expected", [
        ("DATE", ct.DateType),
        ("DATETIME", ct.DateTimeType),
        ("DATETIME(6)", ct.DateTimeType),
        ("TIME", ct.TimeType),
        ("TIME(3)", ct.TimeType),
        ("TIMESTAMP", ct.TimestampType),
        ("TIMESTAMP(3)", ct.TimestampType),
    ])
    def test_datetime_family(self, raw, expected):
        """Test date/time family parsing maps to the expected type."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type(raw)
        assert isinstance(result, expected), f"{raw} must parse to {expected.__name__}"

    def test_timestamp_with_time_zone(self):
        """Test TIMESTAMP WITH TIME ZONE parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("TIMESTAMP(3) WITH TIME ZONE")
        assert isinstance(result, ct.TimestampTzType), "TZ timestamp must parse to TimestampTzType"
        assert result.precision == 3, "timestamp precision must be extracted"

    def test_time_with_time_zone(self):
        """Test TIME WITH TIME ZONE parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("TIME WITH TIME ZONE")
        assert isinstance(result, ct.TimeTzType), "TZ time must parse to TimeTzType"

    def test_json(self):
        """Test JSON parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("JSON")
        assert isinstance(result, ct.JsonType), "JSON must parse to JsonType"

    @pytest.mark.parametrize("raw,expected", [
        ("GEOMETRY", mt.MariaDBGeometryType),
        ("POINT", mt.MariaDBPointType),
        ("LINESTRING", mt.MariaDBLineStringType),
        ("POLYGON", mt.MariaDBPolygonType),
        ("MULTIPOINT", mt.MariaDBMultiPointType),
        ("MULTILINESTRING", mt.MariaDBMultiLineStringType),
        ("MULTIPOLYGON", mt.MariaDBMultiPolygonType),
    ])
    def test_spatial(self, raw, expected):
        """Test spatial type parsing."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type(raw)
        assert isinstance(result, expected), f"{raw} must parse to {expected.__name__}"

    def test_spatial_srid(self):
        """Test spatial parsing captures SRID."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("POINT SRID 4326")
        assert isinstance(result, mt.MariaDBPointType), "POINT must parse to MariaDBPointType"
        assert result.srid == 4326, "SRID must be extracted"

    def test_geometry_collection_prefix(self):
        """Test GEOMETRYCOLLECTION matches the GEOMETRY prefix handler."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("GEOMETRYCOLLECTION")
        assert isinstance(result, mt.MariaDBGeometryType), \
            "GEOMETRYCOLLECTION is absorbed by the GEOMETRY prefix handler"

    def test_custom_type_fallback(self):
        """Test an unknown type falls back to CustomType."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.parse_type("MYCUSTOMTYPE")
        assert isinstance(result, ct.CustomType), "unknown types must parse to CustomType"
        assert result.raw == "MYCUSTOMTYPE", "custom type must retain the raw SQL"


class TestSuggestColumnType:
    """Tests for MariaDB type suggestions."""

    @pytest.mark.parametrize("py_type,expected", [
        (str, mt.MariaDBTextType),
        (int, mt.MariaDBIntType),
        (bool, mt.MariaDBTinyIntType),
        (float, ct.DoubleType),
        (bytes, mt.MariaDBBlobType),
        (datetime.datetime, ct.DateTimeType),
        (datetime.date, ct.DateType),
        (datetime.time, ct.TimeType),
        (decimal.Decimal, ct.DecimalType),
        (uuid.UUID, ct.UUIDType),
        (ipaddress.IPv4Address, ct.InetType),
        (ipaddress.IPv6Address, ct.InetType),
        (ipaddress.IPv4Network, ct.CidrType),
        (ipaddress.IPv6Network, ct.CidrType),
    ])
    def test_mapping(self, py_type, expected):
        """Test the Python-type to DataType mapping."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.suggest_column_type(py_type)
        assert isinstance(result, expected), f"{py_type.__name__} must suggest {expected.__name__}"

    def test_enum(self):
        """Test Enum suggestions use VARCHAR(64)."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.suggest_column_type(enum.Enum)
        assert isinstance(result, ct.VarCharType), "Enum must suggest VarCharType"
        assert result.length == 64, "Enum suggestion must use VARCHAR(64)"

    @pytest.mark.parametrize("py_type", [dict, list, set, frozenset, tuple])
    def test_json_types_supported_version(self, py_type):
        """Test dict/list/set/tuple suggest JSON on MariaDB >= 10.2.7."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.suggest_column_type(py_type)
        assert isinstance(result, ct.JsonType), f"{py_type.__name__} must suggest JsonType"

    @pytest.mark.parametrize("py_type", [dict, list])
    def test_json_types_old_version(self, py_type):
        """Test dict/list suggest LONGTEXT before MariaDB 10.2.7."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.suggest_column_type(py_type, (10, 2, 0))
        assert isinstance(result, mt.MariaDBLongTextType), \
            "pre-JSON versions must suggest MariaDBLongTextType"

    @pytest.mark.parametrize("py_type", [dict, list])
    def test_json_types_unknown_version(self, py_type):
        """Test dict/list return None when the version is unknown."""
        dialect = MariaDBDialect()
        result = dialect.suggest_column_type(py_type, None)
        assert result is None, "unknown version must produce no suggestion"

    def test_no_version_dialect(self):
        """Test a versionless dialect returns None for version-gated types."""
        dialect = MariaDBDialect()
        result = dialect.suggest_column_type(dict)
        assert result is None, "dialect without a version must not guess"

    def test_fallback_to_base(self):
        """Test unmapped types fall back to the base neutral suggestion."""
        dialect = MariaDBDialect(VERSION)
        result = dialect.suggest_column_type(complex)
        assert result is None, "unmapped Python types produce no suggestion"