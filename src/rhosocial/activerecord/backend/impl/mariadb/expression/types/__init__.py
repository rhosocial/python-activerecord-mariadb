# rhosocial/activerecord/backend/impl/mariadb/expression/types/__init__.py
"""MariaDB data-type expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'BigIntType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'BinaryType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'BlobType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'DataType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'EnumType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'IntegerType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'LENGTH_PARAMETERS': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'List': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBBigIntType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBBinaryType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBBitType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBBlobType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBEnumType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBGeometryCollectionType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBGeometryType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBIntType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBLineStringType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBLongBlobType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBLongTextType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBMediumBlobType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBMediumIntType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBMediumTextType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBMultiLineStringType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBMultiPointType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBMultiPolygonType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBPointType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBPolygonType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBSetType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBSmallIntType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBTextType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBTinyBlobType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBTinyIntType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBTinyTextType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBUUIDType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBVarBinaryType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBXmlType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'MariaDBYearType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'Optional': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'SmallIntType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'TextType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'TinyIntType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'Tuple': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'UUIDType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'VarBinaryType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'XmlType': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    '_zerofill_signedness': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
    'annotations': 'rhosocial.activerecord.backend.impl.mariadb.expression.types.types',
}

__all__ = [
    'MariaDBBigIntType',
    'MariaDBBinaryType',
    'MariaDBBitType',
    'MariaDBBlobType',
    'MariaDBEnumType',
    'MariaDBGeometryCollectionType',
    'MariaDBGeometryType',
    'MariaDBIntType',
    'MariaDBLineStringType',
    'MariaDBLongBlobType',
    'MariaDBLongTextType',
    'MariaDBMediumBlobType',
    'MariaDBMediumIntType',
    'MariaDBMediumTextType',
    'MariaDBMultiLineStringType',
    'MariaDBMultiPointType',
    'MariaDBMultiPolygonType',
    'MariaDBPointType',
    'MariaDBPolygonType',
    'MariaDBSetType',
    'MariaDBSmallIntType',
    'MariaDBTextType',
    'MariaDBTinyBlobType',
    'MariaDBTinyIntType',
    'MariaDBTinyTextType',
    'MariaDBUUIDType',
    'MariaDBVarBinaryType',
    'MariaDBXmlType',
    'MariaDBYearType',
]


def __getattr__(name):
    """Resolve a public name from this namespace lazily (no import cycles)."""
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_name)
    value = vars(module)[name]
    globals()[name] = value
    return value
