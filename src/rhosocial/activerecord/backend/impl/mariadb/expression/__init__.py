# src/rhosocial/activerecord/backend/impl/mariadb/expression/__init__.py
"""
MariaDB-specific expression classes.

This module provides expression classes that are specific to MariaDB, such as
LOAD DATA INFILE, JSON_TABLE, JSON functions, spatial functions, vector
functions, MATCH...AGAINST expressions, and row-level locking expressions.

Directory structure (canonical top-level names):
- functions/      - JSON, MATCH...AGAINST and spatial function expressions
- objects/        - schema-object expression nodes
- sources/        - JSON_TABLE query source
- statements/     - DDL/DML/LOAD DATA/SHOW/routine/admin statements
- types/          - MariaDB data types
- predicates/     - MATCH...AGAINST predicate vocabulary
- query_parts/    - PARTITION BY clause nodes
- operators/      - ALTER TABLE partition operations
- value_types/    - SET literals and CREATE TABLE option values
- column_types/   - column definition/format/storage expressions
- introspection/  - introspection queries and status expressions
"""

from .functions import (
    MariaDBJSONExtractExpression,
    MariaDBJSONObjectExpression,
    MariaDBJSONArrayExpression,
    MariaDBJSONContainsExpression,
    MariaDBSTGeomFromTextExpression,
    MariaDBSTDistanceExpression,
    MariaDBSTWithinExpression,
    MariaDBSTContainsExpression,
    MariaDBMatchAgainstExpression,
)

from .predicates import MatchAgainstMode

from .sources import (
    MariaDBJSONTableExpression,
    JSONTableColumn,
    NestedPath,
)

from .statements import (
    MariaDBLoadDataStatement,
    LoadDataOptions,
    MariaDBRenameTableStatement,
    MariaDBRenameIndexStatement,
    MariaDBAlterTableExpression,
    MariaDBTableMaintenanceStatement,
    TableMaintenanceOperation,
    MariaDBCreateTableOptions,
    MariaDBAlterTableOptionsStatement,
    MariaDBInsertExpression,
    MariaDBTruncateExpression,
    MariaDBCallStatement,
    MariaDBCreateFunctionStatement,
    MariaDBCreateProcedureStatement,
    MariaDBDropFunctionStatement,
    MariaDBDropProcedureStatement,
    AccountSpec,
    GrantPrivilege,
    MariaDBAlterUserStatement,
    MariaDBCreateRoleStatement,
    MariaDBCreateUserStatement,
    MariaDBDenyStatement,
    MariaDBDropRoleStatement,
    MariaDBDropUserStatement,
    MariaDBFlushStatement,
    MariaDBGrantStatement,
    MariaDBKillStatement,
    MariaDBRevokeStatement,
    MariaDBShutdownStatement,
)

from .query_parts import (
    MariaDBSubpartitionStrategy,
    MariaDBPartitionMaxValue,
    MariaDBPartitionValue,
    MariaDBSubpartitionClause,
    MariaDBPartitionClause,
    MariaDBPartitionByRange,
    MariaDBPartitionByRangeColumns,
    MariaDBPartitionByList,
    MariaDBPartitionByListColumns,
    MariaDBPartitionByHash,
    MariaDBPartitionByKey,
)

from .operators import (
    MariaDBPartitionTableExpression,
    MariaDBAddPartitionExpression,
    MariaDBDropPartitionExpression,
    MariaDBTruncatePartitionExpression,
    MariaDBReorganizePartitionExpression,
    MariaDBRemovePartitioningExpression,
    MariaDBCoalescePartitionExpression,
    MariaDBAnalyzePartitionExpression,
    MariaDBCheckPartitionExpression,
    MariaDBOptimizePartitionExpression,
    MariaDBRebuildPartitionExpression,
    MariaDBRepairPartitionExpression,
    MariaDBGetPartitionsExpression,
    MariaDBExchangePartitionStatement,
)

from .value_types import (
    MariaDBRowFormat,
    MariaDBSetLiteralExpression,
    MariaDBFindInSetExpression,
    MariaDBSetContainsExpression,
)

from .column_types import (
    MariaDBColumnFormat,
    MariaDBColumnStorage,
    MariaDBColumnDefinition,
    MariaDBColumnOptions,
)

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
    "MariaDBLoadDataStatement",
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
    "MariaDBRenameTableStatement",
    "MariaDBRenameIndexStatement",
    "MariaDBAlterTableExpression",
    "MariaDBTableMaintenanceStatement",
    "TableMaintenanceOperation",
    "MariaDBCreateTableOptions",
    "MariaDBAlterTableOptionsStatement",
    "MariaDBRowFormat",
    "MariaDBInsertExpression",
    "MariaDBTruncateExpression",
    "MariaDBColumnFormat",
    "MariaDBColumnStorage",
    "MariaDBColumnDefinition",
    "MariaDBColumnOptions",
    "MariaDBSubpartitionStrategy",
    "MariaDBPartitionMaxValue",
    "MariaDBPartitionValue",
    "MariaDBSubpartitionClause",
    "MariaDBPartitionClause",
    "MariaDBPartitionByRange",
    "MariaDBPartitionByRangeColumns",
    "MariaDBPartitionByList",
    "MariaDBPartitionByListColumns",
    "MariaDBPartitionByHash",
    "MariaDBPartitionByKey",
    "MariaDBPartitionTableExpression",
    "MariaDBAddPartitionExpression",
    "MariaDBDropPartitionExpression",
    "MariaDBTruncatePartitionExpression",
    "MariaDBReorganizePartitionExpression",
    "MariaDBRemovePartitioningExpression",
    "MariaDBCoalescePartitionExpression",
    "MariaDBAnalyzePartitionExpression",
    "MariaDBCheckPartitionExpression",
    "MariaDBOptimizePartitionExpression",
    "MariaDBRebuildPartitionExpression",
    "MariaDBRepairPartitionExpression",
    "MariaDBGetPartitionsExpression",
    "MariaDBExchangePartitionStatement",
    "MariaDBCallStatement",
    "MariaDBCreateFunctionStatement",
    "MariaDBCreateProcedureStatement",
    "MariaDBDropFunctionStatement",
    "MariaDBDropProcedureStatement",
    "AccountSpec",
    "GrantPrivilege",
    "MariaDBAlterUserStatement",
    "MariaDBCreateRoleStatement",
    "MariaDBCreateUserStatement",
    "MariaDBDenyStatement",
    "MariaDBDropRoleStatement",
    "MariaDBDropUserStatement",
    "MariaDBFlushStatement",
    "MariaDBGrantStatement",
    "MariaDBKillStatement",
    "MariaDBRevokeStatement",
    "MariaDBShutdownStatement",
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
# Ownership is structural, not a spelling test: a node *defined* in this
# package is MariaDB's, whether or not it is re-exported above. Judging by a
# name prefix would let a rename change the wire contract silently, and a
# hand-maintained name list would let a new node keep the split spelling. The
# defining module is the declaration, so the walk keys off ``__module__``
# alone; the reserved tokens are an explicit owned-name tuple.
import importlib as _importlib
import pkgutil as _pkgutil

from rhosocial.activerecord.backend.expression.bases.bases import BaseExpression as _BaseExpression

_MARIADB_OWNED_KINDS = ("MariaDB",)

for _module_info in _pkgutil.walk_packages(
    __path__, prefix=__name__ + ".", onerror=lambda _error: None
):
    _module = _importlib.import_module(_module_info.name)
    for _value in vars(_module).values():
        if (
            isinstance(_value, type)
            and issubclass(_value, _BaseExpression)
            and _value.__module__ == _module_info.name
        ):
            _value.KIND_RESERVED = _MARIADB_OWNED_KINDS
del _MARIADB_OWNED_KINDS, _module_info, _module, _value, _importlib, _pkgutil, _BaseExpression
