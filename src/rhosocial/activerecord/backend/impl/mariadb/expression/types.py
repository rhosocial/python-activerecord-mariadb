# src/rhosocial/activerecord/backend/impl/mariadb/expression/types.py
"""MariaDB-specific DataType subclasses.

Naming convention
-----------------
MariaDB-specific types use the ``MariaDB`` prefix to distinguish them from
the core types (which have no prefix).  This avoids ambiguity when both
core and backend types are used together.

Usage scope
-----------
These types are used **only** for MariaDB backend DDL column definitions,
introspection result parsing, and schema comparison.  They should **not**
be used by application code directly — always use the core types for
DDL definition expressions (``ColumnDefinition.data_type``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    DataType,
    IntegerType,
    SmallIntType,
    TextType,
    TinyIntType,
)


# ---------------------------------------------------------------------------
# Integer variants with UNSIGNED / ZEROFILL
# ---------------------------------------------------------------------------

class MariaDBIntType(IntegerType):
    """MariaDB ``INTEGER`` / ``INT`` with optional UNSIGNED / ZEROFILL."""

    name = "mariadb_int"

    unsigned: bool = False
    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.unsigned = unsigned
        self.zerofill = zerofill

    def _type_params(self) -> tuple:
        return (self.unsigned, self.zerofill)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'IntegerType'}


class MariaDBTinyIntType(TinyIntType):
    """MariaDB ``TINYINT`` with optional UNSIGNED / ZEROFILL."""

    name = "mariadb_tinyint"

    unsigned: bool = False
    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.unsigned = unsigned
        self.zerofill = zerofill

    def _type_params(self) -> tuple:
        return (self.unsigned, self.zerofill)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'TinyIntType'}


class MariaDBSmallIntType(SmallIntType):
    """MariaDB ``SMALLINT`` with optional UNSIGNED / ZEROFILL."""

    name = "mariadb_smallint"

    unsigned: bool = False
    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.unsigned = unsigned
        self.zerofill = zerofill

    def _type_params(self) -> tuple:
        return (self.unsigned, self.zerofill)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'SmallIntType'}


class MariaDBBigIntType(BigIntType):
    """MariaDB ``BIGINT`` with optional UNSIGNED / ZEROFILL."""

    name = "mariadb_bigint"

    unsigned: bool = False
    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.unsigned = unsigned
        self.zerofill = zerofill

    def _type_params(self) -> tuple:
        return (self.unsigned, self.zerofill)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'BigIntType'}


# ---------------------------------------------------------------------------
# BLOB size variants
# ---------------------------------------------------------------------------

class MariaDBTinyBlobType(BlobType):
    """MariaDB ``TINYBLOB`` — maximum 255 bytes."""

    name = "mariadb_tinyblob"


class MariaDBBlobType(BlobType):
    """MariaDB ``BLOB`` — maximum 65,535 bytes."""

    name = "mariadb_blob"


class MariaDBMediumBlobType(BlobType):
    """MariaDB ``MEDIUMBLOB`` — maximum 16,777,215 bytes."""

    name = "mariadb_mediumblob"


class MariaDBLongBlobType(BlobType):
    """MariaDB ``LONGBLOB`` — maximum 4,294,967,295 bytes."""

    name = "mariadb_longblob"


# ---------------------------------------------------------------------------
# TEXT size variants
# ---------------------------------------------------------------------------

class MariaDBTinyTextType(TextType):
    """MariaDB ``TINYTEXT`` — maximum 255 bytes."""

    name = "mariadb_tinytext"


class MariaDBTextType(TextType):
    """MariaDB ``TEXT`` — maximum 65,535 bytes."""

    name = "mariadb_text"


class MariaDBMediumTextType(TextType):
    """MariaDB ``MEDIUMTEXT`` — maximum 16,777,215 bytes."""

    name = "mariadb_mediumtext"


class MariaDBLongTextType(TextType):
    """MariaDB ``LONGTEXT`` — maximum 4,294,967,295 bytes."""

    name = "mariadb_longtext"


# ---------------------------------------------------------------------------
# Bit type
# ---------------------------------------------------------------------------

class MariaDBBitType(DataType):
    """MariaDB ``BIT[(n)]`` — bit-field type."""

    name = "mariadb_bit"

    n: Optional[int] = None

    def __init__(self, dialect=None, n: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.n = n

    def _type_params(self) -> tuple:
        return (self.n,)


# ---------------------------------------------------------------------------
# Year type
# ---------------------------------------------------------------------------

class MariaDBYearType(DataType):
    """MariaDB ``YEAR[(4)]`` — year type."""

    name = "mariadb_year"

    display_width: Optional[int] = None

    def __init__(self, dialect=None, display_width: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.display_width = display_width

    def _type_params(self) -> tuple:
        return (self.display_width,)


# ---------------------------------------------------------------------------
# Binary / VarBinary
# ---------------------------------------------------------------------------

class MariaDBBinaryType(DataType):
    """MariaDB ``BINARY[(n)]`` — fixed-length binary."""

    name = "mariadb_binary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)


class MariaDBVarBinaryType(DataType):
    """MariaDB ``VARBINARY(n)`` — variable-length binary."""

    name = "mariadb_varbinary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)


# ---------------------------------------------------------------------------
# ENUM
# ---------------------------------------------------------------------------

class MariaDBEnumType(DataType):
    """MariaDB ``ENUM('val', ...)`` with optional CHARACTER SET / COLLATE."""

    name = "mariadb_enum"

    values: Tuple[str, ...] = ()
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, values: Optional[List[str]] = None,
                 charset: Optional[str] = None, collation: Optional[str] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        if values is None:
            raise ValueError("MariaDBEnumType requires values")
        if not values:
            raise ValueError("ENUM must have at least one value")
        self.values = tuple(values)
        self.charset = charset
        self.collation = collation

    def _type_params(self) -> tuple:
        return (self.values, self.charset, self.collation)

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={list(self.values)!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# SET
# ---------------------------------------------------------------------------

class MariaDBSetType(DataType):
    """MariaDB ``SET('val', ...)`` with optional CHARACTER SET / COLLATE."""

    name = "mariadb_set"

    values: Tuple[str, ...] = ()
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, values: Optional[List[str]] = None,
                 charset: Optional[str] = None, collation: Optional[str] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        if values is None:
            raise ValueError("MariaDBSetType requires values")
        if not values:
            raise ValueError("SET must have at least one value")
        self.values = tuple(values)
        self.charset = charset
        self.collation = collation

    def _type_params(self) -> tuple:
        return (self.values, self.charset, self.collation)

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={list(self.values)!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# Spatial / Geometry types
# ---------------------------------------------------------------------------

class MariaDBGeometryType(DataType):
    """MariaDB ``GEOMETRY`` with optional SRID."""

    name = "mariadb_geometry"

    srid: Optional[int] = None

    def __init__(self, dialect=None, srid: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.srid = srid

    def _type_params(self) -> tuple:
        return (self.srid,)


class MariaDBPointType(MariaDBGeometryType):
    """MariaDB ``POINT`` with optional SRID."""

    name = "mariadb_point"


class MariaDBLineStringType(MariaDBGeometryType):
    """MariaDB ``LINESTRING`` with optional SRID."""

    name = "mariadb_linestring"


class MariaDBPolygonType(MariaDBGeometryType):
    """MariaDB ``POLYGON`` with optional SRID."""

    name = "mariadb_polygon"


class MariaDBMultiPointType(MariaDBGeometryType):
    """MariaDB ``MULTIPOINT`` with optional SRID."""

    name = "mariadb_multipoint"


class MariaDBMultiLineStringType(MariaDBGeometryType):
    """MariaDB ``MULTILINESTRING`` with optional SRID."""

    name = "mariadb_multilinestring"


class MariaDBMultiPolygonType(MariaDBGeometryType):
    """MariaDB ``MULTIPOLYGON`` with optional SRID."""

    name = "mariadb_multipolygon"


class MariaDBGeometryCollectionType(MariaDBGeometryType):
    """MariaDB ``GEOMETRYCOLLECTION`` with optional SRID."""

    name = "mariadb_geometrycollection"
