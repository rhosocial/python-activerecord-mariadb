# rhosocial/activerecord/backend/impl/mariadb/expression/functions/__init__.py
"""MariaDB function expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'AliasableMixin': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'Any': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'ComparisonMixin': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'Dict': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'List': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'MariaDBJSONArrayExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'MariaDBJSONContainsExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'MariaDBJSONExtractExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'MariaDBJSONObjectExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'MariaDBMatchAgainstExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.match_against',
    'MariaDBSTContainsExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.spatial',
    'MariaDBSTDistanceExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.spatial',
    'MariaDBSTGeomFromTextExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.spatial',
    'MariaDBSTWithinExpression': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.spatial',
    'Optional': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'SQLValue': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.impl.mariadb.expression.functions.json',
}

__all__ = [
    'MariaDBJSONArrayExpression',
    'MariaDBJSONContainsExpression',
    'MariaDBJSONExtractExpression',
    'MariaDBJSONObjectExpression',
    'MariaDBMatchAgainstExpression',
    'MariaDBSTContainsExpression',
    'MariaDBSTDistanceExpression',
    'MariaDBSTGeomFromTextExpression',
    'MariaDBSTWithinExpression',
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
