# src/rhosocial/activerecord/backend/impl/mariadb/expression/query_parts/__init__.py
"""MariaDB query-part expression nodes.

Public names are re-exported lazily (PEP 562): importing this package does not
import the modules that define the nodes. A name is resolved on first access,
then cached in ``globals()``.
"""

from importlib import import_module as _import_module

__all__ = [
    "MariaDBPartitionByHash",
    "MariaDBPartitionByKey",
    "MariaDBPartitionByList",
    "MariaDBPartitionByListColumns",
    "MariaDBPartitionByRange",
    "MariaDBPartitionByRangeColumns",
    "MariaDBPartitionClause",
    "MariaDBPartitionMaxValue",
    "MariaDBPartitionValue",
    "MariaDBSubpartitionClause",
    "MariaDBSubpartitionStrategy",

]

#: name -> defining module, relative to this package
_REEXPORTS = {
    "MariaDBPartitionByHash": ".partition",
    "MariaDBPartitionByKey": ".partition",
    "MariaDBPartitionByList": ".partition",
    "MariaDBPartitionByListColumns": ".partition",
    "MariaDBPartitionByRange": ".partition",
    "MariaDBPartitionByRangeColumns": ".partition",
    "MariaDBPartitionClause": ".partition",
    "MariaDBPartitionMaxValue": ".partition",
    "MariaDBPartitionValue": ".partition",
    "MariaDBSubpartitionClause": ".partition",
    "MariaDBSubpartitionStrategy": ".partition",

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
