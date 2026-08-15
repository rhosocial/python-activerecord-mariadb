# src/rhosocial/activerecord/backend/impl/mariadb/types.py
"""MariaDB-specific type definitions and helpers.

This module re-exports MariaDB-specific DataType subclasses from
``expression.types`` for convenient access.

Usage::

    from rhosocial.activerecord.backend.impl.mariadb.types import (
        MariaDBIntType, MariaDBEnumType, MariaDBSetType,
    )
"""

from .expression.types import (
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

__all__ = [
    "MariaDBBigIntType",
    "MariaDBBinaryType",
    "MariaDBBitType",
    "MariaDBBlobType",
    "MariaDBEnumType",
    "MariaDBGeometryCollectionType",
    "MariaDBGeometryType",
    "MariaDBIntType",
    "MariaDBLineStringType",
    "MariaDBLongBlobType",
    "MariaDBLongTextType",
    "MariaDBMediumBlobType",
    "MariaDBMediumTextType",
    "MariaDBMultiLineStringType",
    "MariaDBMultiPointType",
    "MariaDBMultiPolygonType",
    "MariaDBPointType",
    "MariaDBPolygonType",
    "MariaDBSetType",
    "MariaDBSmallIntType",
    "MariaDBTextType",
    "MariaDBTinyBlobType",
    "MariaDBTinyIntType",
    "MariaDBTinyTextType",
    "MariaDBVarBinaryType",
    "MariaDBYearType",
]
