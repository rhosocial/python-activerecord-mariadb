# rhosocial/activerecord/backend/impl/mariadb/expression/column_types/__init__.py
"""MariaDB column-type expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'ColumnDefinition': 'rhosocial.activerecord.backend.impl.mariadb.expression.column_types.column',
    'ColumnOptions': 'rhosocial.activerecord.backend.impl.mariadb.expression.column_types.column',
    'Enum': 'rhosocial.activerecord.backend.impl.mariadb.expression.column_types.column',
    'MariaDBColumnDefinition': 'rhosocial.activerecord.backend.impl.mariadb.expression.column_types.column',
    'MariaDBColumnFormat': 'rhosocial.activerecord.backend.impl.mariadb.expression.column_types.column',
    'MariaDBColumnOptions': 'rhosocial.activerecord.backend.impl.mariadb.expression.column_types.column',
    'MariaDBColumnStorage': 'rhosocial.activerecord.backend.impl.mariadb.expression.column_types.column',
    'Optional': 'rhosocial.activerecord.backend.impl.mariadb.expression.column_types.column',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.impl.mariadb.expression.column_types.column',
}

__all__ = [
    'MariaDBColumnDefinition',
    'MariaDBColumnFormat',
    'MariaDBColumnOptions',
    'MariaDBColumnStorage',
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
