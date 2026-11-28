# rhosocial/activerecord/backend/impl/mariadb/expression/query_parts/__init__.py
"""MariaDB query-part expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'Any': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'BaseExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'Decimal': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'Enum': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBPartitionByHash': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBPartitionByKey': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBPartitionByList': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBPartitionByListColumns': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBPartitionByRange': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBPartitionByRangeColumns': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBPartitionClause': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBPartitionMaxValue': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBPartitionValue': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBSubpartitionClause': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'MariaDBSubpartitionStrategy': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'Optional': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'PartitionClause': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'PartitionDefinitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'Sequence': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'SubpartitionDefinitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    '_MARIADB_PARTITION_WORDS': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    '_partition_word': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    '_subpartition_strategy_word': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'annotations': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
    'isfinite': 'rhosocial.activerecord.backend.impl.mariadb.expression.query_parts.partition',
}

__all__ = [
    'MariaDBPartitionByHash',
    'MariaDBPartitionByKey',
    'MariaDBPartitionByList',
    'MariaDBPartitionByListColumns',
    'MariaDBPartitionByRange',
    'MariaDBPartitionByRangeColumns',
    'MariaDBPartitionClause',
    'MariaDBPartitionMaxValue',
    'MariaDBPartitionValue',
    'MariaDBSubpartitionClause',
    'MariaDBSubpartitionStrategy',
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
