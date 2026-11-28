# rhosocial/activerecord/backend/impl/mariadb/expression/introspection/__init__.py
"""MariaDB introspection expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'BaseExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.introspection',
    'MariaDBConstraintQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.introspection',
    'MariaDBDatabaseListQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.status',
    'MariaDBPartitionQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.introspection',
    'MariaDBRoutineQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.introspection',
    'MariaDBSequenceQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.introspection',
    'MariaDBSessionInfoQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.status',
    'MariaDBStorageSizeQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.status',
    'MariaDBSystemVariableExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.status',
    'MariaDBTableOptionsQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.introspection',
    'MariaDBUserListQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.status',
    'MariaDBVersionQuery': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.status',
    'Optional': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.introspection',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.impl.mariadb.expression.introspection.introspection',
}

__all__ = [
    'MariaDBConstraintQuery',
    'MariaDBDatabaseListQuery',
    'MariaDBPartitionQuery',
    'MariaDBRoutineQuery',
    'MariaDBSequenceQuery',
    'MariaDBSessionInfoQuery',
    'MariaDBStorageSizeQuery',
    'MariaDBSystemVariableExpression',
    'MariaDBTableOptionsQuery',
    'MariaDBUserListQuery',
    'MariaDBVersionQuery',
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
