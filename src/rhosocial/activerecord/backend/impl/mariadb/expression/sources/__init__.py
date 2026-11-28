# src/rhosocial/activerecord/backend/impl/mariadb/expression/sources/__init__.py
"""MariaDB query-source expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``.
"""

from importlib import import_module as _import_module

__all__ = [
    "JSONTableColumn",
    "MariaDBJSONTableExpression",
    "NestedPath",

]

#: name -> defining module, relative to this package
_REEXPORTS = {
    "JSONTableColumn": ".json_table",
    "MariaDBJSONTableExpression": ".json_table",
    "NestedPath": ".json_table",

}


def __getattr__(name: str):
    """Resolve a re-exported name on first access (PEP 562)."""
    try:
        module_name = _REEXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = _import_module(module_name, __name__).__dict__[name]
    globals()[name] = value  # cache: subsequent access is a plain attribute lookup
    return value


def __dir__() -> list:
    """Make the lazy re-exports visible to ``dir()``."""
    return sorted(set(globals()) | set(__all__))
