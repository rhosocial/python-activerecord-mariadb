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
from .backend.async_backend import AsyncMariaDBBackend
from .dialect import MariaDBDialect, MARIADB_VERSION_BOUNDARIES
from .transaction import MariaDBTransactionManager, MariaDBTransactionMixin
from .async_transaction import AsyncMariaDBTransactionManager
from .config import MariaDBConnectionConfig
from .types import MariaDBEnumType, MariaDBSetType

__all__ = [
    'MariaDBBackend',
    'AsyncMariaDBBackend',
    'MariaDBDialect',
    'MARIADB_VERSION_BOUNDARIES',
    'MariaDBTransactionManager',
    'AsyncMariaDBTransactionManager',
    'MariaDBTransactionMixin',
    'MariaDBConnectionConfig',
    'MariaDBEnumType',
    'MariaDBSetType',
]