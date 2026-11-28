# rhosocial/activerecord/backend/impl/mariadb/expression/sources/__init__.py
"""MariaDB query-source expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'Any': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
    'BaseExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
    'JSONTableColumn': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
    'List': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
    'MariaDBJSONTableExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
    'NestedPath': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
    'Optional': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
    'Union': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
    'dataclass': 'rhosocial.activerecord.backend.impl.mariadb.expression.sources.json_table',
}

__all__ = [
    'JSONTableColumn',
    'MariaDBJSONTableExpression',
    'NestedPath',
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
