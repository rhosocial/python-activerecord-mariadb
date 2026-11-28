# src/rhosocial/activerecord/backend/impl/mariadb/expression/types/__init__.py
"""MariaDB data-type expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``.
"""

from importlib import import_module as _import_module

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
    "MariaDBMediumIntType",
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
    "MariaDBUUIDType",
    "MariaDBVarBinaryType",
    "MariaDBXmlType",
    "MariaDBYearType",

]

#: name -> defining module, relative to this package
_REEXPORTS = {
    "MariaDBBigIntType": ".types",
    "MariaDBBinaryType": ".types",
    "MariaDBBitType": ".types",
    "MariaDBBlobType": ".types",
    "MariaDBEnumType": ".types",
    "MariaDBGeometryCollectionType": ".types",
    "MariaDBGeometryType": ".types",
    "MariaDBIntType": ".types",
    "MariaDBLineStringType": ".types",
    "MariaDBLongBlobType": ".types",
    "MariaDBLongTextType": ".types",
    "MariaDBMediumBlobType": ".types",
    "MariaDBMediumIntType": ".types",
    "MariaDBMediumTextType": ".types",
    "MariaDBMultiLineStringType": ".types",
    "MariaDBMultiPointType": ".types",
    "MariaDBMultiPolygonType": ".types",
    "MariaDBPointType": ".types",
    "MariaDBPolygonType": ".types",
    "MariaDBSetType": ".types",
    "MariaDBSmallIntType": ".types",
    "MariaDBTextType": ".types",
    "MariaDBTinyBlobType": ".types",
    "MariaDBTinyIntType": ".types",
    "MariaDBTinyTextType": ".types",
    "MariaDBUUIDType": ".types",
    "MariaDBVarBinaryType": ".types",
    "MariaDBXmlType": ".types",
    "MariaDBYearType": ".types",

}


def __getattr__(name: str):
    """Resolve a re-exported name on first access (PEP 562)."""
    try:
        module_name = _REEXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = _import_module(module_name, __name__).__dict__[name]
    globals()[name] = value  # cache: subsequent access is a plain attribute lookup
    return value


def __dir__() -> list:
    """Make the lazy re-exports visible to ``dir()``."""
    return sorted(set(globals()) | set(__all__))
