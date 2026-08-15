# src/rhosocial/activerecord/backend/impl/mariadb/mixins/types.py
"""MariaDB DataType formatting and parsing mixin."""

from __future__ import annotations

import re
from typing import Tuple

from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    DataType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    JsonBType,
    JsonType,
    RealType,
    SmallIntType,
    TextType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    TinyIntType,
    VarCharType,
)
from ..expression.types import (
    MariaDBBigIntType,
    MariaDBBinaryType,
    MariaDBBitType,
    MariaDBBlobType,
    MariaDBEnumType,
    MariaDBGeometryCollectionType,
    MariaDBGeometryType,
    MariaDBIntType,
    MariaDBLineStringType,
    MariaDBLongBlobType,
    MariaDBLongTextType,
    MariaDBMediumBlobType,
    MariaDBMediumTextType,
    MariaDBMultiLineStringType,
    MariaDBMultiPointType,
    MariaDBMultiPolygonType,
    MariaDBPointType,
    MariaDBPolygonType,
    MariaDBSetType,
    MariaDBSmallIntType,
    MariaDBTextType,
    MariaDBTinyBlobType,
    MariaDBTinyIntType,
    MariaDBTinyTextType,
    MariaDBVarBinaryType,
    MariaDBYearType,
)


class MariaDBTypeSupportMixin(DDLTypeMixin):
    """MariaDB DataType formatting and parsing.

    Implements ``DDLTypeSupport`` so the dialect can render ``DataType``
    expressions to SQL strings and parse raw SQL type strings back into
    ``DataType`` instances.
    """

    # ------------------------------------------------------------------
    # MariaDB-specific type formatters
    # ------------------------------------------------------------------

    @DDLTypeMixin.handles(MariaDBTinyIntType)
    def format_data_type_tiny_int(self, data_type: MariaDBTinyIntType) -> Tuple[str, tuple]:
        sql = "TINYINT"
        if data_type.zerofill:
            return f"{sql} ZEROFILL", ()
        if data_type.unsigned:
            return f"{sql} UNSIGNED", ()
        return sql, ()

    @DDLTypeMixin.handles(MariaDBSmallIntType)
    def format_data_type_small_int(self, data_type: MariaDBSmallIntType) -> Tuple[str, tuple]:
        sql = "SMALLINT"
        if data_type.zerofill:
            return f"{sql} ZEROFILL", ()
        if data_type.unsigned:
            return f"{sql} UNSIGNED", ()
        return sql, ()

    @DDLTypeMixin.handles(MariaDBIntType)
    def format_data_type_int(self, data_type: MariaDBIntType) -> Tuple[str, tuple]:
        sql = "INT"
        if data_type.zerofill:
            return f"{sql} ZEROFILL", ()
        if data_type.unsigned:
            return f"{sql} UNSIGNED", ()
        return sql, ()

    @DDLTypeMixin.handles(MariaDBBigIntType)
    def format_data_type_big_int(self, data_type: MariaDBBigIntType) -> Tuple[str, tuple]:
        sql = "BIGINT"
        if data_type.zerofill:
            return f"{sql} ZEROFILL", ()
        if data_type.unsigned:
            return f"{sql} UNSIGNED", ()
        return sql, ()

    @DDLTypeMixin.handles(MariaDBTinyBlobType)
    def format_data_type_tiny_blob(self, data_type: MariaDBTinyBlobType) -> Tuple[str, tuple]:
        return "TINYBLOB", ()

    @DDLTypeMixin.handles(MariaDBBlobType)
    def format_data_type_blob(self, data_type: MariaDBBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    @DDLTypeMixin.handles(MariaDBMediumBlobType)
    def format_data_type_medium_blob(self, data_type: MariaDBMediumBlobType) -> Tuple[str, tuple]:
        return "MEDIUMBLOB", ()

    @DDLTypeMixin.handles(MariaDBLongBlobType)
    def format_data_type_long_blob(self, data_type: MariaDBLongBlobType) -> Tuple[str, tuple]:
        return "LONGBLOB", ()

    @DDLTypeMixin.handles(MariaDBTinyTextType)
    def format_data_type_tiny_text(self, data_type: MariaDBTinyTextType) -> Tuple[str, tuple]:
        return "TINYTEXT", ()

    @DDLTypeMixin.handles(MariaDBTextType)
    def format_data_type_text(self, data_type: MariaDBTextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    @DDLTypeMixin.handles(MariaDBMediumTextType)
    def format_data_type_medium_text(self, data_type: MariaDBMediumTextType) -> Tuple[str, tuple]:
        return "MEDIUMTEXT", ()

    @DDLTypeMixin.handles(MariaDBLongTextType)
    def format_data_type_long_text(self, data_type: MariaDBLongTextType) -> Tuple[str, tuple]:
        return "LONGTEXT", ()

    @DDLTypeMixin.handles(MariaDBBitType)
    def format_data_type_bit(self, data_type: MariaDBBitType) -> Tuple[str, tuple]:
        if data_type.n is not None:
            return f"BIT({data_type.n})", ()
        return "BIT", ()

    @DDLTypeMixin.handles(MariaDBYearType)
    def format_data_type_year(self, data_type: MariaDBYearType) -> Tuple[str, tuple]:
        if data_type.display_width is not None:
            return f"YEAR({data_type.display_width})", ()
        return "YEAR", ()

    @DDLTypeMixin.handles(MariaDBBinaryType)
    def format_data_type_binary(self, data_type: MariaDBBinaryType) -> Tuple[str, tuple]:
        if data_type.length is not None:
            return f"BINARY({data_type.length})", ()
        return "BINARY", ()

    @DDLTypeMixin.handles(MariaDBVarBinaryType)
    def format_data_type_var_binary(self, data_type: MariaDBVarBinaryType) -> Tuple[str, tuple]:
        if data_type.length is not None:
            return f"VARBINARY({data_type.length})", ()
        return "VARBINARY", ()

    @DDLTypeMixin.handles(MariaDBEnumType)
    def format_data_type_enum(self, data_type: MariaDBEnumType) -> Tuple[str, tuple]:
        values_str = ",".join(f"'{v}'" for v in data_type.values)
        result = f"ENUM({values_str})"
        if data_type.charset:
            result += f" CHARACTER SET {data_type.charset}"
        if data_type.collation:
            result += f" COLLATE {data_type.collation}"
        return result, ()

    @DDLTypeMixin.handles(MariaDBSetType)
    def format_data_type_set(self, data_type: MariaDBSetType) -> Tuple[str, tuple]:
        values_str = ",".join(f"'{v}'" for v in data_type.values)
        result = f"SET({values_str})"
        if data_type.charset:
            result += f" CHARACTER SET {data_type.charset}"
        if data_type.collation:
            result += f" COLLATE {data_type.collation}"
        return result, ()

    @DDLTypeMixin.handles(MariaDBGeometryType)
    def format_data_type_geometry(self, data_type: MariaDBGeometryType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"GEOMETRY SRID {data_type.srid}", ()
        return "GEOMETRY", ()

    @DDLTypeMixin.handles(MariaDBPointType)
    def format_data_type_point(self, data_type: MariaDBPointType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"POINT SRID {data_type.srid}", ()
        return "POINT", ()

    @DDLTypeMixin.handles(MariaDBLineStringType)
    def format_data_type_line_string(self, data_type: MariaDBLineStringType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"LINESTRING SRID {data_type.srid}", ()
        return "LINESTRING", ()

    @DDLTypeMixin.handles(MariaDBPolygonType)
    def format_data_type_polygon(self, data_type: MariaDBPolygonType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"POLYGON SRID {data_type.srid}", ()
        return "POLYGON", ()

    @DDLTypeMixin.handles(MariaDBMultiPointType)
    def format_data_type_multi_point(self, data_type: MariaDBMultiPointType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"MULTIPOINT SRID {data_type.srid}", ()
        return "MULTIPOINT", ()

    @DDLTypeMixin.handles(MariaDBMultiLineStringType)
    def format_data_type_multi_line_string(self, data_type: MariaDBMultiLineStringType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"MULTILINESTRING SRID {data_type.srid}", ()
        return "MULTILINESTRING", ()

    @DDLTypeMixin.handles(MariaDBMultiPolygonType)
    def format_data_type_multi_polygon(self, data_type: MariaDBMultiPolygonType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"MULTIPOLYGON SRID {data_type.srid}", ()
        return "MULTIPOLYGON", ()

    @DDLTypeMixin.handles(MariaDBGeometryCollectionType)
    def format_data_type_geometry_collection(self, data_type: MariaDBGeometryCollectionType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"GEOMETRYCOLLECTION SRID {data_type.srid}", ()
        return "GEOMETRYCOLLECTION", ()

    # --- Core type overrides (MariaDB/MySQL shared SQL) ---

    @DDLTypeMixin.handles(DoubleType)
    def format_data_type_double(self, data_type: DoubleType) -> Tuple[str, tuple]:
        return "DOUBLE", ()

    @DDLTypeMixin.handles(BooleanType)
    def format_data_type_boolean(self, data_type: BooleanType) -> Tuple[str, tuple]:
        return "TINYINT(1)", ()

    @DDLTypeMixin.handles(TimeTzType)
    def format_data_type_timetz(self, data_type: TimeTzType) -> Tuple[str, tuple]:
        return (f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"), ()

    @DDLTypeMixin.handles(TimestampTzType)
    def format_data_type_timestamptz(self, data_type: TimestampTzType) -> Tuple[str, tuple]:
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    @DDLTypeMixin.handles(JsonBType)
    def format_data_type_jsonb(self, data_type: JsonBType) -> Tuple[str, tuple]:
        return "JSON", ()

    # --- Core type handlers ---

    @DDLTypeMixin.handles(IntegerType)
    def format_data_type_integer(self, data_type: IntegerType) -> Tuple[str, tuple]:
        return "INT", ()

    @DDLTypeMixin.handles(BigIntType)
    def format_data_type_bigint(self, data_type: BigIntType) -> Tuple[str, tuple]:
        return "BIGINT", ()

    @DDLTypeMixin.handles(SmallIntType)
    def format_data_type_smallint(self, data_type: SmallIntType) -> Tuple[str, tuple]:
        return "SMALLINT", ()

    @DDLTypeMixin.handles(TinyIntType)
    def format_data_type_tinyint(self, data_type: TinyIntType) -> Tuple[str, tuple]:
        return "TINYINT", ()

    @DDLTypeMixin.handles(VarCharType)
    def format_data_type_varchar(self, data_type: VarCharType) -> Tuple[str, tuple]:
        return (f"VARCHAR({data_type.length})" if data_type.length is not None else "VARCHAR"), ()

    @DDLTypeMixin.handles(CharType)
    def format_data_type_char(self, data_type: CharType) -> Tuple[str, tuple]:
        return (f"CHAR({data_type.length})" if data_type.length is not None else "CHAR"), ()

    @DDLTypeMixin.handles(TextType)
    def format_data_type_text_core(self, data_type: TextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    @DDLTypeMixin.handles(DateTimeType)
    def format_data_type_datetime(self, data_type: DateTimeType) -> Tuple[str, tuple]:
        return (f"DATETIME({data_type.precision})" if data_type.precision is not None else "DATETIME"), ()

    @DDLTypeMixin.handles(DateType)
    def format_data_type_date(self, data_type: DateType) -> Tuple[str, tuple]:
        return "DATE", ()

    @DDLTypeMixin.handles(TimeType)
    def format_data_type_time(self, data_type: TimeType) -> Tuple[str, tuple]:
        return (f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"), ()

    @DDLTypeMixin.handles(TimestampType)
    def format_data_type_timestamp(self, data_type: TimestampType) -> Tuple[str, tuple]:
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    @DDLTypeMixin.handles(FloatType)
    def format_data_type_float(self, data_type: FloatType) -> Tuple[str, tuple]:
        return (f"FLOAT({data_type.precision})" if data_type.precision is not None else "FLOAT"), ()

    @DDLTypeMixin.handles(RealType)
    def format_data_type_real(self, data_type: RealType) -> Tuple[str, tuple]:
        return "REAL", ()

    @DDLTypeMixin.handles(DecimalType)
    def format_data_type_decimal(self, data_type: DecimalType) -> Tuple[str, tuple]:
        if data_type.precision is not None and data_type.scale is not None:
            return f"DECIMAL({data_type.precision}, {data_type.scale})", ()
        if data_type.precision is not None:
            return f"DECIMAL({data_type.precision})", ()
        return "DECIMAL", ()

    @DDLTypeMixin.handles(JsonType)
    def format_data_type_json(self, data_type: JsonType) -> Tuple[str, tuple]:
        return "JSON", ()

    @DDLTypeMixin.handles(BlobType)
    def format_data_type_blob_core(self, data_type: BlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    # ------------------------------------------------------------------
    # DDLTypeSupport — parsing
    # ------------------------------------------------------------------

    _MARIA_INTEGER_TYPES = re.compile(
        r"^(?:TINYINT|SMALLINT|MEDIUMINT|INT|INTEGER|BIGINT)\b",
        re.IGNORECASE,
    )
    _MARIA_FLOAT_TYPES = re.compile(
        r"^(?:FLOAT|REAL|DOUBLE)\b",
        re.IGNORECASE,
    )
    _MARIA_DECIMAL_TYPES = re.compile(
        r"^(?:DECIMAL|NUMERIC|FIXED)\b",
        re.IGNORECASE,
    )
    _MARIA_STRING_TYPES = re.compile(
        r"^(?:CHAR|VARCHAR|TEXT|TINYTEXT|MEDIUMTEXT|LONGTEXT|"
        r"ENUM|SET|BINARY|VARBINARY)\b",
        re.IGNORECASE,
    )
    _MARIA_BLOB_TYPES = re.compile(
        r"^(?:BLOB|TINYBLOB|MEDIUMBLOB|LONGBLOB)\b",
        re.IGNORECASE,
    )
    _MARIA_DATE_TYPES = re.compile(
        r"^(?:DATE|DATETIME|TIMESTAMP|TIME|YEAR)\b",
        re.IGNORECASE,
    )
    _MARIA_JSON_TYPES = re.compile(
        r"^(?:JSON)\b",
        re.IGNORECASE,
    )
    _MARIA_SPATIAL_TYPES = re.compile(
        r"^(?:GEOMETRY|POINT|LINESTRING|POLYGON|"
        r"MULTIPOINT|MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)\b",
        re.IGNORECASE,
    )
    _MARIA_BIT_TYPES = re.compile(
        r"^(?:BIT)\b",
        re.IGNORECASE,
    )

    def parse_type(self, raw: str) -> DataType:
        stripped = raw.strip()
        upper = stripped.upper()

        if self._MARIA_BIT_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            n = int(nums[0]) if nums else None
            from ..expression.types import MariaDBBitType
            return MariaDBBitType(n)

        if self._MARIA_INTEGER_TYPES.match(upper):
            unsigned = "UNSIGNED" in upper
            zerofill = "ZEROFILL" in upper
            if upper.startswith("TINYINT"):
                nums = re.findall(r"\d+", stripped)
                display_width = int(nums[0]) if nums else None
                from ..expression.types import MariaDBTinyIntType
                t = MariaDBTinyIntType()
                t.unsigned = unsigned
                t.zerofill = zerofill
                if display_width == 1 and not unsigned and not zerofill:
                    return BooleanType()
                return t
            if upper.startswith("SMALLINT"):
                from ..expression.types import MariaDBSmallIntType
                t = MariaDBSmallIntType()
                t.unsigned = unsigned
                t.zerofill = zerofill
                return t
            if upper.startswith("MEDIUMINT"):
                from ..expression.types import MariaDBIntType
                t = MariaDBIntType()
                t.unsigned = unsigned
                t.zerofill = zerofill
                return t
            if upper.startswith("BIGINT"):
                from ..expression.types import MariaDBBigIntType
                t = MariaDBBigIntType()
                t.unsigned = unsigned
                t.zerofill = zerofill
                return t
            from ..expression.types import MariaDBIntType
            t = MariaDBIntType()
            t.unsigned = unsigned
            t.zerofill = zerofill
            return t

        if self._MARIA_FLOAT_TYPES.match(upper):
            if upper.startswith("DOUBLE"):
                return DoubleType()
            if upper.startswith("REAL"):
                return RealType()
            nums = re.findall(r"\d+", stripped)
            precision = int(nums[0]) if nums else None
            return FloatType(precision)

        if self._MARIA_DECIMAL_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return DecimalType(int(nums[0]), int(nums[1]))
            if len(nums) == 1:
                return DecimalType(int(nums[0]))
            return DecimalType()

        if self._MARIA_STRING_TYPES.match(upper):
            if upper.startswith("TINYTEXT"):
                from ..expression.types import MariaDBTinyTextType
                return MariaDBTinyTextType()
            if upper.startswith("MEDIUMTEXT"):
                from ..expression.types import MariaDBMediumTextType
                return MariaDBMediumTextType()
            if upper.startswith("LONGTEXT"):
                from ..expression.types import MariaDBLongTextType
                return MariaDBLongTextType()
            if upper.startswith("TEXT"):
                from ..expression.types import MariaDBTextType
                return MariaDBTextType()
            if upper.startswith("ENUM"):
                from ..expression.types import MariaDBEnumType
                values = re.findall(r"'([^']*)'", stripped)
                charset = None
                collation = None
                cs_match = re.search(r"CHARACTER\s+SET\s+(\w+)", upper)
                if cs_match:
                    charset = cs_match.group(1)
                col_match = re.search(r"COLLATE\s+(\w+)", upper)
                if col_match:
                    collation = col_match.group(1)
                return MariaDBEnumType(values, charset=charset, collation=collation)
            if upper.startswith("SET"):
                from ..expression.types import MariaDBSetType
                values = re.findall(r"'([^']*)'", stripped)
                charset = None
                collation = None
                cs_match = re.search(r"CHARACTER\s+SET\s+(\w+)", upper)
                if cs_match:
                    charset = cs_match.group(1)
                col_match = re.search(r"COLLATE\s+(\w+)", upper)
                if col_match:
                    collation = col_match.group(1)
                return MariaDBSetType(values, charset=charset, collation=collation)
            if upper.startswith("BINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MariaDBBinaryType
                return MariaDBBinaryType(length)
            if upper.startswith("VARBINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MariaDBVarBinaryType
                return MariaDBVarBinaryType(length)
            length_match = re.search(r"\((\d+)\)", stripped)
            length = int(length_match.group(1)) if length_match else None
            if upper.startswith("VARCHAR"):
                return VarCharType(length)
            return CharType(length)

        if self._MARIA_BLOB_TYPES.match(upper):
            if upper.startswith("TINYBLOB"):
                from ..expression.types import MariaDBTinyBlobType
                return MariaDBTinyBlobType()
            if upper.startswith("MEDIUMBLOB"):
                from ..expression.types import MariaDBMediumBlobType
                return MariaDBMediumBlobType()
            if upper.startswith("LONGBLOB"):
                from ..expression.types import MariaDBLongBlobType
                return MariaDBLongBlobType()
            from ..expression.types import MariaDBBlobType
            return MariaDBBlobType()

        if self._MARIA_DATE_TYPES.match(upper):
            if upper.startswith("YEAR"):
                nums = re.findall(r"\d+", stripped)
                display_width = int(nums[0]) if nums else None
                from ..expression.types import MariaDBYearType
                return MariaDBYearType(display_width)
            if upper.startswith("DATE"):
                if upper.strip() == "DATE":
                    return DateType()
                return DateTimeType()
            if upper.startswith("DATETIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                return DateTimeType(precision)
            if upper.startswith("TIMESTAMP"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimestampTzType(precision)
                return TimestampType(precision)
            if upper.startswith("TIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimeTzType(precision)
                return TimeType(precision)

        if self._MARIA_JSON_TYPES.match(upper):
            return JsonType()

        if self._MARIA_SPATIAL_TYPES.match(upper):
            srid = None
            srid_match = re.search(r"SRID\s+(\d+)", upper)
            if srid_match:
                srid = int(srid_match.group(1))
            from ..expression.types import (
                MariaDBGeometryCollectionType,
                MariaDBGeometryType,
                MariaDBLineStringType,
                MariaDBMultiLineStringType,
                MariaDBMultiPointType,
                MariaDBMultiPolygonType,
                MariaDBPointType,
                MariaDBPolygonType,
            )
            spatial_map = {
                "GEOMETRY": MariaDBGeometryType,
                "POINT": MariaDBPointType,
                "LINESTRING": MariaDBLineStringType,
                "POLYGON": MariaDBPolygonType,
                "MULTIPOINT": MariaDBMultiPointType,
                "MULTILINESTRING": MariaDBMultiLineStringType,
                "MULTIPOLYGON": MariaDBMultiPolygonType,
                "GEOMETRYCOLLECTION": MariaDBGeometryCollectionType,
            }
            for name, cls in spatial_map.items():
                if upper.startswith(name):
                    return cls(srid)
            return MariaDBGeometryType(srid)

        from rhosocial.activerecord.backend.expression.types import CustomType
        return CustomType(stripped)