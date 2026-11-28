# rhosocial/activerecord/backend/impl/mariadb/expression/operators/__init__.py
"""MariaDB operator expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'BaseExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBAddPartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBAnalyzePartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBCheckPartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBCoalescePartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBDropPartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBExchangePartitionStatement': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBGetPartitionsExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBOptimizePartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBPartitionTableExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBRebuildPartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBRemovePartitioningExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBReorganizePartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBRepairPartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'MariaDBTruncatePartitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'PartitionDefinitionExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'Sequence': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'Table': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
    'annotations': 'rhosocial.activerecord.backend.impl.mariadb.expression.operators.partition',
}

__all__ = [
    'MariaDBAddPartitionExpression',
    'MariaDBAnalyzePartitionExpression',
    'MariaDBCheckPartitionExpression',
    'MariaDBCoalescePartitionExpression',
    'MariaDBDropPartitionExpression',
    'MariaDBExchangePartitionStatement',
    'MariaDBGetPartitionsExpression',
    'MariaDBOptimizePartitionExpression',
    'MariaDBPartitionTableExpression',
    'MariaDBRebuildPartitionExpression',
    'MariaDBRemovePartitioningExpression',
    'MariaDBReorganizePartitionExpression',
    'MariaDBRepairPartitionExpression',
    'MariaDBTruncatePartitionExpression',
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
