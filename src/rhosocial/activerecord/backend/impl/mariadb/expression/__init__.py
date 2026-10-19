# src/rhosocial/activerecord/backend/impl/mariadb/expression/__init__.py
"""
MariaDB-specific expression classes.

This module provides expression classes that are specific to MariaDB, such as
LOAD DATA INFILE, JSON_TABLE, JSON functions, spatial functions, vector
functions, MATCH...AGAINST expressions, and row-level locking expressions.

Directory structure:
- load_data.py      - LOAD DATA INFILE expression
- json_table.py    - JSON_TABLE expression
- json.py           - JSON function expressions
- spatial.py         - Spatial function expressions
- match_against.py - MATCH...AGAINST expression
- locking.py        - Row-level locking expressions (FOR UPDATE, FOR SHARE)
"""

from .load_data import MariaDBLoadDataExpression, LoadDataOptions
from .json_table import MariaDBJSONTableExpression, JSONTableColumn, NestedPath
from .json import (
    MariaDBJSONExtractExpression,
    MariaDBJSONObjectExpression,
    MariaDBJSONArrayExpression,
    MariaDBJSONContainsExpression,
)
from .spatial import (
    MariaDBSTGeomFromTextExpression,
    MariaDBSTDistanceExpression,
    MariaDBSTWithinExpression,
    MariaDBSTContainsExpression,
)
from .match_against import MariaDBMatchAgainstExpression, MatchAgainstMode
from .rename_table import MariaDBRenameTableExpression
from .rename_index import MariaDBRenameIndexExpression
from .routine import (
    MariaDBCallExpression,
    MariaDBCreateFunctionExpression,
    MariaDBCreateProcedureExpression,
    MariaDBDropFunctionExpression,
    MariaDBDropProcedureExpression,
)
from .set_type import (
    MariaDBSetLiteralExpression,
    MariaDBFindInSetExpression,
    MariaDBSetContainsExpression,
)
from .admin import (
    AccountSpec,
    GrantPrivilege,
    MariaDBAlterUserExpression,
    MariaDBCreateRoleExpression,
    MariaDBCreateUserExpression,
    MariaDBDenyExpression,
    MariaDBDropRoleExpression,
    MariaDBDropUserExpression,
    MariaDBFlushExpression,
    MariaDBGrantExpression,
    MariaDBKillExpression,
    MariaDBRevokeExpression,
    MariaDBShutdownExpression,
)
from .table_options import MariaDBRowFormat, MariaDBCreateTableOptions
from .dml import MariaDBInsertExpression
from .truncate import MariaDBTruncateExpression
from .alter_table import MariaDBAlterTableExpression
from .column import (
    MariaDBColumnFormat,
    MariaDBColumnStorage,
    MariaDBColumnDefinition,
    MariaDBColumnOptions,
)
from .maintenance import (
    MariaDBTableMaintenanceExpression,
    TableMaintenanceOperation,
)
from .partition import (
    MariaDBPartitionStrategy,
    MariaDBSubpartitionStrategy,
    MariaDBPartitionOptions,
    MariaDBPartitionMaxValue,
    MariaDBPartitionValue,
    MariaDBSubpartitionDefinition,
    MariaDBPartitionDefinition,
    MariaDBPartitionClause,
    MariaDBPartitionByRange,
    MariaDBPartitionByRangeColumns,
    MariaDBPartitionByList,
    MariaDBPartitionByListColumns,
    MariaDBPartitionByHash,
    MariaDBPartitionByKey,
    MariaDBExchangePartitionExpression,
)

# DataType subclasses for DDL
from .types import (
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
    MariaDBUUIDType,
    MariaDBVarBinaryType,
    MariaDBYearType,
)

__all__ = [
    "MariaDBLoadDataExpression",
    "LoadDataOptions",
    "MariaDBJSONTableExpression",
    "JSONTableColumn",
    "NestedPath",
    "MariaDBJSONExtractExpression",
    "MariaDBJSONObjectExpression",
    "MariaDBJSONArrayExpression",
    "MariaDBJSONContainsExpression",
    "MariaDBSTGeomFromTextExpression",
    "MariaDBSTDistanceExpression",
    "MariaDBSTWithinExpression",
    "MariaDBSTContainsExpression",
    "MariaDBMatchAgainstExpression",
    "MatchAgainstMode",
    "MariaDBRenameTableExpression",
    "MariaDBRenameIndexExpression",
    "MariaDBAlterTableExpression",
    "MariaDBTableMaintenanceExpression",
    "TableMaintenanceOperation",
    "MariaDBCreateTableOptions",
    "MariaDBRowFormat",
    "MariaDBInsertExpression",
    "MariaDBTruncateExpression",
    "MariaDBColumnFormat",
    "MariaDBColumnStorage",
    "MariaDBColumnDefinition",
    "MariaDBColumnOptions",
    "MariaDBPartitionStrategy",
    "MariaDBSubpartitionStrategy",
    "MariaDBPartitionOptions",
    "MariaDBPartitionMaxValue",
    "MariaDBPartitionValue",
    "MariaDBSubpartitionDefinition",
    "MariaDBPartitionDefinition",
    "MariaDBPartitionClause",
    "MariaDBPartitionByRange",
    "MariaDBPartitionByRangeColumns",
    "MariaDBPartitionByList",
    "MariaDBPartitionByListColumns",
    "MariaDBPartitionByHash",
    "MariaDBPartitionByKey",
    "MariaDBExchangePartitionExpression",
    "MariaDBCallExpression",
    "MariaDBCreateFunctionExpression",
    "MariaDBCreateProcedureExpression",
    "MariaDBDropFunctionExpression",
    "MariaDBDropProcedureExpression",
    "AccountSpec",
    "GrantPrivilege",
    "MariaDBAlterUserExpression",
    "MariaDBCreateRoleExpression",
    "MariaDBCreateUserExpression",
    "MariaDBDenyExpression",
    "MariaDBDropRoleExpression",
    "MariaDBDropUserExpression",
    "MariaDBFlushExpression",
    "MariaDBGrantExpression",
    "MariaDBKillExpression",
    "MariaDBRevokeExpression",
    "MariaDBShutdownExpression",
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
    "MariaDBUUIDType",
    "MariaDBVarBinaryType",
    "MariaDBYearType",
    "MariaDBSetLiteralExpression",
    "MariaDBFindInSetExpression",
    "MariaDBSetContainsExpression",
]
# ``MariaDB`` is one word. The general derivation -- a run of capitals counts
# as a single word -- disagrees with this backend's identifier and yields
# ``maria_db_binary_type``, ``maria_dbjson_object_expression``,
# ``maria_dbst_distance_expression`` and ``maria_dbuuid_type``. The kind is a
# wire contract (spec 3), so the identifier is declared whole and the kind is
# derived from that declaration: ``KIND_RESERVED`` is data, not behaviour, so
# no class overrides ``kind()`` and class name, kind and formatter entry keep
# one source.
#
# The loop walks this package's own modules rather than an exported name
# list, for the reason the sqlite package's note gives: a hand-maintained
# list can only ever be out of date, and a node that is defined but not
# re-exported here would silently keep the split spelling.
import importlib as _importlib
import pkgutil as _pkgutil

from rhosocial.activerecord.backend.expression.core import BaseExpression as _BaseExpression

for _module_info in _pkgutil.walk_packages(__path__, prefix=__name__ + ".", onerror=lambda _error: None):
    _module = _importlib.import_module(_module_info.name)
    for _value in vars(_module).values():
        if (
            isinstance(_value, type)
            and issubclass(_value, _BaseExpression)
            and _value.__name__.startswith("MariaDB")
            and _value.__module__ == _module_info.name
        ):
            _value.KIND_RESERVED = ("MariaDB",)
del _module_info, _module, _value, _importlib, _pkgutil, _BaseExpression
