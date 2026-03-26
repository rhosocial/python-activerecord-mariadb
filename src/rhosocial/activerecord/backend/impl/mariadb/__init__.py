# src/rhosocial/activerecord/backend/impl/mariadb/__init__.py
"""
MariaDB backend implementation for ActiveRecord.

This module provides a MariaDB-specific implementation including:
- MariaDB backend with connection management and query execution
- Async MariaDB backend with full async support
- MariaDB dialect and expression handling
- MariaDB-specific type definitions
- Support for RETURNING clause (available since MariaDB 10.5)
- Support for SEQUENCE (available since MariaDB 10.3)
- Support for INTERSECT/EXCEPT (available since MariaDB 10.3)
"""

__version__ = "1.0.0.dev1"

from .backend import MariaDBBackend
from .dialect import MariaDBDialect, MARIADB_VERSION_BOUNDARIES
from .transaction import MariaDBTransactionManager, MariaDBTransactionMixin
from .config import MariaDBConnectionConfig
from .types import MariaDBEnumType, MariaDBSetType

__all__ = [
    'MariaDBBackend',
    'MariaDBDialect',
    'MARIADB_VERSION_BOUNDARIES',
    'MariaDBTransactionManager',
    'MariaDBTransactionMixin',
    'MariaDBConnectionConfig',
    'MariaDBEnumType',
    'MariaDBSetType',
]


def __getattr__(name: str):
    """Lazily load async components.

    Raises:
        ImportError: If async dependencies are not installed.
        AttributeError: If the requested attribute doesn't exist.
    """
    _lazy_imports = {
        "AsyncMariaDBBackend": (".backend.async_backend", "AsyncMariaDBBackend"),
        "AsyncMariaDBTransactionManager": (".async_transaction", "AsyncMariaDBTransactionManager"),
    }

    if name in _lazy_imports:
        module_path, class_name = _lazy_imports[name]
        try:
            import importlib
            module = importlib.import_module(module_path, __name__)
            return getattr(module, class_name)
        except ImportError as e:
            raise ImportError(
                f"{name} requires async support. "
                f"Install with: pip install rhosocial-activerecord-mariadb[async]"
            ) from e

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
