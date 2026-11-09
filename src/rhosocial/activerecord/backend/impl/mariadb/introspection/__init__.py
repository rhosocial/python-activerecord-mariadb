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

The families MariaDB owns outright -- sequences, table options, partitions,
stored routines, CHECK constraints, and the two status families typed in
``status_types.py`` -- live here rather than in core: a slot on a core shape
would assert that every other engine has something it does not have
(``.claude/rules/introspection.md`` §5).

Design principle: Sync and Async are separate and cannot coexist.
- MariaDBIntrospector: for synchronous backends
- AsyncMariaDBIntrospector: for asynchronous backends
"""

from .introspector import MariaDBIntrospector, AsyncMariaDBIntrospector
from .show_introspector import ShowIntrospector, AsyncShowIntrospector
from .status_introspector import (
    MariaDBStatusIntrospector,
    AsyncMariaDBStatusIntrospector,
)
from .status_types import (
    MariaDBBinaryLogInfo,
    MariaDBReplicationInfo,
    MariaDBServerOverview,
)
from .types import (
    SequenceInfo,
    TableOptionsInfo,
    MariaDBPartitionInfo,
    MariaDBRoutineInfo,
    MariaDBRoutineParameterInfo,
    MariaDBConstraintInfo,
)

__all__ = [
    "MariaDBIntrospector",
    "AsyncMariaDBIntrospector",
    "ShowIntrospector",
    "AsyncShowIntrospector",
    "MariaDBStatusIntrospector",
    "AsyncMariaDBStatusIntrospector",
    "MariaDBBinaryLogInfo",
    "MariaDBReplicationInfo",
    "MariaDBServerOverview",
    "SequenceInfo",
    "TableOptionsInfo",
    "MariaDBPartitionInfo",
    "MariaDBRoutineInfo",
    "MariaDBRoutineParameterInfo",
    "MariaDBConstraintInfo",
]
