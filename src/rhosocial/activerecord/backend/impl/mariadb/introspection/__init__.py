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
  - Result parsing: parse_* methods in introspector.py (pure Python, no I/O)

The families MariaDB owns outright -- sequences, table options, and the two
status families typed in ``status_types.py`` -- live here rather than in
core: a slot on a core shape would assert that every other engine has
something it does not have (``.claude/rules/introspection.md`` §5).

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
from .status_types import (
    MariaDBBinaryLogInfo,
    MariaDBReplicationInfo,
    MariaDBServerOverview,
)
from .types import SequenceInfo, TableOptionsInfo

__all__ = [
    "SyncMariaDBIntrospector",
    "AsyncMariaDBIntrospector",
    "SyncShowIntrospector",
    "AsyncShowIntrospector",
    "SyncMariaDBStatusIntrospector",
    "AsyncMariaDBStatusIntrospector",
    "MariaDBBinaryLogInfo",
    "MariaDBReplicationInfo",
    "MariaDBServerOverview",
    "SequenceInfo",
    "TableOptionsInfo",
]
