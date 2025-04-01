"""
MariaDB backend implementation for the Python ORM.

This module provides a MariaDB-specific implementation including:
- MariaDB backend with connection management and query execution
- Type mapping and value conversion
- Transaction management with savepoint support
- MariaDB dialect and expression handling
- MariaDB-specific type definitions and mappings
- Support for RETURNING clause (available since MariaDB 10.5)
"""

__version__ = "1.0.0.dev1"

from .backend import MariaDBBackend
from .dialect import (
    MariaDBDialect,
    MariaDBExpression,
    MariaDBTypeMapper,
    MariaDBValueMapper,
    MariaDBReturningHandler,
    MariaDBAggregateHandler,
    MariaDBJsonHandler,
    MariaDBSQLBuilder,
    DriverType,
)
from .transaction import MariaDBTransactionManager
from .types import (
    MariaDBTypes,
    MariaDBColumnType,
    MARIADB_TYPE_MAPPINGS,
)

__all__ = [
    # Backend
    'MariaDBBackend',

    # Dialect related
    'MariaDBDialect',
    'MariaDBExpression',
    'MariaDBTypeMapper',
    'MariaDBValueMapper',
    'MariaDBReturningHandler',
    'MariaDBAggregateHandler',
    'MariaDBJsonHandler',
    'MariaDBSQLBuilder',
    'DriverType',

    # Transaction
    'MariaDBTransactionManager',

    # Types
    'MariaDBTypes',
    'MariaDBColumnType',
    'MARIADB_TYPE_MAPPINGS',
]