# rhosocial/activerecord/backend/impl/mariadb/expression/objects/__init__.py
"""MariaDB schema-object expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
}

__all__ = [
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
