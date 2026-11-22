# src/rhosocial/activerecord/backend/impl/mariadb/introspection/type_parser.py
"""MariaDB's type-spelling parser (read direction, introspection-only).

Core removed ``dialect.parse_type``: parsing a server-reported type spelling
back into a ``DataType`` is a backend-local concern, not a dialect protocol
member. This helper lives under introspection and is used only when reading a
column's declared type back from the catalog.
"""
import re
import warnings

from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    CharType,
    CustomType,
    DataType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    JsonType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    VarCharType,
)


class MariaDBTypeParser:
    """Parse a raw MariaDB type spelling into a ``DataType``, bound to a dialect."""

    # Every word MariaDB's own "Numeric Data Type Overview" lists as an integer
    # synonym is recognised here, and each maps to the class its canonical word
    # maps to. INT1..INT8 are tried before INT so the narrower word wins.
    _MARIA_INTEGER_TYPES = re.compile(
        r"^(?:TINYINT|SMALLINT|MEDIUMINT|"
        r"INT1|INT2|INT3|INT4|INT8|"
        r"INT|INTEGER|BIGINT)\b",
        re.IGNORECASE,
    )
    _MARIA_BOOLEAN_TYPES = re.compile(
        r"^(?:BOOL|BOOLEAN)\b",
        re.IGNORECASE,
    )
    _MARIA_FLOAT_TYPES = re.compile(
        r"^(?:FLOAT|REAL|DOUBLE)\b",
        re.IGNORECASE,
    )
    _MARIA_DECIMAL_TYPES = re.compile(
        r"^(?:DECIMAL|NUMERIC|DEC|FIXED)\b",
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
    # MariaDB 12.3's native XML type has its own branch: the string branch ends
    # in a catch-all returning CharType, which would misread XMLTYPE.
    _MARIA_XML_TYPES = re.compile(
        r"^(?:XMLTYPE)\b",
        re.IGNORECASE,
    )
    # MariaDB 10.7's native UUID column type, gated the same way as XMLTYPE.
    _MARIA_UUID_TYPES = re.compile(
        r"^(?:UUID)\b",
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

    def __init__(self, dialect):
        self.dialect = dialect

    def parse(self, raw: str) -> DataType:
        """Turn one MariaDB type string into one ``DataType``.

        One concept in, one class out: every spelling MariaDB accepts for a
        concept yields the same canonical instance shape. A word MariaDB does
        not write falls through to :class:`CustomType`, which is honest
        ignorance rather than a guess.
        """
        dialect = self.dialect
        stripped = raw.strip()
        upper = stripped.upper()

        if self._MARIA_BIT_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            n = int(nums[0]) if nums else None
            from ..expression.types import MariaDBBitType
            return MariaDBBitType(dialect, n)

        # BOOL / BOOLEAN are documented synonyms of TINYINT on MariaDB, so this
        # branch has to run before anything that would otherwise claim the
        # prefix. It yields the same BooleanType that TINYINT(1) yields below.
        if self._MARIA_BOOLEAN_TYPES.match(upper):
            return BooleanType(dialect)

        if self._MARIA_INTEGER_TYPES.match(upper):
            unsigned = "UNSIGNED" in upper
            zerofill = "ZEROFILL" in upper
            if upper.startswith("TINYINT") or upper.startswith("INT1"):
                # The display width is the number inside the parentheses, never
                # a digit in the type word: a bare INT1 must not become a
                # BooleanType just because its name contains a "1".
                width_match = re.search(r"\(\s*(\d+)\s*\)", stripped)
                display_width = int(width_match.group(1)) if width_match else None
                from ..expression.types import MariaDBTinyIntType
                t = MariaDBTinyIntType(dialect, unsigned=unsigned, zerofill=zerofill)
                if display_width == 1 and not unsigned and not zerofill:
                    return BooleanType(dialect)
                return t
            if upper.startswith("SMALLINT") or upper.startswith("INT2"):
                from ..expression.types import MariaDBSmallIntType
                return MariaDBSmallIntType(dialect, unsigned=unsigned, zerofill=zerofill)
            if upper.startswith("MEDIUMINT") or upper.startswith("INT3"):
                # MEDIUMINT is 3 bytes - a width of its own; reading it as the
                # 4-byte MariaDBIntType would make the differ miss a real change.
                from ..expression.types import MariaDBMediumIntType
                return MariaDBMediumIntType(dialect, unsigned=unsigned, zerofill=zerofill)
            if upper.startswith("BIGINT") or upper.startswith("INT8"):
                from ..expression.types import MariaDBBigIntType
                return MariaDBBigIntType(dialect, unsigned=unsigned, zerofill=zerofill)
            # INT, INTEGER and INT4 all land here: one concept, three words.
            from ..expression.types import MariaDBIntType
            return MariaDBIntType(dialect, unsigned=unsigned, zerofill=zerofill)

        if self._MARIA_FLOAT_TYPES.match(upper):
            # DOUBLE / DOUBLE PRECISION / REAL are one 8-byte concept. REAL is
            # mode-dependent and the catalog never writes it back, so it
            # canonicalises to the storage it actually is (DoubleType; under
            # REAL_AS_FLOAT the column reports "float" and takes the FLOAT branch).
            unsigned = "UNSIGNED" in upper
            if upper.startswith("DOUBLE") or upper.startswith("REAL"):
                return DoubleType(dialect, unsigned=unsigned)
            # A single FLOAT argument is bit-precision p: 0..24 -> 4-byte FLOAT,
            # 25..53 -> 8-byte DOUBLE. The deprecated two-argument FLOAT(M,D) is
            # single precision with the (M,D) display spec dropped.
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return FloatType(dialect, unsigned=unsigned)
            precision = int(nums[0]) if nums else None
            if precision is not None and precision >= 25:
                return DoubleType(dialect, unsigned=unsigned)
            return FloatType(dialect, unsigned=unsigned)

        # DECIMAL / NUMERIC / DEC / FIXED are one concept with four words.
        if self._MARIA_DECIMAL_TYPES.match(upper):
            unsigned = "UNSIGNED" in upper
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return DecimalType(dialect, int(nums[0]), int(nums[1]), unsigned=unsigned)
            if len(nums) == 1:
                return DecimalType(dialect, int(nums[0]), unsigned=unsigned)
            return DecimalType(dialect, unsigned=unsigned)

        if self._MARIA_STRING_TYPES.match(upper):
            if upper.startswith("TINYTEXT"):
                from ..expression.types import MariaDBTinyTextType
                return MariaDBTinyTextType(dialect=dialect)
            if upper.startswith("MEDIUMTEXT"):
                from ..expression.types import MariaDBMediumTextType
                return MariaDBMediumTextType(dialect=dialect)
            if upper.startswith("LONGTEXT"):
                from ..expression.types import MariaDBLongTextType
                return MariaDBLongTextType(dialect)
            if upper.startswith("TEXT"):
                from ..expression.types import MariaDBTextType
                return MariaDBTextType(dialect)
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
                return MariaDBEnumType(dialect, values, charset=charset, collation=collation)
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
                return MariaDBSetType(dialect, values, charset=charset, collation=collation)
            if upper.startswith("BINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MariaDBBinaryType
                return MariaDBBinaryType(dialect, length)
            if upper.startswith("VARBINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MariaDBVarBinaryType
                return MariaDBVarBinaryType(dialect, length)
            length_match = re.search(r"\((\d+)\)", stripped)
            length = int(length_match.group(1)) if length_match else None
            if upper.startswith("VARCHAR"):
                return VarCharType(dialect, length)
            return CharType(dialect, length)

        if self._MARIA_BLOB_TYPES.match(upper):
            if upper.startswith("TINYBLOB"):
                from ..expression.types import MariaDBTinyBlobType
                return MariaDBTinyBlobType(dialect=dialect)
            if upper.startswith("MEDIUMBLOB"):
                from ..expression.types import MariaDBMediumBlobType
                return MariaDBMediumBlobType(dialect=dialect)
            if upper.startswith("LONGBLOB"):
                from ..expression.types import MariaDBLongBlobType
                return MariaDBLongBlobType(dialect=dialect)
            from ..expression.types import MariaDBBlobType
            return MariaDBBlobType(dialect=dialect)

        if self._MARIA_DATE_TYPES.match(upper):
            if upper.startswith("YEAR"):
                nums = re.findall(r"\d+", stripped)
                display_width = int(nums[0]) if nums else None
                from ..expression.types import MariaDBYearType
                if display_width not in MariaDBYearType.ALLOWED_DISPLAY_WIDTHS:
                    # A pre-13.0 server can still report YEAR(2). We cannot
                    # round-trip it, so degrade to bare YEAR and say so.
                    warnings.warn(
                        f"Server reported YEAR({display_width}); MariaDB 13.0+ rejects "
                        "YEAR(2). Reading it as YEAR. Use old_mode=2_DIGIT_YEAR (itself "
                        "deprecated) only if the 2-digit truncation is intentional.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    display_width = None
                return MariaDBYearType(dialect, display_width)
            # DATETIME before DATE: DATETIME begins with DATE, so the order is
            # load-bearing. The fractional-seconds precision is preserved.
            if upper.startswith("DATETIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                return DateTimeType(dialect, precision)
            if upper.startswith("DATE"):
                return DateType(dialect)
            if upper.startswith("TIMESTAMP"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimestampTzType(dialect, precision)
                return TimestampType(dialect, precision)
            if upper.startswith("TIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimeTzType(dialect, precision)
                return TimeType(dialect, precision)

        if self._MARIA_JSON_TYPES.match(upper):
            return JsonType(dialect)

        if self._MARIA_XML_TYPES.match(upper):
            # XMLTYPE only exists from 12.3. On an older server the word cannot
            # come from the catalog, so the honest reading is CustomType.
            if not dialect.supports_data_type_mariadb_xml():
                return CustomType(dialect=dialect, raw=stripped)
            from ..expression.types import MariaDBXmlType
            return MariaDBXmlType(dialect)

        if self._MARIA_UUID_TYPES.match(upper):
            # UUID arrived in 10.7; below that the word cannot come from that
            # server's catalog, so return CustomType rather than a class whose
            # formatter would raise UnsupportedFeatureError.
            if not dialect.supports_data_type_uuid():
                return CustomType(dialect=dialect, raw=stripped)
            from ..expression.types import MariaDBUUIDType
            return MariaDBUUIDType(dialect)

        if self._MARIA_SPATIAL_TYPES.match(upper):
            srid = None
            # ``REF_SYSTEM_ID=<n>`` is MariaDB's spelling. ``SRID <n>`` is
            # MySQL's attribute and every measured MariaDB server rejects it.
            srid_match = re.search(r"REF_SYSTEM_ID\s*=\s*(\d+)", upper)
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
            # Dispatch on the leading word, not a prefix scan: GEOMETRYCOLLECTION
            # begins with GEOMETRY and must not be read as the generic type.
            head = re.match(r"[A-Z]+", upper)
            name = head.group(0) if head else upper
            return spatial_map.get(name, MariaDBGeometryType)(dialect, srid)

        return CustomType(dialect=dialect, raw=stripped)


__all__ = ["MariaDBTypeParser"]
