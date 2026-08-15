# src/rhosocial/activerecord/backend/impl/mariadb/introspection/__init__.py
"""MariaDB introspection module.

This module provides introspection capabilities for MariaDB databases,
allowing inspection of database metadata including tables, columns,
indexes, foreign keys, views, and triggers.

The introspectors are exposed via ``backend.introspector`` and also provide
MariaDB-specific access through ``backend.introspector.show``.

Architecture:
  - SQL generation: Delegated to MariaDBIntrospectionMixin.format_*_query()
    methods in the Dialect layer via Expression.to_sql()
  - Query execution: Handled by IntrospectorExecutor
  - Result parsing: _parse_* methods in introspector.py (pure Python, no I/O)

Design principle: Sync and Async are separate and cannot coexist.
- SyncMariaDBIntrospector: for synchronous backends
- AsyncMariaDBIntrospector: for asynchronous backends
"""

from .introspector import SyncMariaDBIntrospector, AsyncMariaDBIntrospector
from .show_introspector import SyncShowIntrospector, AsyncShowIntrospector
from .status_introspector import (
    SyncMariaDBStatusIntrospector,
    AsyncMariaDBStatusIntrospector,
)

__all__ = [
    "SyncMariaDBIntrospector",
    "AsyncMariaDBIntrospector",
    "SyncShowIntrospector",
    "AsyncShowIntrospector",
    "SyncMariaDBStatusIntrospector",
    "AsyncMariaDBStatusIntrospector",
]
