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

from typing import List, Optional, Set

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

    unsigned: bool = False
    zerofill: bool = False

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.unsigned == other.unsigned and
                self.zerofill == other.zerofill)

    def __hash__(self) -> int:
        return hash((type(self), self.unsigned, self.zerofill))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'IntegerType'}


class MariaDBTinyIntType(TinyIntType):
    """MariaDB ``TINYINT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.unsigned == other.unsigned and
                self.zerofill == other.zerofill)

    def __hash__(self) -> int:
        return hash((type(self), self.unsigned, self.zerofill))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'TinyIntType'}


class MariaDBSmallIntType(SmallIntType):
    """MariaDB ``SMALLINT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.unsigned == other.unsigned and
                self.zerofill == other.zerofill)

    def __hash__(self) -> int:
        return hash((type(self), self.unsigned, self.zerofill))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'SmallIntType'}


class MariaDBBigIntType(BigIntType):
    """MariaDB ``BIGINT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.unsigned == other.unsigned and
                self.zerofill == other.zerofill)

    def __hash__(self) -> int:
        return hash((type(self), self.unsigned, self.zerofill))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'BigIntType'}


# ---------------------------------------------------------------------------
# BLOB size variants
# ---------------------------------------------------------------------------

class MariaDBTinyBlobType(BlobType):
    """MariaDB ``TINYBLOB`` — maximum 255 bytes."""


class MariaDBBlobType(BlobType):
    """MariaDB ``BLOB`` — maximum 65,535 bytes."""


class MariaDBMediumBlobType(BlobType):
    """MariaDB ``MEDIUMBLOB`` — maximum 16,777,215 bytes."""


class MariaDBLongBlobType(BlobType):
    """MariaDB ``LONGBLOB`` — maximum 4,294,967,295 bytes."""


# ---------------------------------------------------------------------------
# TEXT size variants
# ---------------------------------------------------------------------------

class MariaDBTinyTextType(TextType):
    """MariaDB ``TINYTEXT`` — maximum 255 bytes."""


class MariaDBTextType(TextType):
    """MariaDB ``TEXT`` — maximum 65,535 bytes."""


class MariaDBMediumTextType(TextType):
    """MariaDB ``MEDIUMTEXT`` — maximum 16,777,215 bytes."""


class MariaDBLongTextType(TextType):
    """MariaDB ``LONGTEXT`` — maximum 4,294,967,295 bytes."""


# ---------------------------------------------------------------------------
# Bit type
# ---------------------------------------------------------------------------

class MariaDBBitType(DataType):
    """MariaDB ``BIT[(n)]`` — bit-field type."""

    n: Optional[int] = None

    def __init__(self, dialect=None, *, n: Optional[int] = None):
        super().__init__(dialect)
        self.n = n

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.n == other.n

    def __hash__(self) -> int:
        return hash((type(self), self.n))


# ---------------------------------------------------------------------------
# Year type
# ---------------------------------------------------------------------------

class MariaDBYearType(DataType):
    """MariaDB ``YEAR[(4)]`` — year type."""

    display_width: Optional[int] = None

    def __init__(self, dialect=None, *, display_width: Optional[int] = None):
        super().__init__(dialect)
        self.display_width = display_width

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.display_width == other.display_width

    def __hash__(self) -> int:
        return hash((type(self), self.display_width))


# ---------------------------------------------------------------------------
# Binary / VarBinary
# ---------------------------------------------------------------------------

class MariaDBBinaryType(DataType):
    """MariaDB ``BINARY[(n)]`` — fixed-length binary."""

    length: Optional[int] = None

    def __init__(self, dialect=None, *, length: Optional[int] = None):
        super().__init__(dialect)
        self.length = length

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))


class MariaDBVarBinaryType(DataType):
    """MariaDB ``VARBINARY(n)`` — variable-length binary."""

    length: Optional[int] = None

    def __init__(self, dialect=None, *, length: Optional[int] = None):
        super().__init__(dialect)
        self.length = length

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))


# ---------------------------------------------------------------------------
# ENUM
# ---------------------------------------------------------------------------

class MariaDBEnumType(DataType):
    """MariaDB ``ENUM('val', ...)`` with optional CHARACTER SET / COLLATE."""

    values: List[str]
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, *, values: List[str],
                 charset: Optional[str] = None, collation: Optional[str] = None):
        super().__init__(dialect)
        if not values:
            raise ValueError("ENUM must have at least one value")
        self.values = list(values)
        self.charset = charset
        self.collation = collation

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.values == other.values and
                self.charset == other.charset and
                self.collation == other.collation)

    def __hash__(self) -> int:
        return hash((type(self), tuple(self.values), self.charset, self.collation))

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# SET
# ---------------------------------------------------------------------------

class MariaDBSetType(DataType):
    """MariaDB ``SET('val', ...)`` with optional CHARACTER SET / COLLATE."""

    values: List[str]
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, *, values: List[str],
                 charset: Optional[str] = None, collation: Optional[str] = None):
        super().__init__(dialect)
        if not values:
            raise ValueError("SET must have at least one value")
        self.values = list(values)
        self.charset = charset
        self.collation = collation

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.values == other.values and
                self.charset == other.charset and
                self.collation == other.collation)

    def __hash__(self) -> int:
        return hash((type(self), tuple(self.values), self.charset, self.collation))

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# Spatial / Geometry types
# ---------------------------------------------------------------------------

class MariaDBGeometryType(DataType):
    """MariaDB ``GEOMETRY`` with optional SRID."""

    srid: Optional[int] = None

    def __init__(self, dialect=None, *, srid: Optional[int] = None):
        super().__init__(dialect)
        self.srid = srid

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.srid == other.srid

    def __hash__(self) -> int:
        return hash((type(self), self.srid))


class MariaDBPointType(MariaDBGeometryType):
    """MariaDB ``POINT`` with optional SRID."""


class MariaDBLineStringType(MariaDBGeometryType):
    """MariaDB ``LINESTRING`` with optional SRID."""


class MariaDBPolygonType(MariaDBGeometryType):
    """MariaDB ``POLYGON`` with optional SRID."""


class MariaDBMultiPointType(MariaDBGeometryType):
    """MariaDB ``MULTIPOINT`` with optional SRID."""


class MariaDBMultiLineStringType(MariaDBGeometryType):
    """MariaDB ``MULTILINESTRING`` with optional SRID."""


class MariaDBMultiPolygonType(MariaDBGeometryType):
    """MariaDB ``MULTIPOLYGON`` with optional SRID."""


class MariaDBGeometryCollectionType(MariaDBGeometryType):
    """MariaDB ``GEOMETRYCOLLECTION`` with optional SRID."""