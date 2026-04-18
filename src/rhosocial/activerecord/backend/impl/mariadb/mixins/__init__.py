# src/rhosocial/activerecord/backend/impl/mariadb/mixins/__init__.py
"""MariaDB dialect-specific Mixin implementations.

This module provides modular mixin classes that implement MariaDB-specific
functionality shared between sync and async backends.

Mixin Organization:
- introspection.py: Database metadata introspection
- transaction.py: Transaction isolation level management
- backend.py: Backend common functionality
- sequence.py: SEQUENCE storage engine support (MariaDB 10.3+)
- returning.py: RETURNING clause support (MariaDB 10.5+)
- system_versioning.py: System-versioned tables (MariaDB 10.3+)
- dml.py: DML operations (INSERT IGNORE, REPLACE, LOAD DATA)
- spatial.py: Spatial data types and functions
- locking.py: Row-level locking (FOR UPDATE, FOR SHARE, SKIP LOCKED)
- trigger.py: Trigger DDL with INSTEAD OF support (MariaDB 10.4+)
- json.py: JSON functions and arrow operators
- set_type.py: SET type support
- fulltext.py: Full-text search support
- intersect_except.py: INTERSECT/EXCEPT set operations
- cte.py: Common Table Expressions support
- window.py: Window functions support
"""

from .introspection import MariaDBIntrospectionMixin
from .transaction import MariaDBTransactionMixin
from .backend import MariaDBBackendMixin, MARIADB_VERSION_BOUNDARIES
from .sequence import MariaDBSequenceMixin
from .returning import MariaDBReturningMixin
from .system_versioning import MariaDBSystemVersioningMixin
from .dml import MariaDBDMLOperationMixin
from .spatial import MariaDBSpatialMixin
from .locking import MariaDBLockingMixin
from .trigger import MariaDBTriggerMixin
from .json import MariaDBJSONMixin

__all__ = [
    'MARIADB_VERSION_BOUNDARIES',
    'MariaDBIntrospectionMixin',
    'MariaDBTransactionMixin',
    'MariaDBBackendMixin',
    'MariaDBSequenceMixin',
    'MariaDBReturningMixin',
    'MariaDBSystemVersioningMixin',
    'MariaDBDMLOperationMixin',
    'MariaDBSpatialMixin',
    'MariaDBLockingMixin',
    'MariaDBTriggerMixin',
    'MariaDBJSONMixin',
]
