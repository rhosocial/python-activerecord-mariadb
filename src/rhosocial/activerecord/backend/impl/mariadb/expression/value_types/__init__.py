# rhosocial/activerecord/backend/impl/mariadb/expression/value_types/__init__.py
"""MariaDB value-type expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'AliasableMixin': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.set_type',
    'ComparisonMixin': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.set_type',
    'Enum': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.table_options',
    'List': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.set_type',
    'MariaDBFindInSetExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.set_type',
    'MariaDBRowFormat': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.table_options',
    'MariaDBSetContainsExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.set_type',
    'MariaDBSetLiteralExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.set_type',
    'Optional': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.set_type',
    'SQLValue': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.set_type',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.impl.mariadb.expression.value_types.set_type',
}

__all__ = [
    'MariaDBFindInSetExpression',
    'MariaDBRowFormat',
    'MariaDBSetContainsExpression',
    'MariaDBSetLiteralExpression',
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
